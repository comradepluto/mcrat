import socket
import threading
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

    if len(sys.argv) > 1:
        server_path = sys.argv[1]
        config_file = write_config(server_path, local_ip, PORT)
        print("=========================================")
        print("  serverphysics listener")
        print(f"  Listening on port {PORT}")
        print(f"  Your IP: {local_ip}")
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
