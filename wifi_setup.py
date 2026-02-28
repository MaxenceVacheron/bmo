#!/usr/bin/env python3
"""
WiFi Configuration Portal — Web server for BMO/AMO setup.
Serves a mobile-friendly config page on http://192.168.4.1
when the device is in hotspot mode.

Runs as a subprocess spawned by bmo_pygame.py.
"""
import os
import sys
import json
import re
import signal
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

# --- PATHS ---
BMO_DIR = "/home/pi/bmo"
WPA_CONF = "/etc/wpa_supplicant/wpa_supplicant.conf"
NAME_FILE = os.path.join(BMO_DIR, ".name")
CONFIG_FILE = os.path.join(BMO_DIR, "bmo_config.json")
WPA_TEMPLATE = os.path.join(BMO_DIR, "wpa_supplicant.conf")

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 80


def read_device_name():
    try:
        with open(NAME_FILE, "r") as f:
            return f.read().strip().upper()
    except:
        return "BMO"


def read_current_wifi():
    """Parse wpa_supplicant.conf to get current SSID"""
    ssid = ""
    try:
        conf = WPA_CONF if os.path.exists(WPA_CONF) else WPA_TEMPLATE
        with open(conf, "r") as f:
            for line in f:
                if "ssid=" in line and "#" not in line:
                    match = re.search(r'ssid="([^"]*)"', line)
                    if match:
                        ssid = match.group(1)
    except:
        pass
    return ssid


def read_config():
    """Read bmo_config.json"""
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def get_messages_url():
    """Read the messaging server URL from bmo_pygame.py constants"""
    try:
        with open(os.path.join(BMO_DIR, "bmo_pygame.py"), "r") as f:
            for line in f:
                if "MESSAGES_URL" in line and "=" in line and "#" not in line:
                    match = re.search(r'"(https?://[^"]*)"', line)
                    if match:
                        return match.group(1)
    except:
        pass
    return "https://bmo.pg.maxencevacheron.fr"


