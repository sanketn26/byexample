# Go 12 — Idiomatic Go

Go is deliberately small. Do the plain thing, make the zero value useful,
and keep the happy path left-aligned. `gofmt` settles formatting, so do not
argue about it. Names are `MixedCaps`, short in a short scope (`i`, `r`,
`buf`), never `snake_case` and never `GetFoo` when `Foo` will do. Packages
are short, lowercase, and singular (`bytes`, not `util`, `common`, or
`helpers`). Receivers are one or two letters, consistent, and never `this`
or `self`. A comment starts with the name: `// Foo does …`.
`context.Context` is the first parameter and is not stored in a struct.
Put code that must stay private in `internal/`. Avoid `init` and mutable
package globals. Return errors, wrapped with `%w`, instead of panicking for
control flow. Reach for `strings.Builder` and `make([]T, 0, n)` instead of
repeated `+=`. A little copying beats a little dependency, and a little
repetition beats a premature abstraction. If a generic seems necessary,
check whether an interface or a plain function already does the job. Run
`go vet ./...`, `staticcheck ./...`, and `go test -race ./...` in CI. The
standard library (`bufio`, `net/http`, `sort`, `io`) is the style guide.
Do not rebuild Java: no getters, no `AbstractFactoryBean`, no inheritance
tree. Handle an error where you have enough context to do something useful.
Concurrency needs a way to stop; do not fire a goroutine and forget it.

## An enum is `iota` plus `String`

The zero value is the first name. `String` is what `%v` prints; `%d` is
still the number. An unknown value should show the number rather than a
blank.

```go file=n01.go
package main

import "fmt"

type Weekday int

const (
	Sunday Weekday = iota
	Monday
	Tuesday
)

func (d Weekday) String() string {
	switch d {
	case Sunday:
		return "Sunday"
	case Monday:
		return "Monday"
	case Tuesday:
		return "Tuesday"
	}
	return fmt.Sprintf("Weekday(%d)", int(d))
}

func main() {
	fmt.Println(Monday, Weekday(9))
	fmt.Printf("%v %d\n", Tuesday, Tuesday)
}
```

```text output
Monday Weekday(9)
Tuesday 2
```

## Options are functions that edit a struct

Defaults live in the constructor. Each option is a `func(*Server)` the
caller may pass or skip. That stays smaller than a constructor per
combination, and it does not force the caller to fill a struct of zeros.

```go file=n02.go
package main

import (
	"fmt"
	"time"
)

type Server struct {
	host    string
	port    int
	timeout time.Duration
}

type Option func(*Server)

func WithPort(p int) Option { return func(s *Server) { s.port = p } }

func WithTimeout(d time.Duration) Option {
	return func(s *Server) { s.timeout = d }
}

func NewServer(host string, opts ...Option) *Server {
	s := &Server{host: host, port: 8080, timeout: 30 * time.Second}
	for _, o := range opts {
		o(s)
	}
	return s
}

func main() {
	s := NewServer("localhost", WithPort(9000))
	fmt.Println(s.host, s.port, s.timeout)
}
```

```text output
localhost 9000 30s
```

## The zero value should be ready to use

`SafeSet` allocates its map on the first `Add`. Callers do not need a
constructor, and the mutex is not copied because methods take a pointer.

```go file=n03.go
package main

import (
	"fmt"
	"sync"
)

type SafeSet struct {
	mu sync.Mutex
	m  map[string]struct{}
}

func (s *SafeSet) Add(k string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.m == nil {
		s.m = make(map[string]struct{})
	}
	s.m[k] = struct{}{}
}

func (s *SafeSet) Len() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return len(s.m)
}

func main() {
	var set SafeSet
	set.Add("a")
	set.Add("a")
	set.Add("b")
	fmt.Println(set.Len())
}
```

```text output
2
```

## Accept an interface, return a concrete type

`Report` writes to an `io.Writer`. The caller passes `os.Stdout` or a
`strings.Builder`. The function returns nothing abstract: the concrete
result is the bytes it wrote. Small interfaces belong next to the code
that uses them, not next to one implementation.

```go file=n04.go
package main

import (
	"fmt"
	"io"
	"os"
	"strings"
)

func Report(w io.Writer, items []string) {
	for i, it := range items {
		fmt.Fprintf(w, "%d. %s\n", i+1, it)
	}
}

func main() {
	Report(os.Stdout, []string{"first", "second"})
	var sb strings.Builder
	Report(&sb, []string{"x"})
	fmt.Printf("%q\n", sb.String())
}
```

```text output
1. first
2. second
"1. x\n"
```

## Return early and keep the happy path left

The error checks leave the function. The success path is not nested inside
`else`. The error text says what failed, in lowercase, with no trailing
period.

```go file=n05.go
package main

import "fmt"

func parseAge(s string) (int, error) {
	if s == "" {
		return 0, fmt.Errorf("age: empty")
	}
	n := 0
	for _, r := range s {
		if r < '0' || r > '9' {
			return 0, fmt.Errorf("age: bad digit %q", r)
		}
		n = n*10 + int(r-'0')
	}
	return n, nil
}

func main() {
	n, err := parseAge("42")
	fmt.Println(n, err)
	_, err = parseAge("")
	fmt.Println(err)
	_, err = parseAge("4x")
	fmt.Println(err)
}
```

