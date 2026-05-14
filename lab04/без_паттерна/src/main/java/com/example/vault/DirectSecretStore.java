package com.example.vault;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

public class DirectSecretStore {

    public void save(Connection connection, String key, String encryptedPayload) throws SQLException {
        String sql = "MERGE INTO secrets (secret_key, payload) KEY (secret_key) VALUES (?, ?)";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, key);
            statement.setString(2, encryptedPayload);
            statement.executeUpdate();
        }
    }

    public String getPayload(Connection connection, String key) throws SQLException {
        String sql = "SELECT payload FROM secrets WHERE secret_key = ?";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, key);
            try (ResultSet rs = statement.executeQuery()) {
                if (rs.next()) {
                    return rs.getString("payload");
                }
                return null;
            }
        }
    }

    public List<String> getAllKeys(Connection connection) throws SQLException {
        List<String> keys = new ArrayList<>();
        String sql = "SELECT secret_key FROM secrets ORDER BY secret_key";
        try (Statement statement = connection.createStatement();
             ResultSet rs = statement.executeQuery(sql)) {
            while (rs.next()) {
                keys.add(rs.getString("secret_key"));
            }
        }
        return keys;
    }

    public void delete(Connection connection, String key) throws SQLException {
        String sql = "DELETE FROM secrets WHERE secret_key = ?";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, key);
            statement.executeUpdate();
        }
    }

    public void updateAllPayloads(Connection connection, List<String[]> data) throws SQLException {
        String sql = "UPDATE secrets SET payload = ? WHERE secret_key = ?";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            for (String[] row : data) {
                statement.setString(1, row[1]);
                statement.setString(2, row[0]);
                statement.addBatch();
            }
            statement.executeBatch();
        }
    }

    public void createTable(Connection connection) throws SQLException {
        try (Statement statement = connection.createStatement()) {
            statement.execute("CREATE TABLE IF NOT EXISTS secrets (secret_key VARCHAR(255) PRIMARY KEY, payload CLOB)");
        }
    }
}
