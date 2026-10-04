// DragonAIAgent.exe — first-party Dragon AI Agent Windows desktop.
//
// This is the product window. It is shipped with the Dragon package.
// The window loads the Hermes dashboard web UI (default :8660) and
// injects the Dragon overlay. It refuses the headless hermes serve
// page on :8650 ("web UI disabled").
package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

const (
	productName        = "Dragon AI Agent"
	productVer         = "0.1.0"
	uiPortPref         = "127.0.0.1:8655"
	gatewayAPI         = "http://127.0.0.1:8642"
	desktopSvc         = "http://127.0.0.1:8650"
	defaultDesktopUI   = "http://127.0.0.1:8660/"
	teamsSvc           = "http://127.0.0.1:8653"
	voiceSvc           = "http://127.0.0.1:8654"
	apiKey             = "dragon-local-key"
	sessionTok         = "dragon-local"
	headlessFixture    = "Headless backend (hermes serve): web UI disabled - use `hermes dashboard` for the browser UI."
	headlessRefuseText = "refusing headless hermes serve page (web UI disabled). Point the window at hermes dashboard."
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

func embeddedHome() string {
	if v := os.Getenv("HERMES_HOME"); strings.TrimSpace(v) != "" {
		return v
	}
	if v := os.Getenv("HERMES_EMBEDDED_HOME"); strings.TrimSpace(v) != "" {
		return v
	}
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".hermes-airmaze-embedded")
}

func desktopUIURL() string {
	if v := strings.TrimSpace(os.Getenv("DRAGON_AI_UI_URL")); v != "" {
		if !strings.HasSuffix(v, "/") {
			v += "/"
		}
		return v
	}
	return defaultDesktopUI
}

func isHeadlessPage(body string) bool {
	return strings.Contains(body, "web UI disabled") ||
		strings.Contains(body, "Headless backend (hermes serve)") ||
		strings.Contains(body, "use `hermes dashboard` for the browser UI") ||
		strings.Contains(body, "use 'hermes dashboard' for the browser UI")
}

func isHTMLPage(body string) bool {
	low := strings.ToLower(body)
	return strings.Contains(low, "<html") || strings.Contains(low, "<!doctype html")
}

func isDesktopWebUI(body string) bool {
	return isHTMLPage(body) && !isHeadlessPage(body)
}

func overlaySnippets() [][2]string {
	return [][2]string{
		{`data-dragon-ai-branding="ui-face"`, `<link rel="stylesheet" href="/dragon-ai-branding/dragon-ui.css" data-dragon-ai-branding="ui-face">`},
		{`data-dragon-ai-branding="sidebar-header"`, `<script src="/dragon-ai-branding/sidebar-header.js" data-dragon-ai-branding="sidebar-header"></script>`},
		{`data-dragon-ai-branding="teams-picker"`, `<script src="/dragon-ai-branding/teams-picker.js" data-dragon-ai-branding="teams-picker"></script>`},
		{`data-dragon-ai-branding="provider-setup"`, `<script src="/dragon-ai-branding/provider-setup.js" data-dragon-ai-branding="provider-setup"></script>`},
		{`data-dragon-ai-branding="bot-workspace"`, `<script src="/dragon-ai-branding/bot-workspace.js" data-dragon-ai-branding="bot-workspace"></script>`},
		{`data-dragon-ai-branding="first-run-models"`, `<script src="/dragon-ai-branding/first-run-models.js" data-dragon-ai-branding="first-run-models"></script>`},
		{`data-dragon-ai-branding="voice-provider"`, `<script src="/dragon-ai-branding/dragon-voice-selector.js" data-dragon-ai-branding="voice-provider"></script>`},
		{`data-dragon-ai-branding="voice-settings"`, `<script src="/dragon-ai-branding/dragon-voice-settings.js" data-dragon-ai-branding="voice-settings"></script>`},
	}
}

