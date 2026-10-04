//go:build !windows

package main

import (
	"encoding/json"
	"fmt"
	"os"
)

func openDesktop(url string) error {
	// Linux/macOS hosts are used for package builds and --self-test only.
	// The Windows exe opens a native Dragon AI Agent window.
	if os.Getenv("DRAGON_AI_PRINT_URL") == "1" {
		fmt.Println(url)
		return nil
	}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	_ = enc.Encode(map[string]any{
		"ok":     true,
		"action": "launch-check",
		"note":   "DragonAIAgent.exe is the Windows desktop. Cross-compile with GOOS=windows.",
		"url":    url,
	})
	return nil
}
