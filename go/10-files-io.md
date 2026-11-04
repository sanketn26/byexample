# Go 10 — Files, I/O and the Standard Library

`io.Reader` and `io.Writer` are the universal plumbing. Files, network
connections, buffers, and compressors all speak them. `os.ReadFile` loads
the whole file; stream a large one with `io.Copy`. Use `filepath` for OS
paths and `path` for slash-separated paths such as URLs. `exec.Command`
does not run a shell, so pass arguments separately and the call stays free
of injection.

## Read and write a whole small file

`WriteFile` and `ReadFile` are the short path. Every `os.Open` still needs
a `Close`. Defer it immediately after you know the open succeeded, and
check the error from `Close` on a file you wrote: that is sometimes where
the failure shows up.

```go file=n01.go
package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

func main() {
	dir, err := os.MkdirTemp("", "gobyexample")
	if err != nil {
		panic(err)
	}
	defer os.RemoveAll(dir)

	notes := filepath.Join(dir, "notes.txt")
	if err := os.WriteFile(notes, []byte("alpha\nbeta\ngamma\n"), 0o644); err != nil {
		panic(err)
	}
	data, err := os.ReadFile(notes)
	if err != nil {
		panic(err)
	}
	fmt.Println(strings.Split(strings.TrimSpace(string(data)), "\n"))
}
```

```text output
[alpha beta gamma]
```

## A scanner walks one line at a time

`Scan` strips the newline. The default token limit is 64 KiB; call
`sc.Buffer` for longer lines. `sc.Err()` is the I/O error, distinct from
a clean end of file.

```go file=n02.go
package main

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
)

func main() {
	dir, err := os.MkdirTemp("", "gobyexample")
	if err != nil {
		panic(err)
	}
	defer os.RemoveAll(dir)
	notes := filepath.Join(dir, "notes.txt")
	if err := os.WriteFile(notes, []byte("alpha\nbeta\ngamma\n"), 0o644); err != nil {
		panic(err)
	}
	f, err := os.Open(notes)
	if err != nil {
		panic(err)
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	for line := 1; sc.Scan(); line++ {
		fmt.Println(line, sc.Text())
	}
	fmt.Println(sc.Err())
}
```

```text output
1 alpha
2 beta
3 gamma
<nil>
```

## A buffered writer holds bytes until `Flush`

`bufio.Writer` does not touch the file on every `WriteString`. `Flush`
pushes the buffer. Skip it and the last lines never land.

```go file=n03.go
package main

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

func main() {
	dir, err := os.MkdirTemp("", "gobyexample")
	if err != nil {
		panic(err)
	}
	defer os.RemoveAll(dir)
	notes := filepath.Join(dir, "notes.txt")
	if err := os.WriteFile(notes, []byte("alpha\nbeta\ngamma\n"), 0o644); err != nil {
		panic(err)
	}
	f, err := os.OpenFile(notes, os.O_APPEND|os.O_WRONLY, 0o644)
	if err != nil {
		panic(err)
	}
	w := bufio.NewWriter(f)
	if _, err := w.WriteString("delta\n"); err != nil {
		panic(err)
	}
	if err := w.Flush(); err != nil {
		panic(err)
	}
	if err := f.Close(); err != nil {
		panic(err)
	}
	data, err := os.ReadFile(notes)
	if err != nil {
		panic(err)
	}
	fmt.Println(strings.Count(string(data), "\n"))
}
```

```text output
4
```

## A binary file is a slice of bytes

There is no separate binary mode. `Stat` reports the size the kernel sees,
which matches the slice you wrote.

```go file=n04.go
package main

import (
	"fmt"
	"os"
	"path/filepath"
)

func main() {
	dir, err := os.MkdirTemp("", "gobyexample")
	if err != nil {
		panic(err)
	}
	defer os.RemoveAll(dir)
	bin := filepath.Join(dir, "data.bin")
	if err := os.WriteFile(bin, []byte{0, 1, 2, 255}, 0o600); err != nil {
		panic(err)
	}
	raw, err := os.ReadFile(bin)
	if err != nil {
		panic(err)
	}
	st, err := os.Stat(bin)
	if err != nil {
		panic(err)
	}
	fmt.Println(raw, st.Size())
}
```

```text output
[0 1 2 255] 4
```

## Struct tags control JSON field names

Exported fields are encoded. `extra` is a nil pointer, so it becomes
`null`. `debug` is present because the tag has no `omitempty`. Unexported
fields are ignored.

```go file=n05.go
package main

import (
	"encoding/json"
	"fmt"
	"reflect"
)

type Config struct {
	Name  string  `json:"name"`
	Ports []int   `json:"ports"`
	Debug bool    `json:"debug"`
	Extra *string `json:"extra"`
}

func main() {
	cfg := Config{Name: "app", Ports: []int{80, 443}}
	js, err := json.Marshal(cfg)
	if err != nil {
		panic(err)
	}
	var back Config
	if err := json.Unmarshal(js, &back); err != nil {
		panic(err)
	}
	fmt.Println(reflect.DeepEqual(cfg, back))
	fmt.Println(string(js))
}
```