func injectOverlay(html string) string {
	var b strings.Builder
	for _, item := range overlaySnippets() {
		if !strings.Contains(html, item[0]) {
			b.WriteString(item[1])
			b.WriteByte('\n')
		}
	}
	insert := b.String()
	if insert == "" {
		return html
	}
	lower := strings.ToLower(html)
	if i := strings.Index(lower, "</head>"); i >= 0 {
		return html[:i] + insert + html[i:]
	}
	if i := strings.Index(lower, "</body>"); i >= 0 {
		return html[:i] + insert + html[i:]
	}
	return html + "\n" + insert
}

func fetchURL(raw string, token string, timeout time.Duration) (int, string, error) {
	client := &http.Client{Timeout: timeout}
	req, err := http.NewRequest(http.MethodGet, raw, nil)
	if err != nil {
		return 0, "", err
	}
	req.Header.Set("Accept", "text/html,*/*")
	if token != "" {
		req.Header.Set("X-Hermes-Session-Token", token)
	}
	res, err := client.Do(req)
	if err != nil {
		return 0, "", err
	}
	defer res.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(res.Body, 256*1024))
	return res.StatusCode, string(body), nil
}

func probeDesktopUI() map[string]any {
	url := desktopUIURL()
	status, body, err := fetchURL(url, "", 3*time.Second)
	if err != nil {
		return map[string]any{"ok": false, "url": url, "headless": false, "error": err.Error()}
	}
	headless := isHeadlessPage(body)
	html := isHTMLPage(body)
	ok := isDesktopWebUI(body)
	errMsg := ""
	if headless {
		errMsg = headlessRefuseText
	} else if !html {
		errMsg = "desktop UI is not an HTML page"
	}
	return map[string]any{
		"ok":       ok,
		"url":      url,
		"status":   status,
		"headless": headless,
		"html":     html,
		"error":    errMsg,
	}
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
		"window":      desktopUIURL(),
		"gateway":     gatewayAPI,
		"desktop":     desktopSvc,
	}
}

