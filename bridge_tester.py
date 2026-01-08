import socket
import re
import time
import concurrent.futures
from threading import Lock
import requests
import os
import random
import zipfile

# --- Configuration ---
IS_GITHUB = os.getenv('GITHUB_ACTIONS') == 'true'
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

BRIDGE_SOURCES = [
    {"type": "obfs4", "url": "https://raw.githubusercontent.com/scriptzteam/Tor-Bridges-Collector/main/bridges-obfs4", "output_file": "working_obfs4.txt"},
    {"type": "webtunnel", "url": "https://raw.githubusercontent.com/scriptzteam/Tor-Bridges-Collector/main/bridges-webtunnel", "output_file": "working_webtunnel.txt"},
    {"type": "vanilla", "url": "https://github.com/scriptzteam/Tor-Bridges-Collector/raw/refs/heads/main/bridges-vanilla", "output_file": "working_vanilla.txt"}
]

# تنظیم مسیرها برای ویندوز (اگر در گیت هاب نباشد)
if not IS_GITHUB:
    for source in BRIDGE_SOURCES:
        source['output_file'] = os.path.join(r"C:\PyCharm\All\tor", source['output_file'])

MAX_WORKERS = 100
CONNECTION_TIMEOUT = 10
MAX_RETRIES = 2
file_lock = Lock()

def test_bridge(bridge_line):
    # (همان منطق تست قبلی برای تشخیص obfs4، webtunnel و vanilla)
    try:
        if "obfs4" in bridge_line.lower():
            match = re.search(r'(\d{1,3}(?:\.\d{1,3}){3}:\d+)', bridge_line)
            host, port = match.group(1).split(':') if match else (None, None)
        elif "https" in bridge_line.lower():
            match = re.search(r'https://([^/:]+)(?::(\d+))?', bridge_line)
            host, port = (match.group(1), int(match.group(2)) if match.group(2) else 443) if match else (None, None)
        else:
            match = re.search(r'^(\d{1,3}(?:\.\d{1,3}){3}):(\d+)', bridge_line.split()[0])
            host, port = (match.group(1), int(match.group(2))) if match else (None, None)

        if host and port:
            sock = socket.create_connection((host, int(port)), timeout=CONNECTION_TIMEOUT)
            sock.close()
            return bridge_line
    except: pass
    return None

def send_to_telegram(file_path):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials missing. Skipping upload.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    try:
        with open(file_path, 'rb') as f:
            response = requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID}, files={'document': f})
        print(f"Telegram Upload: {response.status_code}")
    except Exception as e:
        print(f"Telegram Error: {e}")

def main():
    for source in BRIDGE_SOURCES:
        # در ویندوز فقط وانیلا تست شود (طبق درخواست قبلی شما)
        if not IS_GITHUB and source['type'] != 'vanilla': continue
        
        response = requests.get(source['url'])
        bridges = [line.strip() for line in response.text.splitlines() if line.strip() and not line.startswith('#')]
        
        if source['type'] == 'vanilla' and len(bridges) > 1000:
            bridges = random.sample(bridges, 1000)

        with open(source['output_file'], 'w', encoding='utf-8') as f: pass
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            results = list(executor.map(test_bridge, bridges))
            with open(source['output_file'], 'a', encoding='utf-8') as f:
                for r in results:
                    if r: f.write(r + '\n')

    # فشرده‌سازی فایل‌ها
    zip_name = "Tor_Bridges_Configs.zip"
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        for source in BRIDGE_SOURCES:
            if os.path.exists(source['output_file']):
                zipf.write(source['output_file'], os.path.basename(source['output_file']))

    # ارسال به تلگرام
    if IS_GITHUB:
        send_to_telegram(zip_name)

if __name__ == "__main__":
    main()