def build_html(device_name, current_ssid, messages_url, save_result=None):
    """Generate the config page HTML"""
    # Device color theme
    if device_name == "AMO":
        accent = "#b284dc"
        accent_dark = "#8a5cbf"
        bg_grad = "linear-gradient(135deg, #1a0a2e 0%, #2d1b4e 50%, #1a0a2e 100%)"
    else:
        accent = "#a5d7b9"
        accent_dark = "#7bc49a"
        bg_grad = "linear-gradient(135deg, #0a1e14 0%, #1b3a2b 50%, #0a1e14 100%)"

    result_html = ""
    if save_result == "ok":
        result_html = '<div class="alert success">✅ Settings saved! WiFi will reconnect shortly...</div>'
    elif save_result:
        result_html = f'<div class="alert error">❌ Error: {save_result}</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>{device_name} Setup</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: {bg_grad};
            min-height: 100vh;
            color: #e8e8f0;
            padding: 20px;
        }}
        .container {{
            max-width: 420px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            padding: 30px 0 20px;
        }}
        .header h1 {{
            font-size: 2.2em;
            color: {accent};
            text-shadow: 0 0 20px {accent}44;
            margin-bottom: 6px;
        }}
        .header p {{
            color: #888;
            font-size: 0.9em;
        }}
        .card {{
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 16px;
            backdrop-filter: blur(10px);
        }}
        .card h2 {{
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: {accent};
            margin-bottom: 16px;
        }}
        .field {{
            margin-bottom: 16px;
        }}
        .field label {{
            display: block;
            font-size: 0.85em;
            color: #aaa;
            margin-bottom: 6px;
        }}
        .field input {{
            width: 100%;
            padding: 12px 16px;
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 10px;
            color: #fff;
            font-size: 1em;
            outline: none;
            transition: border-color 0.2s;
        }}
        .field input:focus {{
            border-color: {accent};
            box-shadow: 0 0 0 3px {accent}22;
        }}
        .field input::placeholder {{
            color: #555;
        }}
        .btn {{
            display: block;
            width: 100%;
            padding: 14px;
            background: {accent};
            color: #000;
            font-size: 1.1em;
            font-weight: 700;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .btn:hover {{
            background: {accent_dark};
            transform: translateY(-1px);
            box-shadow: 0 4px 20px {accent}44;
        }}
        .btn:active {{
            transform: translateY(0);
        }}
        .alert {{
            padding: 14px 18px;
            border-radius: 10px;
            margin-bottom: 16px;
            font-size: 0.95em;
        }}
        .alert.success {{
            background: rgba(46,204,113,0.15);
            border: 1px solid rgba(46,204,113,0.3);
            color: #2ecc71;
        }}
        .alert.error {{
            background: rgba(231,76,60,0.15);
            border: 1px solid rgba(231,76,60,0.3);
            color: #e74c3c;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #444;
            font-size: 0.8em;
        }}
        .status {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 14px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            font-size: 0.85em;
            color: #888;
        }}
        .status .dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: {accent};
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.4; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚙️ {device_name}</h1>
            <p>Configuration Portal</p>
        </div>

        {result_html}

        <form method="POST" action="/save">
            <div class="card">
                <h2>📶 WiFi Network</h2>
                <div class="field">
                    <label>Network Name (SSID)</label>
                    <input type="text" name="ssid" value="{current_ssid}" placeholder="Your WiFi name" required>
                </div>
                <div class="field">
                    <label>Password</label>
                    <input type="password" name="password" placeholder="WiFi password" required>
                </div>
            </div>

            <div class="card">
                <h2>🤖 Device</h2>
                <div class="field">
                    <label>Device Name</label>
                    <input type="text" name="device_name" value="{device_name}" placeholder="BMO or AMO">
                </div>
                <div class="field">
                    <label>Messaging Server URL</label>
                    <input type="url" name="messages_url" value="{messages_url}" placeholder="https://...">
                </div>
            </div>

            <button type="submit" class="btn">💾 Save & Reconnect</button>
        </form>

        <div class="card" style="margin-top: 16px;">
            <div class="status">
                <div class="dot"></div>
                <span>Hotspot active — {device_name}-Setup</span>
            </div>
        </div>

        <div class="footer">
            Built with ❤️ by Maxence
        </div>
    </div>
</body>
</html>"""


class SetupHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the config portal"""

    def log_message(self, format, *args):
        print(f"🌐 {args[0]}")
        sys.stdout.flush()

    def do_GET(self):
        # Captive Portal detection paths
        captive_paths = [
            "/generate_204", "/gen_204", "/ncsi.txt", "/success.html", 
            "/hotspot-detect.html", "/connectivity-check.html"
        ]
        
        if any(self.path.startswith(p) for p in captive_paths):
            print(f"🚩 Captive Portal query: {self.path} -> Redirecting to /")
            self.send_response(302)
            self.send_header("Location", f"http://{LISTEN_HOST if LISTEN_HOST != '0.0.0.0' else '192.168.4.1'}/")
            self.end_headers()
            return

        device_name = read_device_name()
        current_ssid = read_current_wifi()
        messages_url = get_messages_url()

        # Serve the config page for any GET request (captive portal)
        html = build_html(device_name, current_ssid, messages_url)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html.encode())))
        self.end_headers()
        self.wfile.write(html.encode())

    def do_POST(self):
        if self.path != "/save":
            self.send_error(404)
            return

        # Read form data
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        params = parse_qs(body)

        ssid = params.get("ssid", [""])[0].strip()
        password = params.get("password", [""])[0]
        device_name = params.get("device_name", ["BMO"])[0].strip().upper()
        messages_url = params.get("messages_url", [""])[0].strip()

        result = None

        try:
            if not ssid or not password:
                raise ValueError("SSID and password are required")

            # 1. Write wpa_supplicant.conf (both local template and system)
            wpa_content = f"""ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=FR

network={{
    ssid="{ssid}"
    psk="{password}"

    key_mgmt=WPA-PSK
    scan_ssid=1
    priority=1
}}
"""
            # Write local template
            with open(WPA_TEMPLATE, "w") as f:
                f.write(wpa_content)

            # Write system config
            with open(WPA_CONF, "w") as f:
                f.write(wpa_content)
            os.chmod(WPA_CONF, 0o600)

            # 2. Write device name
            with open(NAME_FILE, "w") as f:
                f.write(device_name.lower())

            # 3. Update messages URL in config if provided
            if messages_url:
                config = read_config()
                config["messages_url"] = messages_url
                with open(CONFIG_FILE, "w") as f:
                    json.dump(config, f)

            print(f"✅ Config saved: SSID={ssid}, Device={device_name}")
            sys.stdout.flush()
            result = "ok"

        except Exception as e:
            print(f"❌ Save error: {e}")
            sys.stdout.flush()
            result = str(e)

        # Respond with result page
        current_ssid = ssid if result == "ok" else read_current_wifi()
        html = build_html(device_name, current_ssid, messages_url or get_messages_url(), save_result=result)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html.encode())))
        self.end_headers()
        self.wfile.write(html.encode())

        # If save was successful, schedule hotspot stop after response
        if result == "ok":
            print("🔄 Scheduling hotspot stop in 3 seconds...")
            sys.stdout.flush()
            import threading
            def delayed_stop():
                import time
                time.sleep(3)
                print("📡 Stopping hotspot and restoring WiFi...")
                sys.stdout.flush()
                os.system("sudo /home/pi/bmo/wifi_setup.sh stop")
                # Signal parent that we're done
                with open("/tmp/bmo_wifi_setup_done", "w") as f:
                    f.write("done")
                os._exit(0)
            threading.Thread(target=delayed_stop, daemon=True).start()


def main():
    print(f"🌐 WiFi Setup Server starting on {LISTEN_HOST}:{LISTEN_PORT}")
    sys.stdout.flush()

    server = HTTPServer((LISTEN_HOST, LISTEN_PORT), SetupHandler)

    # Handle graceful shutdown
    def sig_handler(sig, frame):
        print("🛑 Setup server shutting down...")
        sys.stdout.flush()
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("🛑 Setup server stopped.")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
