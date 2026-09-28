// DragonAIAgentSetup — console launcher for Dragon AI Agent Windows installer payload.
// Build (from this directory or via PACKAGING.md):
//
//	GOOS=windows GOARCH=amd64 go build -o DragonAIAgentSetup.exe .
//
// Looks for sibling payload\install.ps1 (or DragonAIAgent\payload\install.ps1)
// and runs: powershell -NoProfile -ExecutionPolicy Bypass -File <install.ps1>
package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
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

func main() {
	exe, err := os.Executable()
	if err != nil {
		fmt.Fprintf(os.Stderr, "DragonAIAgentSetup: cannot resolve executable path: %v\n", err)
		os.Exit(1)
	}
	exeDir := filepath.Dir(exe)

	script, err := findInstallScript(exeDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "DragonAIAgentSetup: %v\n", err)
		fmt.Fprintln(os.Stderr, "Unzip the full Dragon-AI-Agent-v0.1.0-windows.zip and run DragonAIAgentSetup.exe from that folder.")
		os.Exit(1)
	}

	fmt.Println("Dragon AI Agent Setup v0.1.0")
	fmt.Println("Running:", script)
	fmt.Println()

	payloadRoot := filepath.Dir(script)
	cmd := exec.Command(
		"powershell.exe",
		"-NoProfile",
		"-ExecutionPolicy", "Bypass",
		"-File", script,
		"-PayloadRoot", payloadRoot,
	)
	cmd.Dir = exeDir
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
