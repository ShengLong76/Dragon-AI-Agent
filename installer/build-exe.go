// DragonAIAgentSetup — console launcher for Dragon AI Agent Windows installer payload.
// Build (from this directory or via installer/pack.py):
//
//	GOOS=windows GOARCH=amd64 go build -o DragonAIAgentSetup.exe .
//
// Release handoff is this one exe. pack.py appends a zip of the payload to the
// PE so the file is both an installer and a zip. On run, Setup extracts that
// zip (or uses a sibling payload\ folder from an older layout) and runs:
//
//	powershell -NoProfile -ExecutionPolicy Bypass -File <install.ps1>
package main

import (
	"archive/zip"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
)

func findInstallScript(exeDir string) (string, error) {
	candidates := []string{
		filepath.Join(exeDir, "payload", "install.ps1"),
		filepath.Join(exeDir, "DragonAIAgent", "payload", "install.ps1"),
		filepath.Join(exeDir, "install.ps1"),
		filepath.Join(exeDir, "DragonAIAgentSetup.ps1"),
	}
	for _, c := range candidates {
		if st, err := os.Stat(c); err == nil && !st.IsDir() {
			return c, nil
		}
	}
	return "", fmt.Errorf("install.ps1 not found beside exe (expected payload\\install.ps1 under %s)", exeDir)
}

func extractSelfPayload(exe string) (string, error) {
	zr, err := zip.OpenReader(exe)
	if err != nil {
		return "", fmt.Errorf("this exe has no embedded payload: %w", err)
	}
	defer zr.Close()

	dest := filepath.Join(os.TempDir(), "DragonAIAgentSetup-"+strconv.Itoa(os.Getpid()))
	if err := os.RemoveAll(dest); err != nil {
		return "", err
	}
	if err := os.MkdirAll(dest, 0o755); err != nil {
		return "", err
	}

	for _, f := range zr.File {
		if err := extractZipFile(dest, f); err != nil {
			return "", err
		}
	}

	script := filepath.Join(dest, "install.ps1")
	if st, err := os.Stat(script); err != nil || st.IsDir() {
		nested := filepath.Join(dest, "payload", "install.ps1")
		if st, err := os.Stat(nested); err == nil && !st.IsDir() {
			return filepath.Dir(nested), nil
		}
		return "", fmt.Errorf("embedded payload has no install.ps1")
	}
	return dest, nil
}

func extractZipFile(dest string, f *zip.File) error {
	name := filepath.ToSlash(f.Name)
	name = strings.TrimPrefix(name, "/")
	if name == "" || name == "." {
		return nil
	}
	cleaned := filepath.Clean(filepath.FromSlash(name))
	if cleaned == "." || cleaned == ".." || strings.HasPrefix(cleaned, ".."+string(os.PathSeparator)) {
		return fmt.Errorf("refusing zip path %q", f.Name)
	}
	target := filepath.Join(dest, cleaned)
	rel, err := filepath.Rel(dest, target)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(os.PathSeparator)) {
		return fmt.Errorf("refusing zip path %q", f.Name)
	}

	if f.FileInfo().IsDir() {
		return os.MkdirAll(target, 0o755)
	}
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return err
	}
	rc, err := f.Open()
	if err != nil {
		return err
	}
	defer rc.Close()
	out, err := os.OpenFile(target, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0o644)
	if err != nil {
		return err
	}
	defer out.Close()
	_, err = io.Copy(out, rc)
	return err
}

func resolvePayload(exe, exeDir string) (script string, payloadRoot string, err error) {
	script, err = findInstallScript(exeDir)
	if err == nil {
		return script, filepath.Dir(script), nil
	}
	root, xerr := extractSelfPayload(exe)
	if xerr != nil {
		return "", "", fmt.Errorf("%v; %v", err, xerr)
	}
	return filepath.Join(root, "install.ps1"), root, nil
}

func main() {
	exe, err := os.Executable()
	if err != nil {
		fmt.Fprintf(os.Stderr, "DragonAIAgentSetup: cannot resolve executable path: %v\n", err)
		os.Exit(1)
	}
	exeDir := filepath.Dir(exe)

	script, payloadRoot, err := resolvePayload(exe, exeDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "DragonAIAgentSetup: %v\n", err)
		fmt.Fprintln(os.Stderr, "Re-download DragonAIAgentSetup.exe and run that one file.")
		os.Exit(1)
	}

	fmt.Println("Dragon AI Agent Setup v0.1.0")
	fmt.Println("Running:", script)
	fmt.Println()

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
