// DragonAIAgent.exe — first-party Dragon AI Agent Windows desktop.
//
// This is the product window. It is shipped with the Dragon package.
// It does not search for, copy, or launch a Hermes install.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const (
	productName = "Dragon AI Agent"
	productVer  = "0.1.0"
	uiPortPref  = "127.0.0.1:8655"
	gatewayAPI  = "http://127.0.0.1:8642"
	desktopSvc  = "http://127.0.0.1:8650"
	teamsSvc    = "http://127.0.0.1:8653"
	voiceSvc    = "http://127.0.0.1:8654"
	apiKey      = "dragon-local-key"
	sessionTok  = "dragon-local"
)

func installRoot() string {
	if v := os.Getenv("DRAGON_AI_INSTALL_ROOT"); strings.TrimSpace(v) != "" {
		return v
	}
	local := os.Getenv("LOCALAPPDATA")
	if local == "" {
		home, _ := os.UserHomeDir()
		local = filepath.Join(home, "AppData", "Local")
	}
	return filepath.Join(local, "DragonAIAgent")
}

func userDataDir() string {
	if v := os.Getenv("DRAGON_AI_USER_DATA_DIR"); strings.TrimSpace(v) != "" {
		return v
	}
	if v := os.Getenv("HERMES_DESKTOP_USER_DATA_DIR"); strings.TrimSpace(v) != "" {
		return v
	}
	return filepath.Join(installRoot(), "electron-userdata")
}

func pathsJSON() map[string]string {
	root := installRoot()
	return map[string]string{
		"product":     productName,
		"version":     productVer,
		"exe":         "desktop/win-unpacked/DragonAIAgent.exe",
		"installRoot": root,
		"userData":    userDataDir(),
		"ui":          "http://" + uiPortPref + "/",
		"gateway":     gatewayAPI,
		"desktop":     desktopSvc,
	}
}

func startUIServer(ui fs.FS) (addr string, stop func(), err error) {
	mux := http.NewServeMux()
	mux.HandleFunc("/api/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]any{
			"ok":      true,
			"product": productName,
			"paths":   pathsJSON(),
		})
	})
	mux.HandleFunc("/api/status", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]any{
			"gateway": probe(gatewayAPI+"/health", ""),
			"desktop": probe(desktopSvc+"/api/health", sessionTok),
			"teams":   probe(teamsSvc+"/api/health", ""),
		})
	})
	mux.HandleFunc("/api/chat", func(w http.ResponseWriter, r *http.Request) {
		proxy(w, r, gatewayAPI+"/v1/chat/completions", "Bearer "+apiKey, false)
	})
	mux.HandleFunc("/api/teams/", func(w http.ResponseWriter, r *http.Request) {
		suffix := strings.TrimPrefix(r.URL.Path, "/api/teams")
		if suffix == "" {
			suffix = "/api/teams"
		} else if !strings.HasPrefix(suffix, "/api/") {
			suffix = "/api/teams" + suffix
		}
		proxy(w, r, teamsSvc+suffix, "", true)
	})
	mux.HandleFunc("/api/voice/", func(w http.ResponseWriter, r *http.Request) {
		suffix := strings.TrimPrefix(r.URL.Path, "/api/voice")
		proxy(w, r, voiceSvc+"/api/voice"+suffix, "", true)
	})
	mux.HandleFunc("/vm/", func(w http.ResponseWriter, r *http.Request) {
		suffix := strings.TrimPrefix(r.URL.Path, "/vm")
		if suffix == "" {
			suffix = "/"
		}
		proxy(w, r, desktopSvc+suffix, sessionTok, true)
	})
	mux.Handle("/", http.FileServer(http.FS(ui)))

	ln, err := net.Listen("tcp", uiPortPref)
	if err != nil {
		ln, err = net.Listen("tcp", "127.0.0.1:0")
		if err != nil {
			return "", nil, err
		}
	}
	srv := &http.Server{Handler: mux}
	go func() { _ = srv.Serve(ln) }()
	return "http://" + ln.Addr().String() + "/", func() { _ = srv.Close() }, nil
}

func probe(url, token string) map[string]any {
	client := &http.Client{Timeout: 2 * time.Second}
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return map[string]any{"ok": false, "error": err.Error()}
	}
	if token != "" {
		req.Header.Set("X-Hermes-Session-Token", token)
	}
	res, err := client.Do(req)
	if err != nil {
		return map[string]any{"ok": false, "error": err.Error()}
	}
	defer res.Body.Close()
	return map[string]any{"ok": res.StatusCode >= 200 && res.StatusCode < 400, "status": res.StatusCode}
}

func proxy(w http.ResponseWriter, r *http.Request, dest, auth string, copyQuery bool) {
	client := &http.Client{Timeout: 120 * time.Second}
	var body io.Reader
	if r.Body != nil {
		body = r.Body
	}
	url := dest
	if copyQuery && r.URL.RawQuery != "" {
		url = dest + "?" + r.URL.RawQuery
	}
	req, err := http.NewRequest(r.Method, url, body)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}
	req.Header = r.Header.Clone()
	if auth != "" {
		req.Header.Set("Authorization", auth)
	}
	res, err := client.Do(req)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}
	defer res.Body.Close()
	for k, vs := range res.Header {
		for _, v := range vs {
			w.Header().Add(k, v)
		}
	}
	w.WriteHeader(res.StatusCode)
	_, _ = io.Copy(w, res.Body)
}

func main() {
	selfTest := flag.Bool("self-test", false, "print paths JSON and exit")
	serveOnly := flag.Bool("serve", false, "serve the Dragon AI Agent UI and block (Linux verification)")
	flag.Parse()
	if *selfTest {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		_ = enc.Encode(pathsJSON())
		os.Exit(0)
	}
	_ = os.MkdirAll(userDataDir(), 0o755)
	_ = os.MkdirAll(installRoot(), 0o755)
	ui, err := fs.Sub(uiFS, "ui")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Dragon AI Agent: missing UI pack: %v\n", err)
		os.Exit(1)
	}
	addr, stop, err := startUIServer(ui)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Dragon AI Agent: UI server failed: %v\n", err)
		os.Exit(1)
	}
	defer stop()
	if *serveOnly {
		fmt.Println(addr)
		select {}
	}
	if err := openDesktop(addr); err != nil {
		fmt.Fprintf(os.Stderr, "Dragon AI Agent: %v\n", err)
		os.Exit(1)
	}
}
