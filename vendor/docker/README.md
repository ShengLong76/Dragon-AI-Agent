# Packaged Docker Desktop installer

This folder is the Windows-zip slot for the official **Docker Desktop Installer**.

Dragon AI Agent Setup looks here first (`Docker Desktop Installer.exe` or `DockerDesktopInstaller.exe`) and runs a quiet install. If the file is missing, Setup downloads the same official installer itself. The user does not install Docker from docker.com first.

## Stage for a release zip

Do not commit the exe (it is large and third-party). When building `Dragon-AI-Agent-v0.1.0-windows.zip`:

```bash
python3 installer/stage-docker-desktop.py
```

That writes `vendor/docker/Docker Desktop Installer.exe` from `https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe`.

## License

Docker Desktop is Docker, Inc. software. See https://www.docker.com/legal/docker-subscription-service-agreement/ and `THIRD_PARTY_NOTICES.md`.