```text output
true
{"name":"app","ports":[80,443],"debug":false,"extra":null}
```

## JSON numbers become `float64` in `any`

A `map[string]any` has nowhere to put an integer type, so the decoder uses
`float64`. `json.Decoder.UseNumber` keeps the digits exact when that
matters.

```go file=n06.go
package main

import (
	"encoding/json"
	"fmt"
)

func main() {
	js := []byte(`{"ports":[80,443]}`)
	var generic map[string]any
	if err := json.Unmarshal(js, &generic); err != nil {
		panic(err)
	}
	fmt.Printf("%T\n", generic["ports"].([]any)[0])
}
```

```text output
float64
```

## CSV quotes a field that contains a comma

`WriteAll` flushes. The reader returns the unquoted field, so the comma
inside the name is data, not a separator.

```go file=n07.go
package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

func main() {
	dir, err := os.MkdirTemp("", "gobyexample")
	if err != nil {
		panic(err)
	}
	defer os.RemoveAll(dir)
	csvPath := filepath.Join(dir, "people.csv")
	cf, err := os.Create(csvPath)
	if err != nil {
		panic(err)
	}
	cw := csv.NewWriter(cf)
	if err := cw.WriteAll([][]string{{"name", "age"}, {"Ada", "36"}, {"Linus, T.", "55"}}); err != nil {
		panic(err)
	}
	if err := cf.Close(); err != nil {
		panic(err)
	}
	text, err := os.ReadFile(csvPath)
	if err != nil {
		panic(err)
	}
	fmt.Println(strings.Split(string(text), "\n")[2])

	cf, err = os.Open(csvPath)
	if err != nil {
		panic(err)
	}
	rows, err := csv.NewReader(cf).ReadAll()
	cf.Close()
	if err != nil {
		panic(err)
	}
	total := 0
	for _, r := range rows[1:] {
		n, err := strconv.Atoi(r[1])
		if err != nil {
			panic(err)
		}
		total += n
	}
	fmt.Println(rows[2][0], total)
}
```

```text output
"Linus, T.",55
Linus, T. 91
```

## `WalkDir` visits names in lexical order

The callback sees every file and directory. Skip directories when you want
only files, and use `filepath.ToSlash` so the printed relative path does
not depend on the OS separator. The order is sorted, not the order of
`Create`.

```go file=n08.go
package main

import (
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
)

func main() {
	dir, err := os.MkdirTemp("", "gobyexample")
	if err != nil {
		panic(err)
	}
	defer os.RemoveAll(dir)
	if err := os.WriteFile(filepath.Join(dir, "notes.txt"), []byte("n"), 0o644); err != nil {
		panic(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "data.bin"), []byte{1}, 0o600); err != nil {
		panic(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "people.csv"), []byte("a"), 0o644); err != nil {
		panic(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "cfg.json"), []byte(`{"name":"app"}`), 0o644); err != nil {
		panic(err)
	}
	if err := os.Mkdir(filepath.Join(dir, "sub"), 0o755); err != nil {
		panic(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "sub", "x.go"), []byte("package x"), 0o644); err != nil {
		panic(err)
	}
	var files []string
	err = filepath.WalkDir(dir, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !d.IsDir() {
			rel, err := filepath.Rel(dir, p)
			if err != nil {
				return err
			}
			files = append(files, filepath.ToSlash(rel))
		}
		return nil
	})
	if err != nil {
		panic(err)
	}
	fmt.Println(files)
}
```

```text output
[cfg.json data.bin notes.txt people.csv sub/x.go]
```

## A missing file is `fs.ErrNotExist`

`os.IsNotExist` answers the same question. `errors.Is` is the form that
still works when the error is wrapped.

```go file=n09.go
package main

import (
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
)

func main() {
	dir, err := os.MkdirTemp("", "gobyexample")
	if err != nil {
		panic(err)
	}
	defer os.RemoveAll(dir)
	_, err = os.ReadFile(filepath.Join(dir, "nope"))
	fmt.Println(errors.Is(err, fs.ErrNotExist))
}
```

```text output
true
```

## `exec.Command` takes the program and its arguments

`Output` runs `echo` with the argument `42`. No shell sees the string, so
spaces and metacharacters stay data.

```go file=n10.go
package main

import (
	"fmt"
	"os/exec"
	"strings"
)

func main() {
	out, err := exec.Command("echo", "42").Output()
	if err != nil {
		panic(err)
	}
	fmt.Println(strings.TrimSpace(string(out)))
}
```

```text output
42
```

## Standard error is a different stream

`fmt.Fprintln(os.Stderr, ...)` does not appear below; this page records
standard output only. `LookupEnv` reports a missing variable as `""` and
false, which is not the same as a variable set to empty (`os.Getenv`
cannot tell those apart).

```go file=n11.go
package main

import (
	"fmt"
	"os"
)

func main() {
	fmt.Fprintln(os.Stderr, "to stderr")
	v, ok := os.LookupEnv("DEFINITELY_NOT_SET")
	fmt.Printf("%q %v\n", v, ok)
}
```

```text output
"" false
```

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