func startUIServer(ui fs.FS) (addr string, stop func(), err error) {
	upstream, err := url.Parse(desktopUIURL())
	if err != nil {
		return "", nil, err
	}
	proxy := httputil.NewSingleHostReverseProxy(upstream)
	director := proxy.Director
	proxy.Director = func(req *http.Request) {
		director(req)
		req.Host = upstream.Host
		req.Header.Del("Accept-Encoding")
	}
	proxy.ModifyResponse = func(res *http.Response) error {
		ct := strings.ToLower(res.Header.Get("Content-Type"))
		if !strings.Contains(ct, "text/html") && !strings.Contains(ct, "text/plain") {
			return nil
		}
		body, err := io.ReadAll(io.LimitReader(res.Body, 2*1024*1024))
		res.Body.Close()
		if err != nil {
			return err
		}
		text := string(body)
		if isHeadlessPage(text) {
			msg := []byte(headlessErrorHTML())
			res.StatusCode = http.StatusServiceUnavailable
			res.Header.Set("Content-Type", "text/html; charset=utf-8")
			res.Header.Set("Content-Length", strconv.Itoa(len(msg)))
			res.Header.Del("Content-Encoding")
			res.Body = io.NopCloser(bytes.NewReader(msg))
			res.ContentLength = int64(len(msg))
			return nil
		}
		if isHTMLPage(text) {
			out := []byte(injectOverlay(text))
			res.Header.Set("Content-Type", "text/html; charset=utf-8")
			res.Header.Set("Content-Length", strconv.Itoa(len(out)))
			res.Header.Del("Content-Encoding")
			res.Body = io.NopCloser(bytes.NewReader(out))
			res.ContentLength = int64(len(out))
			return nil
		}
		res.Body = io.NopCloser(bytes.NewReader(body))
		res.ContentLength = int64(len(body))
		return nil
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/api/health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]any{"ok": true, "product": productName, "paths": pathsJSON()})
	})
	mux.HandleFunc("/api/status", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]any{
			"gateway": probe(gatewayAPI+"/health", ""),
			"desktop": probe(desktopSvc+"/api/health", sessionTok),
			"webUI":   probeDesktopUI(),
			"teams":   probe(teamsSvc+"/api/health", ""),
		})
	})
	mux.HandleFunc("/api/chat", func(w http.ResponseWriter, r *http.Request) {
		proxyJSON(w, r, gatewayAPI+"/v1/chat/completions", "Bearer "+apiKey, false)
	})
	mux.HandleFunc("/api/teams/", func(w http.ResponseWriter, r *http.Request) {
		suffix := strings.TrimPrefix(r.URL.Path, "/api/teams")
		if suffix == "" {
			suffix = "/api/teams"
		} else if !strings.HasPrefix(suffix, "/api/") {
			suffix = "/api/teams" + suffix
		}
		proxyJSON(w, r, teamsSvc+suffix, "", true)
	})
	mux.HandleFunc("/api/voice/", func(w http.ResponseWriter, r *http.Request) {
		suffix := strings.TrimPrefix(r.URL.Path, "/api/voice")
		proxyJSON(w, r, voiceSvc+"/api/voice"+suffix, "", true)
	})
	mux.HandleFunc("/api/launch", handleLaunch)
	mux.HandleFunc("/dragon-ai-api/launch", handleLaunch)
	mux.HandleFunc("/api/models", handleModels)
	mux.HandleFunc("/dragon-ai-api/models", handleModels)
	mux.HandleFunc("/dragon-ai-api/desktop-ui", func(w http.ResponseWriter, r *http.Request) {
		result := probeDesktopUI()
		status := http.StatusOK
		if result["ok"] != true {
			status = http.StatusServiceUnavailable
		}
		writeJSON(w, status, result)
	})
	mux.HandleFunc("/bot-screen/", func(w http.ResponseWriter, r *http.Request) {
		suffix := strings.TrimPrefix(r.URL.Path, "/bot-screen")
		if suffix == "" || suffix == "/" {
			suffix = "/api/health"
		}
		proxyJSON(w, r, desktopSvc+suffix, sessionTok, true)
	})
	mux.Handle("/dragon-ai-branding/", brandingHandler(ui))
	files := http.FileServer(http.FS(ui))
	mux.Handle("/dragon-ai-agent-logo.png", files)
	mux.Handle("/dragon-ai-agent-logo.svg", files)
	mux.Handle("/app.css", files)
	mux.Handle("/app.js", files)
	mux.HandleFunc("/vm/", func(w http.ResponseWriter, r *http.Request) {
		suffix := strings.TrimPrefix(r.URL.Path, "/vm")
		if suffix == "" {
			suffix = "/"
		}
		proxyJSON(w, r, desktopSvc+suffix, sessionTok, true)
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodGet && (r.URL.Path == "/" || r.URL.Path == "/index.html") {
			handleWindowRoot(w, r, ui)
			return
		}
		proxy.ServeHTTP(w, r)
	})

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

func handleWindowRoot(w http.ResponseWriter, _ *http.Request, ui fs.FS) {
	status, body, err := fetchURL(desktopUIURL(), "", 4*time.Second)
	if err != nil {
		serveLoader(w, ui, "Opening the desktop chat screen...")
		return
	}
	if isHeadlessPage(body) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.WriteHeader(http.StatusServiceUnavailable)
		_, _ = w.Write([]byte(headlessErrorHTML()))
		return
	}
	if isHTMLPage(body) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.WriteHeader(status)
		_, _ = w.Write([]byte(injectOverlay(body)))
		return
	}
	serveLoader(w, ui, "Opening the desktop chat screen...")
}

func serveLoader(w http.ResponseWriter, ui fs.FS, status string) {
	raw, err := fs.ReadFile(ui, "index.html")
	if err != nil {
		http.Error(w, "Dragon AI Agent loader missing", http.StatusInternalServerError)
		return
	}
	html := strings.ReplaceAll(string(raw), "Opening the desktop chat screen...", status)
	html = strings.Replace(html, "<body>", `<body data-dragon-ai-loader="desktop-web-ui">`, 1)
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_, _ = w.Write([]byte(html))
}

