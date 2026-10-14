# Go 10 — Files, I/O and the Standard Library

`io.Reader` and `io.Writer` are the universal plumbing. Files, network
connections, buffers and compressors all speak them.

## Example

```go file=example.go
package main

import (
	"bufio"
	"encoding/csv"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
)

type Config struct {
	Name  string  `json:"name"`
	Ports []int   `json:"ports"`
	Debug bool    `json:"debug"`
	Extra *string `json:"extra"`
}

func must(err error) {
	if err != nil {
		panic(err)
	}
}

func main() {
	dir, err := os.MkdirTemp("", "gobyexample")
	must(err)
	defer os.RemoveAll(dir)

	// Whole-file helpers
	notes := filepath.Join(dir, "notes.txt")
	must(os.WriteFile(notes, []byte("alpha\nbeta\ngamma\n"), 0o644))
	data, err := os.ReadFile(notes)
	must(err)
	fmt.Println(strings.Split(strings.TrimSpace(string(data)), "\n"))

	// Streaming line by line
	f, err := os.Open(notes)
	must(err)
	sc := bufio.NewScanner(f)
	for line := 1; sc.Scan(); line++ {
		fmt.Println(line, sc.Text())
	}
	f.Close()

	// Appending; defer Close right after a successful open
	func() {
		f, err := os.OpenFile(notes, os.O_APPEND|os.O_WRONLY, 0o644)
		must(err)
		defer f.Close()
		w := bufio.NewWriter(f)
		w.WriteString("delta\n")
		must(w.Flush()) // buffered writers must be flushed
	}()
	data, _ = os.ReadFile(notes)
	fmt.Println(strings.Count(string(data), "\n"))

	// Binary
	bin := filepath.Join(dir, "data.bin")
	must(os.WriteFile(bin, []byte{0, 1, 2, 255}, 0o600))
	raw, _ := os.ReadFile(bin)
	st, _ := os.Stat(bin)
	fmt.Println(raw, st.Size())

	// JSON round trip
	cfg := Config{Name: "app", Ports: []int{80, 443}}
	js, _ := json.Marshal(cfg)
	var back Config
	must(json.Unmarshal(js, &back))
	fmt.Println(reflect.DeepEqual(cfg, back))
	fmt.Println(string(js))

	// Decoding into any: numbers become float64
	var generic map[string]any
	must(json.Unmarshal(js, &generic))
	fmt.Printf("%T\n", generic["ports"].([]any)[0])

	// CSV quotes fields that contain commas
	csvPath := filepath.Join(dir, "people.csv")
	cf, _ := os.Create(csvPath)
	cw := csv.NewWriter(cf)
	cw.WriteAll([][]string{{"name", "age"}, {"Ada", "36"}, {"Linus, T.", "55"}})
	cf.Close()
	text, _ := os.ReadFile(csvPath)
	fmt.Println(strings.Split(string(text), "\n")[2])

	cf, _ = os.Open(csvPath)
	rows, _ := csv.NewReader(cf).ReadAll()
	cf.Close()
	total := 0
	for _, r := range rows[1:] {
		n, _ := strconv.Atoi(r[1])
		total += n
	}
	fmt.Println(rows[2][0], total)

	// Walking a tree
	must(os.Mkdir(filepath.Join(dir, "sub"), 0o755))
	must(os.WriteFile(filepath.Join(dir, "sub", "x.go"), []byte("package x"), 0o644))
	must(os.WriteFile(filepath.Join(dir, "cfg.json"), js, 0o644))
	var files []string
	must(filepath.WalkDir(dir, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !d.IsDir() {
			rel, _ := filepath.Rel(dir, p)
			files = append(files, filepath.ToSlash(rel))
		}
		return nil
	}))
	fmt.Println(files)

	// Missing file
	_, err = os.ReadFile(filepath.Join(dir, "nope"))
	fmt.Println(errors.Is(err, fs.ErrNotExist))

	// Subprocess
	out, err := exec.Command("echo", "42").Output()
	must(err)
	fmt.Println(strings.TrimSpace(string(out)))

	// Environment
	v, ok := os.LookupEnv("DEFINITELY_NOT_SET")
	fmt.Printf("%q %v\n", v, ok)
	fmt.Fprintln(os.Stderr, "to stderr")
}
```

```text output
[alpha beta gamma]
1 alpha
2 beta
3 gamma
4
[0 1 2 255] 4
true
{"name":"app","ports":[80,443],"debug":false,"extra":null}
float64
"Linus, T.",55
Linus, T. 91
[cfg.json data.bin notes.txt people.csv sub/x.go]
true
42
"" false
```

## Details that bite

- Every `os.Open` needs a `Close`. `defer f.Close()` right after checking
  the error. For *writes*, check the `Close` error too — it can be where
  the failure shows up.
- `bufio.Scanner` has a 64 KiB line limit by default; use
  `sc.Buffer(...)` for long lines and check `sc.Err()`.
- `bufio.Writer` holds data until `Flush`.
- `json` ignores unexported fields, and decodes numbers into `float64` when
  the target is `any`. Use `json.Decoder.UseNumber` for exact integers.
