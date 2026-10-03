# Dragon AI Agent desktop

This folder is the first-party Windows app. The product window is **Dragon AI Agent**, not a Hermes.exe the user has to provide.

## Layout

```text
desktop/
  main.go                 Windows host (WebView2, Edge --app fallback)
  ui/                     Chat / Models / Teams Marketplace
  win-unpacked/
    DragonAIAgent.exe     Cross-compiled product exe
```

Install copies `win-unpacked` to `%LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked`.

## Build

```bash
cd desktop
GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -ldflags="-H windowsgui -s -w" -o win-unpacked/DragonAIAgent.exe .
go run . --self-test
```

Self-test prints install / userdata paths. It does not search for a Hermes install.
