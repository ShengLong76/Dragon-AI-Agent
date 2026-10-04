//go:build windows

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"unsafe"

	"github.com/jchv/go-webview2"
)

func showLaunchError(msg string) {
	user32 := syscall.NewLazyDLL("user32.dll")
	messageBoxW := user32.NewProc("MessageBoxW")
	title, _ := syscall.UTF16PtrFromString(productName)
	text, _ := syscall.UTF16PtrFromString(msg)
	_, _, _ = messageBoxW.Call(0, uintptr(unsafe.Pointer(text)), uintptr(unsafe.Pointer(title)), 0x10)
}

func openDesktop(url string) error {
	w := webview2.NewWithOptions(webview2.WebViewOptions{
		Debug:     false,
		AutoFocus: true,
		DataPath:  userDataDir(),
		WindowOptions: webview2.WindowOptions{
			Title:  productName,
			Width:  1280,
			Height: 800,
			Center: true,
			IconId: 1,
		},
	})
	if w != nil {
		defer w.Destroy()
		w.SetTitle(productName)
		w.SetSize(1280, 800, webview2.HintNone)
		w.Navigate(url)
		w.Run()
		return nil
	}
	if err := openEdgeApp(url); err != nil {
		showLaunchError("Dragon AI Agent could not open a window. " + err.Error())
		return err
	}
	return nil
}

func openEdgeApp(url string) error {
	candidates := []string{
		filepath.Join(os.Getenv("ProgramFiles(x86)"), `Microsoft\Edge\Application\msedge.exe`),
		filepath.Join(os.Getenv("ProgramFiles"), `Microsoft\Edge\Application\msedge.exe`),
		filepath.Join(os.Getenv("LOCALAPPDATA"), `Microsoft\Edge\Application\msedge.exe`),
	}
	edge := ""
	for _, c := range candidates {
		if c != "" {
			if st, err := os.Stat(c); err == nil && !st.IsDir() {
				edge = c
				break
			}
		}
	}
	if edge == "" {
		if p, err := exec.LookPath("msedge"); err == nil {
			edge = p
		}
	}
	if edge == "" {
		return fmt.Errorf("could not open the Dragon AI Agent window (WebView2 / Edge missing)")
	}
	profile := filepath.Join(userDataDir(), "edge-app")
	_ = os.MkdirAll(profile, 0o755)
	cmd := exec.Command(edge,
		"--app="+url,
		"--user-data-dir="+profile,
		"--no-first-run",
		"--no-default-browser-check",
	)
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: false}
	return cmd.Run()
}
