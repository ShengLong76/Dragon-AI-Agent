# Packaged Docker Desktop installer

This folder is the optional payload slot for the official **Docker Desktop Installer** inside the single installer exe.

Dragon AI Agent Setup looks here first (`Docker Desktop Installer.exe` or `DockerDesktopInstaller.exe`) and runs a quiet install. If the file is missing, Setup downloads the same official installer itself. The user does not install Docker from docker.com first.

## Stage for a release (optional)

Do not commit the exe (it is large and third-party). When embedding Docker into `DragonAIAgentSetup.exe`:

```bash
python3 installer/stage-docker-desktop.py
python3 installer/pack.py --out dist/DragonAIAgentSetup.exe --with-docker
```

That writes `vendor/docker/Docker Desktop Installer.exe` from `https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe` and embeds it in the single installer exe. Setup still downloads this same URL when the slot is empty.

## License

Docker Desktop is Docker, Inc. software. See https://www.docker.com/legal/docker-subscription-service-agreement/ and `THIRD_PARTY_NOTICES.md`.
