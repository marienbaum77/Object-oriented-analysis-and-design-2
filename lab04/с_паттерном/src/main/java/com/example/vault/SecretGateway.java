package com.example.vault;

import java.util.List;
import java.util.Optional;

public interface SecretGateway {
    void save(SecretEntry entry);
    Optional<SecretEntry> findByKey(String key);
    List<String> listAllKeys();
    void remove(String key);
    void rekey(String oldPassword, String newPassword);
}
