import json
import threading
import time
import random
import string
import requests
from datetime import datetime
from config import CONFIG  # This file should export your configuration list

# --- Global Variables & Settings ---
api_base_url = "https://gateway-run.bls.dev/api/v1"
ping_interval = 120  # seconds between pings
max_ping_errors = 3

# Set this flag to True to use proxies from your configuration; set it to False to ignore proxies.
USE_PROXY = True

# Common headers used in HTTP requests.
common_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9"
}

# --- Helper Functions ---
def get_formatted_time():
    now = datetime.now()
    return f"[{now.strftime('%H:%M:%S')}]"

def generate_random_hardware_info():
    # Generates example hardware info.
    return {"random": ''.join(random.choices(string.ascii_letters + string.digits, k=8))}

# --- Network Functions ---
def register_node(node_id, hardware_id, ip_address, auth_token, hardware_info, proxy=None):
    url = f"{api_base_url}/nodes/{node_id}"
    payload = {
        "ipAddress": ip_address,
        "hardwareId": hardware_id,
        "hardwareInfo": hardware_info,
        "extensionVersion": "0.1.7"
    }
    proxies = {"http": proxy, "https": proxy} if proxy else None

    response = requests.post(
        url,
        headers={**common_headers,
                 "Content-Type": "application/json",
                 "Authorization": f"Bearer {auth_token}"},
        json=payload,
        proxies=proxies
    )
    try:
        data = response.json()
        print(f"{get_formatted_time()} Registration response for node {node_id}:", data)
        return data
    except Exception:
        print(f"{get_formatted_time()} Failed to parse registration JSON for node {node_id}:", response.text)
        raise

def start_session(node_id, auth_token, proxy=None):
    url = f"{api_base_url}/nodes/{node_id}/start-session"
    proxies = {"http": proxy, "https": proxy} if proxy else None

    response = requests.post(
        url,
        headers={**common_headers, "Authorization": f"Bearer {auth_token}"},
        proxies=proxies
    )
    try:
        data = response.json()
        print(f"{get_formatted_time()} Start session response for node {node_id}:", data)
        return data
    except Exception:
        print(f"{get_formatted_time()} Failed to parse start session JSON for node {node_id}:", response.text)
        raise

def ping_node(node_id, auth_token, proxy=None):
    url = f"{api_base_url}/nodes/{node_id}/ping"
    proxies = {"http": proxy, "https": proxy} if proxy else None

    response = requests.post(
        url,
        headers={**common_headers, "Authorization": f"Bearer {auth_token}"},
        proxies=proxies
    )
    try:
        data = response.json()
        print(f"{get_formatted_time()} Ping response for node {node_id}:", data)
        return data
    except Exception:
        print(f"{get_formatted_time()} Failed to parse ping JSON for node {node_id}:", response.text)
        raise

def check_node_status(node_id, proxy=None):
    url = f"{api_base_url}/nodes/{node_id}"
    proxies = {"http": proxy, "https": proxy} if proxy else None

    response = requests.get(url, headers=common_headers, proxies=proxies)
    if response.ok:
        print(f"{get_formatted_time()} Node {node_id} status: OK")
    else:
        print(f"{get_formatted_time()} Node {node_id} status check failed: {response.status_code}")

def check_service_health(proxy=None):
    url = "https://gateway-run.bls.dev/health"
    proxies = {"http": proxy, "https": proxy} if proxy else None

    response = requests.get(url, headers=common_headers, proxies=proxies)
    try:
        data = response.json()
        if data.get("status") == "ok":
            print(f"{get_formatted_time()} Service health check: OK")
        else:
            print(f"{get_formatted_time()} Service health check failed:", data)
    except Exception as e:
        print(f"{get_formatted_time()} Error during service health check:", e)

# --- Node Processing Function ---
def process_node(node, user_token, hardware_info):
    node_id = node.get("nodeId")
    hardware_id = node.get("hardwareId")
    # Determine proxy usage: if USE_PROXY is True, get proxy from node configuration; otherwise, use None.
    proxy = node.get("proxy") if USE_PROXY else None
    # For demonstration purposes, using a placeholder IP address.
    ip_address = "127.0.0.1"
    print(f"{get_formatted_time()} Processing node {node_id} with hardware ID {hardware_id} and IP {ip_address}")
    try:
        register_node(node_id, hardware_id, ip_address, user_token, hardware_info, proxy)
        start_session(node_id, user_token, proxy)
    except Exception as e:
        print(f"{get_formatted_time()} Error during registration/session for node {node_id}: {e}")
        return

    ping_errors = 0
    while True:
        try:
            check_service_health(proxy)
            ping_node(node_id, user_token, proxy)
            check_node_status(node_id, proxy)
            ping_errors = 0  # reset on success
        except Exception as e:
            ping_errors += 1
            print(f"{get_formatted_time()} Ping error for node {node_id}: {e} (error count: {ping_errors})")
            if ping_errors >= max_ping_errors:
                print(f"{get_formatted_time()} Maximum ping errors reached for node {node_id}. Restarting process...")
                break  # Optionally add re-registration/restarting logic here
        time.sleep(ping_interval)

# --- Main Execution Function ---
def run_all():
    threads = []
    # CONFIG structure is assumed to be a list of user objects.
    for user in CONFIG:
        user_token = user.get("usertoken")
        for node in user.get("nodes", []):
            # Use the hardware info provided in the node configuration.
            # If you prefer to generate default hardware info for each node, adjust accordingly.
            hardware_info = {"hardwareId": node.get("hardwareId")}
            t = threading.Thread(target=process_node, args=(node, user_token, hardware_info))
            t.start()
            threads.append(t)

    for t in threads:
        t.join()

# --- Main Entry Point ---
if __name__ == "__main__":
    print(f"{get_formatted_time()} Starting Python port of Blockless Bless Network Bot")
    run_all()
