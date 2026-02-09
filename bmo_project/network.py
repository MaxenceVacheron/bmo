import os
import base64
import json
import urllib.request
import urllib.parse
import time
import sys
import threading
import urllib.error
from . import config

def get_auth_headers():
    """Return Basic Auth headers based on identity"""
    # Use identity as both username and password as per requirements
    username = config.IDENTITY
    password = config.IDENTITY
    auth_str = f"{username}:{password}"
    auth_bytes = auth_str.encode("ascii")
    auth_b64 = base64.b64encode(auth_bytes).decode("ascii")
    return {"Authorization": f"Basic {auth_b64}"}

def sync_messages(state):
    """Single pass message sync from remote API"""
    try:
        print("✉️ Manual sync...")
        sys.stdout.flush()
        
        headers = get_auth_headers()
        
        # Filter messages for current recipient
        params = urllib.parse.urlencode({'recipient': config.IDENTITY})
        url = f"{config.MESSAGES_URL}/?{params}"
        
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                # Server returns {"messages": [...]}
                new_msgs = data.get("messages", [])
                
                existing_ids = {m["id"] for m in state["messages"]["list"]}
                added = False
                for m in new_msgs:
                    if m["id"] not in existing_ids:
                        state["messages"]["list"].append(m)
                        if not m.get("read", False):
                            state["messages"]["unread"] = True
                        added = True
                    else:
                        # Update read status if changed
                        for local_m in state["messages"]["list"]:
                            if local_m["id"] == m["id"]:
                                if m.get("read", False) and not local_m.get("read", False):
                                    local_m["read"] = True

                if added:
                    state["messages"]["list"].sort(key=lambda x: x.get("timestamp", 0), reverse=True)
                    save_messages(state)
                    state["needs_redraw"] = True
                    print(f"📩 Received {len(new_msgs)} messages!")
                    sys.stdout.flush()
                return True
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error during Sync: {e.code} - {e.reason}")
        try:
             print(f"  Response: {e.read().decode()}")
        except: pass
        sys.stdout.flush()
    except Exception as e:
        print(f"❌ Sync Error: {e}")
        sys.stdout.flush()
    return False

def send_read_receipt(msg_id):
    """Notify the API that a message has been read"""
    try:
        print(f"👀 Sending read receipt for message ID: {msg_id}")
        sys.stdout.flush()
        
        # Add +1h (3600s) to match server expectation? 
        # Server expects "read_at". Let's use current time.
        read_time = int(time.time())
        
        data = json.dumps({
            "message_id": msg_id,
            "read_at": read_time
        }).encode('utf-8')
        
        headers = get_auth_headers()
        headers['Content-Type'] = 'application/json'
        
        req = urllib.request.Request(config.READ_RECEIPT_URL, data=data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                print(f"✅ Read receipt sent successfully for {msg_id}")
            else:
                print(f"⚠️ Failed to send receipt for {msg_id}. Status: {response.status}")
                try: print(response.read().decode())
                except: pass
        sys.stdout.flush()
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error sending receipt for {msg_id}: {e.code} - {e.reason}")
        try: print(e.read().decode())
        except: pass
        sys.stdout.flush()
    except Exception as e:
        print(f"❌ Error sending read receipt: {e}")
        sys.stdout.flush()

def send_message(recipient, content):
    """Send a new message"""
    try:
        print(f"📤 Sending to {recipient}: {content}")
        sys.stdout.flush()
        
        timestamp = int(time.time())
        
        payload = {
            "sender": config.IDENTITY,
            "recipient": recipient,
            "content": content,
            "timestamp": timestamp 
        }
        
        data = json.dumps(payload).encode('utf-8')
        
        headers = get_auth_headers()
        headers['Content-Type'] = 'application/json'
        
        req = urllib.request.Request(config.SEND_MESSAGE_URL, data=data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                print("✅ Message sent successfully!")
                return True
            else:
                print(f"⚠️ Failed to send message: {response.status}")
                return False
                
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error during Send: {e.code} - {e.reason}")
        try:
             print(f"  Response: {e.read().decode()}")
        except: pass
    except Exception as e:
        print(f"❌ Send Error: {e}")
        return False

def fetch_remote_messages(state):
    """Background thread for periodic fetch"""
    while True:
        sync_messages(state)
        time.sleep(60)

def load_messages(state):
    """Load messages from local storage"""
    if os.path.exists(config.MESSAGES_FILE):
        try:
            with open(config.MESSAGES_FILE, 'r') as f:
                data = json.load(f)
                state["messages"]["list"] = data.get("messages", [])
        except Exception as e:
            print(f"Error loading messages: {e}")

def save_messages(state):
    """Save messages to local storage"""
    try:
        with open(config.MESSAGES_FILE, 'w') as f:
            json.dump({"messages": state["messages"]["list"]}, f)
    except Exception as e:
        print(f"Error saving messages: {e}")