```text output
42 <nil>
age: empty
age: bad digit 'x'
```

## One table drives every case

Each row names the input, the wanted value, and whether an error is
expected. The loop is the whole test. Adding a case is a new row, not a
copy of the body. With `go test`, the same loop calls `t.Run`.

```go file=n06.go
package main

import "fmt"

func parseAge(s string) (int, error) {
	if s == "" {
		return 0, fmt.Errorf("age: empty")
	}
	n := 0
	for _, r := range s {
		if r < '0' || r > '9' {
			return 0, fmt.Errorf("age: bad digit %q", r)
		}
		n = n*10 + int(r-'0')
	}
	return n, nil
}

func main() {
	tests := []struct {
		name    string
		in      string
		want    int
		wantErr bool
	}{
		{"ok", "42", 42, false},
		{"empty", "", 0, true},
		{"letters", "4x", 0, true},
	}
	for _, tc := range tests {
		got, err := parseAge(tc.in)
		pass := got == tc.want && (err != nil) == tc.wantErr
		fmt.Printf("%-8s pass=%v\n", tc.name, pass)
	}
}
```

```text output
ok       pass=true
empty    pass=true
letters  pass=true
```

## Comma-ok and keyed literals survive change

The boolean distinguishes a missing key from a stored zero. A keyed struct
literal still compiles if someone reorders the fields; a positional one
may not.

```go file=n07.go
package main

import "fmt"

type Server struct {
	host string
	port int
}

func main() {
	m := map[string]int{"a": 1}
	if v, ok := m["b"]; !ok {
		fmt.Println("missing b", v)
	}
	srv := Server{host: "h", port: 1}
	fmt.Println(srv.port)
}
```

```text output
missing b 0
1
```

## `Atoi` reports a bad number

`strconv.Atoi` returns the integer and an error. A bad string is an
error, not a zero you have to second-guess.

```go file=n08.go
package main

import (
	"fmt"
	"strconv"
)

func main() {
	n, err := strconv.Atoi("42")
	fmt.Println(n, err == nil)
	_, err = strconv.Atoi("no")
	fmt.Println(err != nil)
}
```

```text output
42 true
true
```

## `slices` searches and sorts

`slices.Contains` answers membership. `slices.SortFunc` sorts in place.
The comparison returns a negative number, zero, or a positive number.

```go file=n09.go
package main

import (
	"fmt"
	"slices"
)

func main() {
	xs := []int{3, 1, 2}
	fmt.Println(slices.Contains(xs, 2), slices.Contains(xs, 9))
	slices.SortFunc(xs, func(a, b int) int { return a - b })
	fmt.Println(xs)
}
```

```text output
true false
[1 2 3]
```

## `Cut` splits once

`strings.Cut` returns the text before the separator, the text after it,
and whether the separator was there. The host and the port of
`host:port` are that one call.

```go file=n10.go
package main

import (
	"fmt"
	"strings"
)

func main() {
	host, port, ok := strings.Cut("localhost:8080", ":")
	fmt.Println(host, port, ok)
	_, _, ok = strings.Cut("noport", ":")
	fmt.Println(ok)
}
```

```text output
localhost 8080 true
false
```

## `LookupEnv` tells you the name was unset

An empty value and a missing name are different. The boolean is false
only when the name is absent.

```go file=n11.go
package main

import (
	"fmt"
	"os"
)

func main() {
	os.Setenv("APP_PORT", "8080")
	port, ok := os.LookupEnv("APP_PORT")
	_, missing := os.LookupEnv("APP_MISSING")
	fmt.Println(port, ok, missing)
}
```

```text output
8080 true false
```

## Marshal a struct with the field names you choose

The `json` tag is the name in the document. `Marshal` returns bytes and
an error.

```go file=n12.go
package main

import (
	"encoding/json"
	"fmt"
)

func main() {
	b, err := json.Marshal(struct {
		Name string `json:"name"`
		N    int    `json:"n"`
	}{"Ada", 3})
	if err != nil {
		panic(err)
	}
	fmt.Println(string(b))
}
```

```text output
{"name":"Ada","n":3}
```

## Parse a timestamp in RFC3339

The layout string is the reference time `2006-01-02T15:04:05Z07:00`,
not a strftime pattern. `time.RFC3339` is that layout.

```go file=n13.go
package main

import (
	"fmt"
	"time"
)

func main() {
	t, err := time.Parse(time.RFC3339, "2024-03-15T13:45:00Z")
	if err != nil {
		panic(err)
	}
	fmt.Println(t.Format("2006-01-02"), t.UTC().Hour())
}
```

```text output
2024-03-15 13
```

## Exercises

