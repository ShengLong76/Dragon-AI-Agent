// DragonAIAgentSetup - single-file Windows installer for Dragon AI Agent.
//
//	python3 installer/pack-payload.py
//	GOOS=windows GOARCH=amd64 go build -o DragonAIAgentSetup.exe .
//
// The exe embeds payload.zip. It extracts that payload and runs install.ps1.
// It is not a zip with a second exe beside it.
package main

import (
	"archive/zip"
	"bytes"
	_ "embed"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

//go:embed embed/payload.zip
var payloadZip []byte

func main() {
	fmt.Println("Dragon AI Agent Setup v0.1.0")
	fmt.Println()

	if len(payloadZip) < 64 {
		fmt.Fprintln(os.Stderr, "DragonAIAgentSetup: embedded payload is empty. Rebuild with installer/pack-payload.py.")
		os.Exit(1)
	}

	work, err := os.MkdirTemp("", "DragonAIAgentSetup-*")
	if err != nil {
		fmt.Fprintf(os.Stderr, "DragonAIAgentSetup: cannot create temp dir: %v\n", err)
		os.Exit(1)
	}
	defer os.RemoveAll(work)

	if err := unzipBytes(payloadZip, work); err != nil {
		fmt.Fprintf(os.Stderr, "DragonAIAgentSetup: cannot extract payload: %v\n", err)
		os.Exit(1)
	}

	script, payloadRoot, err := findInstallScript(work)
	if err != nil {
		fmt.Fprintf(os.Stderr, "DragonAIAgentSetup: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("Installing Dragon AI Agent...")
	cmd := exec.Command(
		"powershell.exe",
		"-NoProfile",
		"-ExecutionPolicy", "Bypass",
		"-File", script,
		"-PayloadRoot", payloadRoot,
	)
	cmd.Dir = payloadRoot
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		if ee, ok := err.(*exec.ExitError); ok {
			os.Exit(ee.ExitCode())
		}
		fmt.Fprintf(os.Stderr, "DragonAIAgentSetup: failed to run PowerShell: %v\n", err)
		os.Exit(1)
	}
}

func findInstallScript(root string) (script string, payloadRoot string, err error) {
	candidates := []string{
		filepath.Join(root, "payload", "install.ps1"),
		filepath.Join(root, "install.ps1"),
		filepath.Join(root, "scripts", "airmaze", "install.ps1"),
		filepath.Join(root, "DragonAIAgentSetup.ps1"),
	}
	for _, c := range candidates {
		if st, err := os.Stat(c); err == nil && !st.IsDir() {
			dir := filepath.Dir(c)
			if strings.HasSuffix(strings.ToLower(dir), `\scripts\airmaze`) || strings.HasSuffix(dir, "/scripts/airmaze") {
				dir = filepath.Dir(filepath.Dir(dir))
			}
			return c, dir, nil
		}
	}
	return "", "", fmt.Errorf("install.ps1 missing from the embedded payload")
}

func unzipBytes(blob []byte, dest string) error {
	r, err := zip.NewReader(bytes.NewReader(blob), int64(len(blob)))
	if err != nil {
		return err
	}
	for _, f := range r.File {
		name := filepath.Clean(f.Name)
		if name == "." || strings.HasPrefix(name, "..") || strings.Contains(name, ":") {
			continue
		}
		target := filepath.Join(dest, name)
		rel, err := filepath.Rel(dest, target)
		if err != nil || strings.HasPrefix(rel, "..") {
			continue
		}
		if f.FileInfo().IsDir() {
			if err := os.MkdirAll(target, 0o755); err != nil {
				return err
			}
			continue
		}
		if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
			return err
		}
		rc, err := f.Open()
		if err != nil {
			return err
		}
		out, err := os.OpenFile(target, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0o644)
		if err != nil {
			rc.Close()
			return err
		}
		_, copyErr := io.Copy(out, rc)
		out.Close()
		rc.Close()
		if copyErr != nil {
			return copyErr
		}
	}
	return nil
}
