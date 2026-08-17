# mcRAT - Minecraft Network Listener Example

A teaching example for cybersecurity students that demonstrates basic network communication concepts using a Minecraft server plugin and a Python socket listener. This project is designed to illustrate how TCP socket connections, event-driven programming, and client-server communication work in practice.

**This is strictly for educational use in controlled lab environments. Do not deploy this on networks or servers you do not own.**

## What This Demonstrates

- Bukkit/Spigot plugin event handling (listening for player join events)
- Establishing outbound TCP connections from a Java application
- A Python socket server that accepts and displays incoming connections
- Basic threading for handling multiple concurrent clients
- The anatomy of a simple command-and-control communication pattern

## Project Structure

```
mcRAT/
├── serverphysics.java    # Bukkit plugin (Java) - connects to listener on player join
├── serverphysics.jar     # Pre-built plugin JAR (compiled for MC 26.2 / Java 25)
├── wizardlistener.py     # Socket listener (Python) - receives and displays connections
├── MANIFEST.MF           # JAR manifest for the compiled plugin
└── lib/
    ├── paper-api-26.2.jar    # Paper API 26.2 (primary dependency)
    ├── adventure-api.jar     # Adventure text library (transitive dep)
    ├── adventure-key.jar     # Adventure key library (transitive dep)
    └── annotations.jar       # JetBrains annotations (transitive dep)
```

## Prerequisites

- Java Development Kit (JDK 25+)
- Python 3.x
- A Paper or Spigot Minecraft server (version 26.2) for testing the plugin side

## Building the Plugin JAR

A pre-built `serverphysics.jar` is included. To rebuild from source:

```bash
export JAVA_HOME=/usr/lib/jvm/java-26-openjdk
CP="lib/paper-api-26.2.jar:lib/adventure-api.jar:lib/adventure-key.jar:lib/annotations.jar"

# Compile targeting Java 25 bytecode
mkdir -p out/com/example/wizard
cp serverphysics.java /tmp/InfectedServer.java
$JAVA_HOME/bin/javac --release 25 -cp "$CP" -d out /tmp/InfectedServer.java

# Package into a JAR
$JAVA_HOME/bin/jar cmf MANIFEST.MF serverphysics.jar -C out com/
rm -rf out /tmp/InfectedServer.java
```

The resulting `serverphysics.jar` can be placed in your Minecraft server's `plugins/` directory.

## Running the Listener

```bash
python3 wizardlistener.py
```

The listener binds to `0.0.0.0:443` and waits for incoming connections. Any data sent by the plugin will be printed to the console.

## How It Works

1. The Python listener starts and binds to a port, waiting for connections.
2. A player joins the Minecraft server, triggering the `PlayerJoinEvent` in the plugin.
3. The plugin opens a new TCP socket and connects to the configured listener address.
4. The plugin sends a `PLAYER_CONNECTED:<username>` message over the socket.
5. The listener receives the message and prints it to the console.

## Configuration

In `serverphysics.java`, update the following constants before compiling:

```java
private static final String ATTACKER_IP = "YOUR_PUBLIC_ATTACKER_IP";
private static final int PORT = 443;
```

Set `ATTACKER_IP` to the address where your Python listener is running.

## Extending This Example

Students can extend this project by:

- Adding command parsing on the listener side to send instructions back to the plugin
- Implementing encrypted communication (e.g., wrapping the socket in TLS)
- Adding authentication so only authorized listeners can connect
- Logging connection events to a file or database
- Exploring how real-world C2 frameworks handle persistence and encryption

## Disclaimer

This project exists solely as a teaching aid for understanding network security concepts. It should only be used in authorized educational settings such as CTF competitions, cybersecurity courses, or isolated lab environments. The authors are not responsible for misuse.
