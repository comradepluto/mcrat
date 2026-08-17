import socket
import threading

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
    """Handles communication with one connected client."""
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
    print("=========================================")
    print("  serverphysics listener")
    print(f"  Listening on port {PORT}")
    print(f"  Your IP: {local_ip}")
    print(f"  Set this in plugins/serverphysics/config.yml")
    print("=========================================\n")
    start_listener()
