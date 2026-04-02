package main

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

func main() {
	out, err := os.Create("compiled_project.txt")
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	defer out.Close()

	ignoreList := []string{".git", "media", ".jpg", ".png", ".pdf", "go.sum", "bundle.go", "compiled_project.txt"}

	err = filepath.Walk(".", func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		// 1. Check if the current path should be ignored
		for _, ignore := range ignoreList {
			if strings.Contains(path, ignore) {
				if info.IsDir() {
					return filepath.SkipDir
				}
				return nil
			}
		}

		// 2. Only process actual files
		if !info.IsDir() {
			f, err := os.Open(path)
			if err != nil {
				return nil
			}
			defer f.Close()

			fmt.Fprintf(out, "\n--- FILE: %s ---\n", path)
			_, _ = io.Copy(out, f)
			fmt.Fprintf(out, "\n")
			fmt.Printf("Bundled: %s\n", path)
		}
		return nil
	})

	if err == nil {
		fmt.Println("\nDone! Check compiled_project.txt for your clean source code.")
	}
}