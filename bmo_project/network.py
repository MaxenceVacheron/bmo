import base64
import json
import urllib.request
import time
import sys
import threading
from . import config

def sync_messages(state):
    """Single pass message sync from remote API"""
    try:
        print("✉️ Manual sync...")
        sys.stdout.flush()
        
        # HTTP Basic Auth
        # Use config.IDENTITY to determine auth if needed, but for now assuming BMO:BMO or AMO:AMO?
        # The user said "create another BMO, named AMO".
        # I'll assume the credentials might need to change based on identity.
        # For now, let's keep it simple: BMO:BMO.
        # Wait, if I am AMO, maybe I should use AMO:AMO?
        # The user didn't specify credentials. I'll stick to BMO:BMO for read, but maybe send needs identity.
        
        # Actually, let's use the identity for auth
        auth_str = f"{config.IDENTITY}:{config.IDENTITY}"
        auth = base64.b64encode(auth_str.encode("ascii")).decode("ascii")
        headers = {"Authorization": f"Basic {auth}"}
        
        req = urllib.request.Request(config.MESSAGES_URL, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                new_msgs = data.get("messages", [])
                
                # Filter messages intended for ME (config.IDENTITY)
                # Assuming the server returns all messages or messages are filtered by auth.
                # If server filtering isn't "smart", we might receive messages for the other bot.
                # But typically "my messages" are what I get.
                
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
                                    # If all messages are read, clear notification? 
                                    # (Optimization for later, but good for now)

                
                if added:
                    state["messages"]["list"].sort(key=lambda x: x.get("timestamp", 0), reverse=True)
                    save_messages(state)
                    state["needs_redraw"] = True
                    print(f"📩 Received {len(new_msgs)} messages!")
                    sys.stdout.flush()
                return True
    except Exception as e:
        print(f"Sync Error: {e}")
        sys.stdout.flush()
    return False

def send_read_receipt(msg_id):
    """Notify the API that a message has been read"""
    try:
        # Add +1h (3600s) to match server expectation
        read_time = int(time.time()) + 3600
        
        data = json.dumps({
            "message_id": msg_id,
            "read_at": read_time
        }).encode('utf-8')
        
        req = urllib.request.Request(config.READ_RECEIPT_URL, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        
        auth_str = f"{config.IDENTITY}:{config.IDENTITY}"
        auth = base64.b64encode(auth_str.encode("ascii")).decode("ascii")
        req.add_header('Authorization', f"Basic {auth}")
        
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                print(f"✅ Read receipt sent for {msg_id}")
            else:
                print(f"⚠️ Failed to send receipt for {msg_id}: {response.status}")
        sys.stdout.flush()
    except Exception as e:
        print(f"Receipt Error: {e}")
        sys.stdout.flush()

def send_message(recipient, content):
    """Send a new message"""
    try:
        print(f"📤 Sending to {recipient}: {content}")
        sys.stdout.flush()
        
        timestamp = int(time.time()) + 3600 # Adjust timezone if needed
        
        data = json.dumps({
            "sender": config.IDENTITY,
            "recipient": recipient,
            "content": content,
            "timestamp": timestamp 
        }).encode('utf-8')
        
        req = urllib.request.Request(config.SEND_MESSAGE_URL, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        
        auth_str = f"{config.IDENTITY}:{config.IDENTITY}"
        auth = base64.b64encode(auth_str.encode("ascii")).decode("ascii")
        req.add_header('Authorization', f"Basic {auth}")
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                print("✅ Message sent successfully!")
                return True
            else:
                print(f"⚠️ Failed to send message: {response.status}")
                return False
                
    except Exception as e:
        print(f"Send Error: {e}")
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
