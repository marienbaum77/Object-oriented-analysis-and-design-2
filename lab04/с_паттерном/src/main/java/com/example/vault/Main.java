package com.example.vault;

import java.util.List;
import java.util.Optional;
import java.util.Scanner;

public final class Main {
    private Main() {
        throw new IllegalStateException("Main class");
    }

    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        System.out.print("Enter master password: ");
        String masterPassword = scanner.nextLine().trim();

        SecretGateway gateway = new DbSecretGateway("jdbc:h2:file:./vaultdb;AUTO_SERVER=TRUE", masterPassword.toCharArray());
        printHelp();

        while (true) {
            System.out.print("vault> ");
            String command = scanner.nextLine().trim().toLowerCase();
            if (command.isEmpty()) {
                continue;
            }
            switch (command) {
                case "save" -> handleSave(scanner, gateway);
                case "get" -> handleGet(scanner, gateway);
                case "list" -> handleList(gateway);
                case "remove" -> handleRemove(scanner, gateway);
                case "rekey" -> handleRekey(scanner, gateway);
                case "help" -> printHelp();
                case "exit", "quit" -> {
                    System.out.println("Bye.");
                    return;
                }
                default -> System.out.println("Unknown command. Type 'help' for available commands.");
            }
        }
    }

    private static void handleSave(Scanner scanner, SecretGateway gateway) {
        System.out.print("Secret key: ");
        String key = scanner.nextLine().trim();
        System.out.print("Secret content: ");
        String content = scanner.nextLine();
        gateway.save(new SecretEntry(key, content));
        System.out.println("Secret saved.");
    }

    private static void handleGet(Scanner scanner, SecretGateway gateway) {
        System.out.print("Secret key: ");
        String key = scanner.nextLine().trim();
        Optional<SecretEntry> entry = gateway.findByKey(key);
        if (entry.isPresent()) {
            System.out.println("Content: " + entry.get().getContent());
        } else {
            System.out.println("Secret not found.");
        }
    }

    private static void handleList(SecretGateway gateway) {
        List<String> keys = gateway.listAllKeys();
        if (keys.isEmpty()) {
            System.out.println("No secrets stored.");
            return;
        }
        System.out.println("Stored keys:");
        keys.forEach(key -> System.out.println(" - " + key));
    }

    private static void handleRemove(Scanner scanner, SecretGateway gateway) {
        System.out.print("Secret key: ");
        String key = scanner.nextLine().trim();
        gateway.remove(key);
        System.out.println("Secret removed if it existed.");
    }

    private static void handleRekey(Scanner scanner, SecretGateway gateway) {
        System.out.print("Old master password: ");
        String oldPassword = scanner.nextLine().trim();
        System.out.print("New master password: ");
        String newPassword = scanner.nextLine().trim();
        gateway.rekey(oldPassword, newPassword);
        System.out.println("Rekey completed.");
    }

    private static void printHelp() {
        System.out.println("Available commands: save, get, list, remove, rekey, help, exit");
    }
}
