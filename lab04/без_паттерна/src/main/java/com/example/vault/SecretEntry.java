package com.example.vault;

public final class SecretEntry {
    private final String key;
    private final String content;

    public SecretEntry(String key, String content) {
        this.key = key;
        this.content = content;
    }

    public String getKey() {
        return key;
    }

    public String getContent() {
        return content;
    }
}