```go file=exercise.go
package main

import (
	"fmt"
	"io"
	"os"
	"reflect"
	"strings"
)

// Level is an enum: Debug, Info, Warn, Error (in that order, zero = Debug).
// Its String method returns "DEBUG", "INFO", "WARN", "ERROR"
// and "Level(N)" for unknown values.
type Level int

const (
	Debug Level = iota
	Info
	Warn
	Error
)

func (l Level) String() string { return "" } // TODO

// ParseLevel is the inverse of String (case-insensitive).
func ParseLevel(s string) (Level, bool) {
	return 0, false // TODO
}

// Logger writes "LEVEL message\n" to W for messages at or above Min.
// Options: WithMin(level), WithPrefix(string) -> "prefix LEVEL message".
type Logger struct {
	W io.Writer
	// TODO: fields
}

type LogOption func(*Logger)

func WithMin(l Level) LogOption       { return func(*Logger) {} } // TODO
func WithPrefix(p string) LogOption   { return func(*Logger) {} } // TODO

func NewLogger(w io.Writer, opts ...LogOption) *Logger {
	return &Logger{W: w} // TODO
}

func (l *Logger) Log(level Level, msg string) {
	// TODO
}

// Set is a generic set whose zero value is usable.
type Set[T comparable] struct {
	m map[T]struct{}
}

func (s *Set[T]) Add(v T)           {}
func (s *Set[T]) Has(v T) bool      { return false }
func (s *Set[T]) Len() int          { return -1 }

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
	check("string", []string{Warn.String(), Level(9).String()}, []string{"WARN", "Level(9)"})
	l, ok := ParseLevel("error")
	check("parse", []any{l, ok}, []any{Error, true})
	_, ok = ParseLevel("loud")
	check("parse bad", ok, false)

	var sb strings.Builder
	lg := NewLogger(&sb, WithMin(Info), WithPrefix("app"))
	lg.Log(Debug, "hidden")
	lg.Log(Warn, "disk low")
	check("logger", sb.String(), "app WARN disk low\n")

	var sb2 strings.Builder
	NewLogger(&sb2).Log(Debug, "shown")
	check("logger default", sb2.String(), "DEBUG shown\n")

	var s Set[string]
	s.Add("a")
	s.Add("a")
	s.Add("b")
	check("set", []any{s.Len(), s.Has("a"), s.Has("z")}, []any{2, true, false})
	_ = os.Stdout
	if failed {
		os.Exit(1)
	}
}
```

<details><summary>Solution</summary>

```go file=solution.go
package main

import (
	"fmt"
	"io"
	"os"
	"reflect"
	"strings"
)

type Level int

const (
	Debug Level = iota
	Info
	Warn
	Error
)

var levelNames = [...]string{"DEBUG", "INFO", "WARN", "ERROR"}

func (l Level) String() string {
	if l < 0 || int(l) >= len(levelNames) {
		return fmt.Sprintf("Level(%d)", int(l))
	}
	return levelNames[l]
}

func ParseLevel(s string) (Level, bool) {
	for i, n := range levelNames {
		if strings.EqualFold(n, s) {
			return Level(i), true
		}
	}
	return 0, false
}

type Logger struct {
	W      io.Writer
	min    Level
	prefix string
}

type LogOption func(*Logger)

func WithMin(l Level) LogOption     { return func(lg *Logger) { lg.min = l } }
func WithPrefix(p string) LogOption { return func(lg *Logger) { lg.prefix = p } }

func NewLogger(w io.Writer, opts ...LogOption) *Logger {
	lg := &Logger{W: w}
	for _, o := range opts {
		o(lg)
	}
	return lg
}

func (l *Logger) Log(level Level, msg string) {
	if level < l.min {
		return
	}
	if l.prefix != "" {
		fmt.Fprintf(l.W, "%s %s %s\n", l.prefix, level, msg)
		return
	}
	fmt.Fprintf(l.W, "%s %s\n", level, msg)
}

type Set[T comparable] struct {
	m map[T]struct{}
}

func (s *Set[T]) Add(v T) {
	if s.m == nil {
		s.m = make(map[T]struct{})
	}
	s.m[v] = struct{}{}
}

func (s *Set[T]) Has(v T) bool {
	_, ok := s.m[v]
	return ok
}

func (s *Set[T]) Len() int { return len(s.m) }

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
	check("string", []string{Warn.String(), Level(9).String()}, []string{"WARN", "Level(9)"})
	l, ok := ParseLevel("error")
	check("parse", []any{l, ok}, []any{Error, true})
	_, ok = ParseLevel("loud")
	check("parse bad", ok, false)

	var sb strings.Builder
	lg := NewLogger(&sb, WithMin(Info), WithPrefix("app"))
	lg.Log(Debug, "hidden")
	lg.Log(Warn, "disk low")
	check("logger", sb.String(), "app WARN disk low\n")

	var sb2 strings.Builder
	NewLogger(&sb2).Log(Debug, "shown")
	check("logger default", sb2.String(), "DEBUG shown\n")

	var s Set[string]
	s.Add("a")
	s.Add("a")
	s.Add("b")
	check("set", []any{s.Len(), s.Has("a"), s.Has("z")}, []any{2, true, false})
	_ = os.Stdout
	if failed {
		os.Exit(1)
	}
}
```

</details>

Next: [13 — Testing](13-testing.md)
