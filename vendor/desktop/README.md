# Packaged Dragon AI Agent desktop

This folder is an optional Windows-zip slot for `DragonAIAgent.exe` if Cos stages it beside the Docker installer.

The source of truth is `desktop/win-unpacked/DragonAIAgent.exe` (built from `desktop/`). Setup copies that tree into `%LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked`. It does not search for a Hermes install.
