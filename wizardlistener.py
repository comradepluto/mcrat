import socket
import threading
import subprocess
import sys
import os
import shutil

HOST = "0.0.0.0"
PORT = 5002

players = {}
selected_player = None
results = []
lock = threading.Lock()

def clear():
    os.system('clear' if os.name != 'nt' else 'cls')

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
    if subprocess.run(["which", "ufw"], capture_output=True).returncode == 0:
        subprocess.run(["sudo", "ufw", "allow", f"{port}/tcp"], capture_output=True)
        print(f"[+] Opened port {port}/tcp via ufw")
        return True
    if subprocess.run(["which", "firewall-cmd"], capture_output=True).returncode == 0:
        subprocess.run(["sudo", "firewall-cmd", "--add-port=" + str(port) + "/tcp", "--permanent"], capture_output=True)
        subprocess.run(["sudo", "firewall-cmd", "--reload"], capture_output=True)
        print(f"[+] Opened port {port}/tcp via firewalld")
        return True
    if subprocess.run(["which", "iptables"], capture_output=True).returncode == 0:
        subprocess.run(["sudo", "iptables", "-A", "INPUT", "-p", "tcp", "--dport", str(port), "-j", "ACCEPT"], capture_output=True)
        print(f"[+] Opened port {port}/tcp via iptables")
        return True
    print("[!] No supported firewall found (ufw/firewalld/iptables)")
    return False

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

