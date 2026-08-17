import socket
import threading
import subprocess
import sys
import os

HOST = "0.0.0.0"
PORT = 5002

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def check_port_open(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex(("127.0.0.1", port))
        s.close()
        return result == 0
    except Exception:
        return False

def open_firewall_port(port):
    # Check for ufw
    if subprocess.run(["which", "ufw"], capture_output=True).returncode == 0:
        subprocess.run(["sudo", "ufw", "allow", f"{port}/tcp"], capture_output=True)
        print(f"[+] Opened port {port}/tcp via ufw")
        return True

    # Check for firewalld
    if subprocess.run(["which", "firewall-cmd"], capture_output=True).returncode == 0:
        subprocess.run(["sudo", "firewall-cmd", "--add-port=" + str(port) + "/tcp", "--permanent"], capture_output=True)
        subprocess.run(["sudo", "firewall-cmd", "--reload"], capture_output=True)
        print(f"[+] Opened port {port}/tcp via firewalld")
        return True

    # Fallback to iptables
    if subprocess.run(["which", "iptables"], capture_output=True).returncode == 0:
        subprocess.run(["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--dport", str(port), "-j", "ACCEPT"], capture_output=True)
        print(f"[+] Opened port {port}/tcp via iptables")
        return True

    print("[!] No supported firewall found (ufw/firewalld/iptables)")
    return False

def handle_client(conn, addr):
    print(f"[+] Connection established with {addr[0]}:{addr[1]}")
    try:
        while True:
            data = conn.recv(1024).decode('utf-8').strip()
            if not data:
                break

            print("\n\n=== RECEIVED MESSAGE ===")
            print(f"From {addr[0]}:{addr[1]} -> Message: {data}")
            print("=======================\n")

    except ConnectionResetError:
        print("[*] Client forcibly closed the connection.")
    except Exception as e:
        print(f"[!] Error handling client connection: {e}")
    finally:
        conn.close()

def write_config(server_path, ip, port):
    config_dir = os.path.join(server_path, "plugins", "serverphysics")
    config_file = os.path.join(config_dir, "config.yml")

    if not os.path.isdir(config_dir):
        os.makedirs(config_dir, exist_ok=True)

    with open(config_file, "w") as f:
        f.write(f"# Auto-configured by wizardlistener.py\n")
        f.write(f'target-ip: "{ip}"\n')
        f.write(f"target-port: {port}\n")

    return config_file

def start_listener():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(5)
        print(f"[*] Listening on {HOST}:{PORT}...")
        while True:
            conn, addr = s.accept()
            print(f"\n[+] Accepted connection from {addr}")
            client_handler = threading.Thread(target=handle_client, args=(conn, addr))
            client_handler.daemon = True
            client_handler.start()

if __name__ == "__main__":
    local_ip = get_local_ip()

    if not check_port_open(PORT):
        print(f"[!] Port {PORT} appears to be blocked by your firewall")
        answer = input(f"Open port {PORT}/tcp now? [Y/n] ").strip().lower()
        if answer != "n" and answer != "no":
            open_firewall_port(PORT)
        else:
            print(f"[*] Skipping. Make sure port {PORT}/tcp is open or the server cannot connect.")
        print()

    if len(sys.argv) > 1:
        server_path = sys.argv[1]
        answer = input(f"Detected IP: {local_ip}. Use this IP? [Y/n] ").strip().lower()
        if answer == "n" or answer == "no":
            local_ip = input("Enter the IP to use: ").strip()
        config_file = write_config(server_path, local_ip, PORT)
        print("\n=========================================")
        print("  serverphysics listener")
        print(f"  Listening on port {PORT}")
        print(f"  Target IP: {local_ip}")
        print(f"  Config written to: {config_file}")
        print("  Restart your Minecraft server to apply")
        print("=========================================\n")
    else:
        print("=========================================")
        print("  serverphysics listener")
        print(f"  Listening on port {PORT}")
        print(f"  Your IP: {local_ip}")
        print("")
        print("  To auto-configure, run with your")
        print("  Minecraft server path:")
        print(f"    python3 wizardlistener.py /path/to/server")
        print("")
        print("  Or manually set target-ip in:")
        print(f"    plugins/serverphysics/config.yml")
        print("=========================================\n")

    start_listener()
