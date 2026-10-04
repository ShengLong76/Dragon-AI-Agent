# Dragon AI Agent desktop

This folder is the first-party Windows app. The product window is **Dragon AI Agent**, not a Hermes.exe the user has to provide.

## Layout

```text
desktop/
  main.go                 Windows host (WebView2, Edge --app fallback)
  ui/                     Thin loader + branding inject. The window loads hermes dashboard (:8660).
  winres/icon.ico         Current branding ICO (resource id 1)
  win-unpacked/
    DragonAIAgent.exe     Cross-compiled product exe with that ICO embedded
```

Install copies `win-unpacked` to `%LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked`.

## Build

```bash
python3 desktop/build-windows.py
go run . --self-test
go run . --launch-check
```

`build-windows.py` copies `branding/dragon-ai-agent-logo.ico` into `desktop/winres/icon.ico`, embeds it with go-winres as resource id 1, then cross-compiles. Do not ship an exe that still contains `Gateway ready` or omits the current ICO frames.

Self-test prints install / userdata paths. Launch-check prints a JSON result (`ok` / `action` / `error`). It does not search for a Hermes install.