def draw_dashboard():
    clear()
    term_width = shutil.get_terminal_size((80, 24)).columns

    print("=" * term_width)
    print(f"  serverphysics | Listening on {HOST}:{PORT}")
    print("=" * term_width)

    with lock:
        player_list = list(players.values())

    if player_list:
        print(f"  ONLINE PLAYERS ({len(player_list)})")
        print("  " + "-" * (term_width - 4))
        for i, p in enumerate(player_list, 1):
            marker = " > " if selected_player == p["name"] else "   "
            hp_bar = "#" * (p["health"] // 2) + "-" * (10 - p["health"] // 2)
            print(f"{marker}[{i}] {p['name']:<16} HP:{p['health']:<3} Food:{p['food']:<3}  {p['world']}")
            print(f"     IP: {p['ip']:<15} Ping: {p['ping']}ms  GM: {p['gamemode']}")
            print(f"     Loc: {p['x']} / {p['y']} / {p['z']}")
            if i < len(player_list):
                print()
    else:
        print("  No players connected")
        print("  Waiting for connections...")

    print()
    print("=" * term_width)
    print("  COMMANDS")
    print("  " + "-" * (term_width - 4))
    cmds = [
        ("select <#>", "select a player by number"),
        ("hurt <amt>", "deal damage"),
        ("heal", "full health"),
        ("starve", "empty hunger bar"),
        ("feed", "fill hunger bar"),
        ("msg <color> <text>", "send colored message"),
        ("fakejoin <name>", "fake a join message"),
        ("fakequit <name>", "fake a quit message"),
        ("tp <x> <y> <z>", "teleport player"),
        ("gamemode <mode>", "change gamemode"),
        ("kick <reason>", "kick player"),
        ("ban <reason>", "ban player"),
        ("ignite <secs>", "set player on fire"),
        ("freeze", "toggle freeze"),
        ("swap <player>", "swap positions"),
        ("cmd <command>", "run server command"),
        ("say <message>", "broadcast message"),
        ("location", "get player location"),
        ("death", "last death location"),
        ("refresh", "refresh player info"),
        ("players", "list all online players"),
        ("quit", "exit"),
    ]
    for cmd, desc in cmds:
        print(f"  {cmd:<22} {desc}")
    print("=" * term_width)

    if selected_player:
        print(f"  Selected: {selected_player}")
    else:
        print("  No player selected (use 'select <#>')")

    if results:
        print()
        for r in results[-5:]:
            print(f"  {r}")
        results.clear()

    print()
    try:
        return input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        return "quit"

def handle_client(conn, addr):
    name = "unknown"
    try:
        while True:
            data = conn.recv(8192).decode('utf-8').strip()
            if not data:
                break
            for line in data.split("\n"):
                line = line.strip()
                if not line:
                    continue
                with lock:
                    if line.startswith("INFO:"):
                        parts = line.split(":")
                        if len(parts) >= 11:
                            players[parts[1]] = {
                                "name": parts[1],
                                "uuid": parts[2],
                                "ip": parts[3],
                                "health": int(parts[4]),
                                "food": int(parts[5]),
                                "x": parts[6],
                                "y": parts[7],
                                "z": parts[8],
                                "gamemode": parts[9],
                                "ping": parts[10],
                                "world": parts[11] if len(parts) > 11 else "unknown",
                                "conn": conn,
                            }
                    elif line.startswith("PLAYERS:"):
                        names = line[8:].split(",")
                        for pname in pname_loop(names):
                            pass
                    elif line.startswith("RESULT:"):
                        results.append(line[7:])
                    elif line.startswith("QUIT:"):
                        qname = line[5:]
                        if qname in players:
                            del players[qname]
                    elif line.startswith("DEATHLOC:"):
                        pass
    except ConnectionResetError:
        pass
    except Exception:
        pass
    finally:
        with lock:
            to_remove = [n for n, p in players.items() if p["conn"] is conn]
            for n in to_remove:
                del players[n]
        conn.close()

def pname_loop(names):
    for n in names:
        yield n

def send_to_selected(message):
    with lock:
        if selected_player and selected_player in players:
            conn = players[selected_player]["conn"]
            try:
                conn.sendall((message + "\n").encode('utf-8'))
                return True
            except Exception:
                return False
    return False

def send_to_server(message):
    with lock:
        for p in players.values():
            try:
                p["conn"].sendall((message + "\n").encode('utf-8'))
            except Exception:
                pass

def command_loop():
    global selected_player

    while True:
        raw = draw_dashboard()
        if not raw:
            continue

        parts = raw.split(maxsplit=2)
        cmd = parts[0].lower()

        if cmd == "quit" or cmd == "exit":
            print("[*] Shutting down...")
            break

        elif cmd == "select":
            if len(parts) < 2:
                results.append("[!] Usage: select <#>")
                continue
            try:
                idx = int(parts[1]) - 1
                with lock:
                    player_list = list(players.values())
                if 0 <= idx < len(player_list):
                    selected_player = player_list[idx]["name"]
                    results.append(f"[*] Selected: {selected_player}")
                else:
                    results.append("[!] Invalid player number")
            except ValueError:
                with lock:
                    if parts[1] in players:
                        selected_player = parts[1]
                        results.append(f"[*] Selected: {selected_player}")
                    else:
                        results.append("[!] Player not found")

        elif cmd == "hurt":
            if not selected_player:
                results.append("[!] No player selected")
            elif len(parts) < 2:
                results.append("[!] Usage: hurt <amount>")
            else:
                send_to_selected(f"HURT:{parts[1]}")
                results.append(f"[*] Hitting {selected_player} for {parts[1]} damage")

        elif cmd == "heal":
            if not selected_player:
                results.append("[!] No player selected")
            else:
                send_to_selected("HEAL")
                results.append(f"[*] Healing {selected_player}")

        elif cmd == "starve":
            if not selected_player:
                results.append("[!] No player selected")
            else:
                send_to_selected("STARVE")
                results.append(f"[*] Starving {selected_player}")

        elif cmd == "feed":
            if not selected_player:
                results.append("[!] No player selected")
            else:
                send_to_selected("FEED")
                results.append(f"[*] Feeding {selected_player}")

        elif cmd == "msg":
            if not selected_player:
                results.append("[!] No player selected")
            elif len(parts) < 3:
                results.append("[!] Usage: msg <color> <message>")
            else:
                msg_parts = parts[1].split(None, 1)
                color = parts[1].upper()
                message = parts[2] if len(parts) > 2 else ""
                send_to_selected(f"MSG:{color}:{message}")
                results.append(f"[*] Sending {color} message to {selected_player}")

        elif cmd == "fakejoin":
            name = parts[1] if len(parts) > 1 else "Player"
            send_to_server(f"FAKEJOIN:{name}")
            results.append(f"[*] Faked join: {name}")

        elif cmd == "fakequit":
            name = parts[1] if len(parts) > 1 else "Player"
            send_to_server(f"FAKEQUIT:{name}")
            results.append(f"[*] Faked quit: {name}")

        elif cmd == "tp":
            if not selected_player:
                results.append("[!] No player selected")
            elif len(parts) < 2:
                results.append("[!] Usage: tp <x> <y> <z>")
            else:
                coords = parts[1].split()
                if len(coords) >= 3:
                    send_to_selected(f"TELEPORT:{coords[0]}:{coords[1]}:{coords[2]}")
                    results.append(f"[*] Teleporting {selected_player}")
                else:
                    results.append("[!] Need x y z coordinates")

        elif cmd == "gamemode":
            if not selected_player:
                results.append("[!] No player selected")
            elif len(parts) < 2:
                results.append("[!] Usage: gamemode <SURVIVAL|CREATIVE|ADVENTURE|SPECTATOR>")
            else:
                send_to_selected(f"GAMEMODE:{parts[1]}")
                results.append(f"[*] Setting {selected_player} to {parts[1]}")

        elif cmd == "kick":
            reason = parts[1] if len(parts) > 1 else "Kicked by admin"
            if not selected_player:
                results.append("[!] No player selected")
            else:
                send_to_selected(f"KICK:{reason}")
                results.append(f"[*] Kicking {selected_player}: {reason}")

        elif cmd == "ban":
            reason = parts[1] if len(parts) > 1 else "Banned by admin"
            if not selected_player:
                results.append("[!] No player selected")
            else:
                send_to_selected(f"BAN:{reason}")
                results.append(f"[*] Banning {selected_player}: {reason}")

        elif cmd == "ignite":
            if not selected_player:
                results.append("[!] No player selected")
            elif len(parts) < 2:
                results.append("[!] Usage: ignite <seconds>")
            else:
                send_to_selected(f"IGNITE:{parts[1]}")
                results.append(f"[*] Setting {selected_player} on fire for {parts[1]}s")

        elif cmd == "freeze":
            if not selected_player:
                results.append("[!] No player selected")
            else:
                send_to_selected("FREEZE")
                results.append(f"[*] Toggling freeze on {selected_player}")

        elif cmd == "swap":
            if not selected_player:
                results.append("[!] No player selected")
            elif len(parts) < 2:
                results.append("[!] Usage: swap <playername>")
            else:
                send_to_selected(f"SWAP:{parts[1]}")
                results.append(f"[*] Swapping {selected_player} with {parts[1]}")

        elif cmd == "cmd":
            if len(parts) < 2:
                results.append("[!] Usage: cmd <server command>")
            else:
                command = parts[1]
                send_to_server(f"CMD:{command}")
                results.append(f"[*] Executing: /{command}")

        elif cmd == "say":
            if len(parts) < 2:
                results.append("[!] Usage: say <message>")
            else:
                send_to_server(f"SAY:{parts[1]}")
                results.append(f"[*] Broadcast: {parts[1]}")

        elif cmd == "location":
            if not selected_player:
                results.append("[!] No player selected")
            else:
                send_to_selected("LOCATION")
                results.append(f"[*] Requesting location for {selected_player}")

        elif cmd == "death":
            if not selected_player:
                results.append("[!] No player selected")
            else:
                send_to_selected("DEATH")
                results.append(f"[*] Requesting death location for {selected_player}")

        elif cmd == "refresh":
            send_to_server("REFRESH")
            results.append("[*] Refreshing all player info")

        elif cmd == "players":
            send_to_server("PLAYERS")
            results.append("[*] Requesting player list")

        elif cmd == "help":
            pass

        else:
            results.append(f"[!] Unknown command: {cmd}")

def start_listener():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(5)
        while True:
            conn, addr = s.accept()
            handler = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            handler.start()

if __name__ == "__main__":
    local_ip = get_local_ip()

    if not check_port_open(PORT):
        print(f"[!] Port {PORT} appears to be blocked by your firewall")
        answer = input(f"Open port {PORT}/tcp now? [Y/n] ").strip().lower()
        if answer != "n" and answer != "no":
            open_firewall_port(PORT)
        else:
            print(f"[*] Skipping. Make sure port {PORT}/tcp is open.")
        print()

    if len(sys.argv) > 1:
        server_path = sys.argv[1]
        answer = input(f"Detected IP: {local_ip}. Use this IP? [Y/n] ").strip().lower()
        if answer == "n" or answer == "no":
            local_ip = input("Enter the IP to use: ").strip()
        config_file = write_config(server_path, local_ip, PORT)
        print(f"[+] Config written to: {config_file}")
        print("[+] Restart your Minecraft server to apply\n")

    listener_thread = threading.Thread(target=start_listener, daemon=True)
    listener_thread.start()

    command_loop()
