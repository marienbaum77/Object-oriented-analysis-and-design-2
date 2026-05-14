@echo off
setlocal
if defined JAVA_HOME (
  "%JAVA_HOME%\bin\jpackage.exe" --input target --name secure-vault-cli --main-jar secure-vault-cli-1.0.0-jar-with-dependencies.jar --main-class com.example.vault.Main --type app-image --win-console --dest package
) else (
  jpackage --input target --name secure-vault-cli --main-jar secure-vault-cli-1.0.0-jar-with-dependencies.jar --main-class com.example.vault.Main --type app-image --win-console --dest package
)
endlocal
