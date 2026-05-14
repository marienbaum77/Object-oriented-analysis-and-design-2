package com.example.vault;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;

public class DbSecretGateway implements SecretGateway {
    private final String jdbcUrl;
    private char[] masterPassword;

    public DbSecretGateway(String jdbcUrl, char[] masterPassword) {
        this.jdbcUrl = jdbcUrl;
        this.masterPassword = Arrays.copyOf(masterPassword, masterPassword.length);
        initDatabase();
    }

    @Override
    public void save(SecretEntry entry) {
        String encrypted = CryptoService.encrypt(entry.getContent(), masterPassword);
        try (Connection connection = DriverManager.getConnection(jdbcUrl);
             PreparedStatement statement = connection.prepareStatement(
                     "MERGE INTO secrets (secret_key, payload) KEY (secret_key) VALUES (?, ?)")
        ) {
            statement.setString(1, entry.getKey());
            statement.setString(2, encrypted);
            statement.executeUpdate();
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to save secret", e);
        }
    }

    @Override
    public Optional<SecretEntry> findByKey(String key) {
        try (Connection connection = DriverManager.getConnection(jdbcUrl);
             PreparedStatement statement = connection.prepareStatement(
                     "SELECT payload FROM secrets WHERE secret_key = ?")
        ) {
            statement.setString(1, key);
            try (ResultSet rs = statement.executeQuery()) {
                if (!rs.next()) {
                    return Optional.empty();
                }
                String payload = rs.getString("payload");
                String content = CryptoService.decrypt(payload, masterPassword);
                return Optional.of(new SecretEntry(key, content));
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to query secret", e);
        }
    }

    @Override
    public List<String> listAllKeys() {
        List<String> keys = new ArrayList<>();
        try (Connection connection = DriverManager.getConnection(jdbcUrl);
             Statement statement = connection.createStatement();
             ResultSet rs = statement.executeQuery("SELECT secret_key FROM secrets ORDER BY secret_key")
        ) {
            while (rs.next()) {
                keys.add(rs.getString("secret_key"));
            }
            return keys;
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to list keys", e);
        }
    }

    @Override
    public void remove(String key) {
        try (Connection connection = DriverManager.getConnection(jdbcUrl);
             PreparedStatement statement = connection.prepareStatement(
                     "DELETE FROM secrets WHERE secret_key = ?")
        ) {
            statement.setString(1, key);
            statement.executeUpdate();
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to remove secret", e);
        }
    }

    @Override
    public void rekey(String oldPassword, String newPassword) {
        char[] oldPasswordChars = oldPassword.toCharArray();
        char[] newPasswordChars = newPassword.toCharArray();
        try (Connection connection = DriverManager.getConnection(jdbcUrl)) {
            connection.setAutoCommit(false);
            try (PreparedStatement select = connection.prepareStatement("SELECT secret_key, payload FROM secrets");
                 PreparedStatement update = connection.prepareStatement(
                         "UPDATE secrets SET payload = ? WHERE secret_key = ?")
            ) {
                try (ResultSet rs = select.executeQuery()) {
                    while (rs.next()) {
                        String key = rs.getString("secret_key");
                        String payload = rs.getString("payload");
                        String decrypted = CryptoService.decrypt(payload, oldPasswordChars);
                        String reencrypted = CryptoService.encrypt(decrypted, newPasswordChars);
                        update.setString(1, reencrypted);
                        update.setString(2, key);
                        update.addBatch();
                    }
                }
                update.executeBatch();
                connection.commit();
                overwriteMasterPassword(newPasswordChars);
            }
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to rekey secrets", e);
        } finally {
            Arrays.fill(oldPasswordChars, '\0');
            Arrays.fill(newPasswordChars, '\0');
        }
    }

    private void initDatabase() {
        try (Connection connection = DriverManager.getConnection(jdbcUrl);
             Statement statement = connection.createStatement()) {
            statement.execute("CREATE TABLE IF NOT EXISTS secrets (secret_key VARCHAR(255) PRIMARY KEY, payload CLOB)");
        } catch (SQLException e) {
            throw new IllegalStateException("Unable to initialize database", e);
        }
    }

    private void overwriteMasterPassword(char[] replacement) {
        Arrays.fill(masterPassword, '\0');
        masterPassword = Arrays.copyOf(replacement, replacement.length);
    }
}