func handleLaunch(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost && r.Method != http.MethodGet {
		writeJSON(w, http.StatusMethodNotAllowed, launchResult(false, "launch", "", "Launch only accepts GET or POST"))
		return
	}
	probe := probeDesktopUI()
	if probe["headless"] == true {
		writeJSON(w, http.StatusServiceUnavailable, launchResult(false, "launch", "", headlessRefuseText))
		return
	}
	if probe["ok"] != true {
		errMsg, _ := probe["error"].(string)
		if errMsg == "" {
			errMsg = "desktop web UI is not ready"
		}
		writeJSON(w, http.StatusServiceUnavailable, launchResult(false, "launch", "", errMsg))
		return
	}
	writeJSON(w, http.StatusOK, launchResult(true, "launch", "Dragon AI Agent window is running on the desktop web UI.", ""))
}

func handleModels(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		saved := false
		if _, err := os.Stat(modelsPath()); err == nil {
			saved = true
		}
		writeJSON(w, http.StatusOK, map[string]any{
			"ok":         true,
			"saved":      saved,
			"chatModel":  "grok-4.7",
			"imageModel": "grok-imagine-image",
			"provider":   "xai",
		})
		return
	}
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]any{"ok": false, "error": "POST required"})
		return
	}
	var body map[string]any
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{"ok": false, "error": "invalid models payload"})
		return
	}
	chat, _ := body["chat"].(string)
	if chat == "" {
		chat, _ = body["chatModel"].(string)
	}
	image, _ := body["image"].(string)
	if image == "" {
		image, _ = body["imageModel"].(string)
	}
	if chat == "" {
		chat = "grok-4.7"
	}
	if image == "" {
		image = "grok-imagine-image"
	}
	ifMissing, _ := body["ifMissing"].(bool)
	_ = os.MkdirAll(userDataDir(), 0o755)
	raw, _ := json.MarshalIndent(map[string]any{
		"chat":      chat,
		"image":     image,
		"provider":  "xai",
		"ifMissing": ifMissing,
	}, "", "  ")
	if err := os.WriteFile(modelsPath(), raw, 0o644); err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]any{"ok": false, "error": err.Error()})
		return
	}
	applied := applyGatewayModels(chat, image, ifMissing)
	writeJSON(w, http.StatusOK, map[string]any{
		"ok":      true,
		"saved":   modelsPath(),
		"chat":    chat,
		"image":   image,
		"applied": applied,
	})
}

func applyGatewayModels(chat, image string, ifMissing bool) map[string]any {
	engine := filepath.Join(installRoot(), "scripts", "airmaze", "gateway_models.py")
	if _, err := os.Stat(engine); err != nil {
		return map[string]any{"ok": false, "error": "gateway_models.py missing"}
	}
	py := lookPathPython()
	if py == "" {
		return map[string]any{"ok": false, "error": "python3 is required to write gateway model defaults"}
	}
	args := []string{engine, "apply", "--home", embeddedHome(), "--chat", chat, "--image", image}
	if ifMissing {
		args = append(args, "--if-missing")
	}
	cmd := exec.Command(py, args...)
	out, err := cmd.CombinedOutput()
	if err != nil {
		return map[string]any{"ok": false, "error": strings.TrimSpace(string(out) + " " + err.Error())}
	}
	var parsed any
	if json.Unmarshal(out, &parsed) == nil {
		return map[string]any{"ok": true, "result": parsed}
	}
	return map[string]any{"ok": true, "result": strings.TrimSpace(string(out))}
}

func lookPathPython() string {
	for _, name := range []string{"python3", "python", "py"} {
		if p, err := exec.LookPath(name); err == nil {
			return p
		}
	}
	return ""
}

func brandingHandler(ui fs.FS) http.Handler {
	dir := brandingDir()
	var files http.Handler
	if dir != "" {
		files = http.FileServer(http.Dir(dir))
	} else if sub, err := fs.Sub(ui, "branding"); err == nil {
		files = http.FileServer(http.FS(sub))
	} else {
		files = http.NotFoundHandler()
	}
	voice := voiceDir()
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		name := strings.TrimPrefix(r.URL.Path, "/dragon-ai-branding/")
		if voice != "" && (name == "dragon-voice-selector.js" || name == "dragon-voice-settings.js") {
			http.ServeFile(w, r, filepath.Join(voice, name))
			return
		}
		r.URL.Path = "/" + name
		files.ServeHTTP(w, r)
	})
}

