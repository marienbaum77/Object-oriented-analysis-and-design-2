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

        DirectSecretStore store = new DirectSecretStore("jdbc:h2:file:./vaultdb-no-pattern;AUTO_SERVER=TRUE", masterPassword.toCharArray());
        printHelp();

        while (true) {
            System.out.print("vault> ");
            String command = scanner.nextLine().trim().toLowerCase();
            if (command.isEmpty()) {
                continue;
            }
            switch (command) {
                case "save" -> handleSave(scanner, store);
                case "get" -> handleGet(scanner, store);
                case "list" -> handleList(store);
                case "remove" -> handleRemove(scanner, store);
                case "rekey" -> handleRekey(scanner, store);
                case "help" -> printHelp();
                case "exit", "quit" -> {
                    System.out.println("Bye.");
                    return;
                }
                default -> System.out.println("Unknown command. Type 'help' for available commands.");
            }
        }
    }

    private static void handleSave(Scanner scanner, DirectSecretStore store) {
        System.out.print("Secret key: ");
        String key = scanner.nextLine().trim();
        System.out.print("Secret content: ");
        String content = scanner.nextLine();
        store.save(key, content);
        System.out.println("Secret saved.");
    }

    private static void handleGet(Scanner scanner, DirectSecretStore store) {
        System.out.print("Secret key: ");
        String key = scanner.nextLine().trim();
        String content = store.get(key);
        if (content == null) {
            System.out.println("Secret not found.");
        } else {
            System.out.println("Content: " + content);
        }
    }

    private static void handleList(DirectSecretStore store) {
        List<String> keys = store.listKeys();
        if (keys.isEmpty()) {
            System.out.println("No secrets stored.");
            return;
        }
        System.out.println("Stored keys:");
        keys.forEach(key -> System.out.println(" - " + key));
    }

    private static void handleRemove(Scanner scanner, DirectSecretStore store) {
        System.out.print("Secret key: ");
        String key = scanner.nextLine().trim();
        store.remove(key);
        System.out.println("Secret removed if it existed.");
    }

    private static void handleRekey(Scanner scanner, DirectSecretStore store) {
        System.out.print("Old master password: ");
        String oldPassword = scanner.nextLine().trim();
        System.out.print("New master password: ");
        String newPassword = scanner.nextLine().trim();
        store.rekey(oldPassword, newPassword);
        System.out.println("Rekey completed.");
    }

    private static void printHelp() {
        System.out.println("Available commands: save, get, list, remove, rekey, help, exit");
    }
}
