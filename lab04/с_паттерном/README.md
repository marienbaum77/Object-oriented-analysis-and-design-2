# Secure Vault CLI

A simple secure vault CLI using the Gateway Pattern, AES-256/GCM encryption, and H2 file-mode storage.

## Build

Requires Java 17+.

```bash
cd c:\Users\igor\Desktop\lab04
mvn package
```

> If Maven cannot download dependencies, ensure a network connection or populate your local Maven repository with the H2 artifact.

## Run

```bash
java -jar target/secure-vault-cli-1.0.0-jar-with-dependencies.jar
```

## Native portable build

A native Windows package is generated into `package\secure-vault-cli`.

Run it directly without a separate Java installation:

```bash
package\secure-vault-cli\secure-vault-cli.exe
```

To rebuild the native image locally:

```bash
build-native.cmd
```

## Commands

- `save` - store a secret key and content
- `get` - retrieve plaintext content by key
- `list` - list all secret keys
- `remove` - delete a secret
- `rekey` - re-encrypt all records under a new master password
- `help` - show help
- `exit` - quit