func brandingDir() string {
	candidates := []string{
		filepath.Join(installRoot(), "branding", "fonts", "syne"),
		filepath.Join(exeDir(), "branding"),
	}
	for _, dir := range candidates {
		if st, err := os.Stat(filepath.Join(dir, "first-run-models.js")); err == nil && !st.IsDir() {
			return dir
		}
		if st, err := os.Stat(filepath.Join(dir, "provider-setup.js")); err == nil && !st.IsDir() {
			return dir
		}
		if st, err := os.Stat(filepath.Join(dir, "bot-workspace.js")); err == nil && !st.IsDir() {
			return dir
		}
	}
	return ""
}

func voiceDir() string {
	candidates := []string{
		filepath.Join(installRoot(), "branding", "voice"),
		filepath.Join(exeDir(), "branding"),
	}
	for _, dir := range candidates {
		if st, err := os.Stat(filepath.Join(dir, "dragon-voice-selector.js")); err == nil && !st.IsDir() {
			return dir
		}
	}
	return ""
}

func exeDir() string {
	p, err := os.Executable()
	if err != nil {
		return ""
	}
	return filepath.Dir(p)
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

func proxyJSON(w http.ResponseWriter, r *http.Request, dest, auth string, copyQuery bool) {
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

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func modelsPath() string {
	return filepath.Join(userDataDir(), "models.json")
}

func launchResult(ok bool, action, message, errMsg string) map[string]any {
	return map[string]any{
		"ok":               ok,
		"action":           action,
		"message":          message,
		"error":            errMsg,
		"ui":               "http://" + uiPortPref + "/",
		"window":           desktopUIURL(),
		"rejectedHeadless": true,
		"exe":              "desktop/win-unpacked/DragonAIAgent.exe",
	}
}

func headlessErrorHTML() string {
	return `<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Dragon AI Agent</title>
<link rel="icon" type="image/png" href="/dragon-ai-agent-logo.png">
<style>body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
background:#1c1c20;color:#f0f0f5;font-family:Syne,ui-sans-serif,system-ui,sans-serif;text-align:center}
main{max-width:28rem;padding:2rem}h1{font-size:1.4rem}p{color:#c4c4ce;line-height:1.45}</style>
</head><body data-dragon-ai-headless-refused="1"><main>
<img src="/dragon-ai-agent-logo.png" width="56" height="56" alt="">
<h1>Dragon AI Agent</h1>
<p>The desktop chat screen did not load. The window refused the headless hermes serve page (web UI disabled). Open the dashboard web UI, not port 8650.</p>
</main></body></html>`
}

func main() {
	selfTest := flag.Bool("self-test", false, "print paths JSON and exit")
	launchCheck := flag.Bool("launch-check", false, "start the UI server, print a launch result, and exit")
	serveOnly := flag.Bool("serve", false, "serve the Dragon AI Agent UI and block (Linux verification)")
	flag.Parse()
	if !isHeadlessPage(headlessFixture) || isDesktopWebUI(headlessFixture) {
		fmt.Fprintln(os.Stderr, "Dragon AI Agent: headless page detector failed its fixture")
		os.Exit(1)
	}
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
		if *launchCheck {
			_ = json.NewEncoder(os.Stdout).Encode(launchResult(false, "launch", "", "UI server failed: "+err.Error()))
		} else {
			fmt.Fprintf(os.Stderr, "Dragon AI Agent: UI server failed: %v\n", err)
		}
		os.Exit(1)
	}
	defer stop()
	if *launchCheck {
		result := launchResult(true, "launch-check", "UI server accepted launch.", "")
		result["headlessFixtureRefused"] = isHeadlessPage(headlessFixture)
		_ = json.NewEncoder(os.Stdout).Encode(result)
		return
	}
	if *serveOnly {
		fmt.Println(addr)
		select {}
	}
	if err := openDesktop(addr); err != nil {
		fmt.Fprintf(os.Stderr, "Dragon AI Agent: %v\n", err)
		os.Exit(1)
	}
}