- `os.ReadFile` loads everything; stream with `io.Copy` for large files.
- Use `filepath` for OS paths and `path` for slash-paths (URLs).
- `exec.Command` does not use a shell; pass arguments separately. That is
  what makes it safe from injection.

## Exercises

```go file=exercise.go
package main

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"strings"
)

// CountLines counts lines read from r (a final line without "\n" counts).
func CountLines(r io.Reader) (int, error) {
	return 0, nil // TODO
}

// Grep returns lines containing needle, with 1-based line numbers
// formatted "N:line".
func Grep(r io.Reader, needle string) ([]string, error) {
	return nil, nil // TODO
}

// SumCSVColumn sums an integer column (by header name) of CSV data.
func SumCSVColumn(r io.Reader, column string) (int, error) {
	return 0, nil // TODO
}

// WriteFileAtomic writes data to path via path+".tmp" then renames.
func WriteFileAtomic(path string, data []byte) error {
	return nil // TODO
}

var failed bool

func check(label string, got, want any) {
	if reflect.DeepEqual(got, want) {
		fmt.Println("PASS", label)
		return
	}
	failed = true
	fmt.Printf("FAIL %s: got %v, want %v\n", label, got, want)
}

func main() {
	n, _ := CountLines(strings.NewReader("one\ntwo\nthree"))
	check("count", n, 3)
	n, _ = CountLines(strings.NewReader(""))
	check("count empty", n, 0)

	lines, _ := Grep(strings.NewReader("one\ntwo\nthree two\n"), "two")
	check("grep", lines, []string{"2:two", "3:three two"})

	sum, err := SumCSVColumn(strings.NewReader("id,qty\n1,5\n2,7\n3,10\n"), "qty")
	check("csv", []any{sum, err}, []any{22, error(nil)})
	_, err = SumCSVColumn(strings.NewReader("id,qty\n1,5\n"), "missing")
	check("csv missing column", err != nil, true)

	dir, _ := os.MkdirTemp("", "ex")
	defer os.RemoveAll(dir)
	target := filepath.Join(dir, "o.txt")
	check("atomic err", WriteFileAtomic(target, []byte("hi")), error(nil))
	b, _ := os.ReadFile(target)
	_, statErr := os.Stat(target + ".tmp")
	check("atomic", []any{string(b), os.IsNotExist(statErr)}, []any{"hi", true})
	if failed {
		os.Exit(1)
	}
}
```

<details><summary>Solution</summary>

```go file=solution.go
package main

import (
	"bufio"
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
)

func CountLines(r io.Reader) (int, error) {
	sc := bufio.NewScanner(r)
	n := 0
	for sc.Scan() {
		n++
	}
	return n, sc.Err()
}

func Grep(r io.Reader, needle string) ([]string, error) {
	sc := bufio.NewScanner(r)
	var out []string
	for i := 1; sc.Scan(); i++ {
		if strings.Contains(sc.Text(), needle) {
			out = append(out, fmt.Sprintf("%d:%s", i, sc.Text()))
		}
	}
	return out, sc.Err()
}

func SumCSVColumn(r io.Reader, column string) (int, error) {
	rows, err := csv.NewReader(r).ReadAll()
	if err != nil {
		return 0, err
	}
	if len(rows) == 0 {
		return 0, fmt.Errorf("empty csv")
	}
	col := -1
	for i, h := range rows[0] {
		if h == column {
			col = i
		}
	}
	if col < 0 {
		return 0, fmt.Errorf("no column %q", column)
	}
	total := 0
	for _, row := range rows[1:] {
		n, err := strconv.Atoi(row[col])
		if err != nil {
			return 0, err
		}
		total += n
	}
	return total, nil
}

func WriteFileAtomic(path string, data []byte) error {
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, data, 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}

var failed bool

func check(label string, got, want any) {
	if reflect.DeepEqual(got, want) {
		fmt.Println("PASS", label)
		return
	}
	failed = true
	fmt.Printf("FAIL %s: got %v, want %v\n", label, got, want)
}

func main() {
	n, _ := CountLines(strings.NewReader("one\ntwo\nthree"))
	check("count", n, 3)
	n, _ = CountLines(strings.NewReader(""))
	check("count empty", n, 0)

	lines, _ := Grep(strings.NewReader("one\ntwo\nthree two\n"), "two")
	check("grep", lines, []string{"2:two", "3:three two"})

	sum, err := SumCSVColumn(strings.NewReader("id,qty\n1,5\n2,7\n3,10\n"), "qty")
	check("csv", []any{sum, err}, []any{22, error(nil)})
	_, err = SumCSVColumn(strings.NewReader("id,qty\n1,5\n"), "missing")
	check("csv missing column", err != nil, true)

	dir, _ := os.MkdirTemp("", "ex")
	defer os.RemoveAll(dir)
	target := filepath.Join(dir, "o.txt")
	check("atomic err", WriteFileAtomic(target, []byte("hi")), error(nil))
	b, _ := os.ReadFile(target)
	_, statErr := os.Stat(target + ".tmp")
	check("atomic", []any{string(b), os.IsNotExist(statErr)}, []any{"hi", true})
	if failed {
		os.Exit(1)
	}
}
```

</details>

Next: [11 — Concurrency](11-concurrency.md)
