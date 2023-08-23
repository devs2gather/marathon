package main

import (
	"bytes"
	"encoding/base32"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
)

type details struct {
	Name        string `json:"name"`
	Email       string `json:"email"`
	Hash        string `json:"hash"`
	Message     string `json:"message"`
	AuthorName  string `json:"authorName"`
	AuthorEmail string `json:"authorEmail"`
}

func main() {
	path, err := exec.LookPath("git")
	if errors.Is(err, exec.ErrDot) {
		err = nil
	}
	if err != nil {
		err = fmt.Errorf("error %d: %s", 100, "git must be installed")
		fmt.Println(err)
		os.Exit(2)
	}

	// exec git and get user.name and user.email
	cmd := exec.Command(path, "config", "--list")
	out, err := cmd.Output()
	if err != nil {
		err = fmt.Errorf("error %d: %s", 102, "unexpected error")
		fmt.Println(err)
		os.Exit(1)
	}

	// parse output
	var name, email []byte
	for _, line := range bytes.Split(out, []byte("\n")) {
		if bytes.HasPrefix(line, []byte("user.name=")) {
			name = line[10:]
		}
		if bytes.HasPrefix(line, []byte("user.email=")) {
			email = line[11:]
		}
	}

	// check if name and email are set
	if string(name) == "" || string(email) == "" {
		err = fmt.Errorf("error %d: %s", 101, "git user.name and user.email must be set")
		fmt.Println(err)
		os.Exit(1)
	}

	// Git log get latest commit hash, message and author
	cmd = exec.Command("git", "log", "-1", "--pretty=format:%h%n%s%n%an%n%ae")
	out, err = cmd.Output()
	if err != nil {
		err = fmt.Errorf("error %d: %s", 101, "can't retrieve latest commit")
		fmt.Println(err)
		os.Exit(2)
	}

	// parse output
	var hash, message, authorName, authorEmail []byte
	for i, line := range bytes.Split(out, []byte("\n")) {
		switch i {
		case 0:
			hash = line
		case 1:
			message = line
		case 2:
			authorName = line
		case 3:
			authorEmail = line
		}
	}

	d := details{
		Name:        string(name),
		Email:       string(email),
		Hash:        string(hash),
		Message:     string(message),
		AuthorName:  string(authorName),
		AuthorEmail: string(authorEmail),
	}

	d_json, err := json.Marshal(d)
	if err != nil {
		err = fmt.Errorf("error %d: %s", 102, "unexpected Error")
		fmt.Println(err)
		os.Exit(1)
	}

	// convert json to hex
	d_hex := fmt.Sprintf("%x", d_json)

	// convert hex to base64
	d_base := base32.StdEncoding.EncodeToString([]byte(d_hex))

	fmt.Printf("Submission Code: %s\n", d_base)
}
