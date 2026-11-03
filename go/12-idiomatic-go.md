# Go 12 — Idiomatic Go

Go is deliberately small. "Idiomatic" mostly means: *do the plain thing, make
the zero value useful, keep the happy path left-aligned, and let the
standard library's conventions guide you.*

## Example

```go file=example.go
package main

import (
	"fmt"
	"io"
	"os"
	"strings"
	"sync"
	"time"
)

// 1. Enums: a named type + iota + String().
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

// 2. Functional options: optional configuration without constructor
// explosions or config structs full of zero values.
type Server struct {
	host    string
	port    int
	timeout time.Duration
}

type Option func(*Server)

func WithPort(p int) Option               { return func(s *Server) { s.port = p } }
func WithTimeout(d time.Duration) Option { return func(s *Server) { s.timeout = d } }

func NewServer(host string, opts ...Option) *Server {
	s := &Server{host: host, port: 8080, timeout: 30 * time.Second} // defaults
	for _, o := range opts {
		o(s)
	}
	return s
}

// 3. Make the zero value useful: no constructor needed.
type SafeSet struct {
	mu sync.Mutex
	m  map[string]struct{} // created lazily
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

// 4. Accept interfaces, return concrete types. Inject io.Writer, not os.Stdout.
func Report(w io.Writer, items []string) {
	for i, it := range items {
		fmt.Fprintf(w, "%d. %s\n", i+1, it)
	}
}

// 5. Early returns keep the happy path unindented.
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

// 6. Table-driven tests: the idiomatic shape of Go tests, runnable here.
func runTable() {
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

func main() {
	fmt.Println(Monday, Weekday(9))
	fmt.Printf("%v %d\n", Tuesday, Tuesday)

	s := NewServer("localhost", WithPort(9000))
	fmt.Println(s.host, s.port, s.timeout)

	var set SafeSet // ready to use
	set.Add("a")
	set.Add("a")
	set.Add("b")
	fmt.Println(set.Len())

	Report(os.Stdout, []string{"first", "second"})
	var sb strings.Builder
	Report(&sb, []string{"x"})
	fmt.Printf("%q\n", sb.String())

	runTable()

	// 7. The comma-ok idiom and keyed struct literals
	m := map[string]int{"a": 1}
	if v, ok := m["b"]; !ok {
		fmt.Println("missing b", v)
	}
	srv := Server{host: "h", port: 1} // keyed: survives field reordering
	fmt.Println(srv.port)
}
```

```text output
Monday Weekday(9)
Tuesday 2
localhost 9000 30s
2
1. first
2. second
"1. x\n"
ok       pass=true
empty    pass=true
letters  pass=true
missing b 0
1
```

## The checklist

| Do | Avoid |
|----|-------|
| `gofmt` / `go vet` on every save | arguing about formatting |
| Short names for short scopes (`i`, `r`, `buf`) | `theCurrentIndexCounter` |
| `MixedCaps`, no underscores | `snake_case`, `GetFoo()` (write `Foo()`) |
| Package names: short, lowercase, singular (`bytes`) | `util`, `common`, `helpers` |
| Receiver names of 1–2 letters, consistent | `this`, `self` |
| Return errors, wrap with `%w` and context | panics for control flow |
| `context.Context` as the **first** parameter | storing contexts in structs |
| Small interfaces at the consumer | big interfaces next to the implementation |
| `strings.Builder`, preallocate with `make([]T, 0, n)` | repeated `+=` |
| Table-driven tests, `t.Run` subtests | copy-pasted test bodies |
| Concurrency only when needed; always a way to stop | fire-and-forget goroutines |
| Comments that start with the name: `// Foo does …` | comments that restate the code |
| `internal/` packages to limit API surface | exporting everything |
| Avoid `init()` and mutable package globals | hidden dependencies |

## Details that bite

- Don't "fix" Go into another language: no getters/setters, no
  `AbstractFactoryBean`, no inheritance hierarchies.
- A little copying is better than a little dependency, and a little
  repetition is better than a premature abstraction.
- Handle errors where you have the context to do something useful.
- If you need generics, check whether an interface or a plain function
  already does the job.
- Run `go vet ./...`, `staticcheck ./...` and `go test -race ./...` in CI.
- Read the standard library: `bufio`, `net/http`, `sort`, `io`. It is the
  best style guide there is.

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
