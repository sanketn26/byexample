# Go 13 — Testing

Go ships a `testing` package and `go test`, which finds `TestXxx(t *testing.T)` functions in `_test.go` files. Lessons here are single files you run directly, so the example carries a miniature `T` with the same `Errorf`/`Run` shape. The habits are the ones that matter: table-driven cases, a subtest per case, errors compared with `errors.Is`, and anything non-deterministic injected as an interface.

## Example

```go file=example.go
package main

import (
	"errors"
	"fmt"
	"io"
	"strconv"
	"strings"
)

// 1. The code under test: plain functions, no test hooks.
func Slugify(s string) string {
	var b strings.Builder
	dash := false
	for _, r := range strings.ToLower(s) {
		if r >= 'a' && r <= 'z' || r >= '0' && r <= '9' {
			b.WriteRune(r)
			dash = false
		} else if !dash && b.Len() > 0 {
			b.WriteByte('-')
			dash = true
		}
	}
	return strings.TrimRight(b.String(), "-")
}

var ErrPort = errors.New("bad port")

func ParsePort(s string) (int, error) {
	n, err := strconv.Atoi(s)
	if err != nil || n < 1 || n > 65535 {
		return 0, fmt.Errorf("%w: %q", ErrPort, s) // wrap a sentinel
	}
	return n, nil
}

// 2. Inject what the code cannot control (time, output) as interfaces.
type Clock interface{ Hour() int }

type Greeter struct {
	clock Clock
	out   io.Writer
}

func (g Greeter) Greet(name string) {
	part := "evening"
	if g.clock.Hour() < 12 {
		part = "morning"
	}
	fmt.Fprintf(g.out, "good %s, %s\n", part, name)
}

type FakeClock struct{ hour int }

func (f FakeClock) Hour() int { return f.hour }

// 3. A miniature of testing.T. With `go test` the real one does this.
type T struct {
	failed bool
	msgs   []string
}

func (t *T) Errorf(format string, args ...any) {
	t.failed = true
	t.msgs = append(t.msgs, fmt.Sprintf(format, args...))
}

// Run starts a named subtest and folds its failure into the parent.
func (t *T) Run(name string, fn func(*T)) {
	sub := &T{}
	fn(sub)
	for _, m := range sub.msgs {
		t.Errorf("%s: %s", name, m)
	}
}

type Test struct {
	Name string
	Fn   func(*T)
}

func run(tests []Test) int {
	passed := 0
	for _, tc := range tests {
		t := &T{}
		tc.Fn(t)
		if t.failed {
			fmt.Printf("FAIL %s: %s\n", tc.Name, strings.Join(t.msgs, "; "))
		} else {
			fmt.Printf("PASS %s\n", tc.Name)
			passed++
		}
	}
	fmt.Printf("%d/%d passed\n", passed, len(tests))
	return passed
}

// 4. Table-driven tests: one slice of cases, one loop, one subtest each.
func TestSlugify(t *T) {
	cases := []struct{ name, in, want string }{
		{"plain", "Hello World", "hello-world"},
		{"punct", "  Go, is -- fun!  ", "go-is-fun"},
		{"empty", "", ""},
		{"digits", "Top 10", "top-10"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *T) {
			if got := Slugify(tc.in); got != tc.want {
				t.Errorf("Slugify(%q) = %q, want %q", tc.in, got, tc.want)
			}
		})
	}
}

func TestParsePort(t *T) {
	if n, err := ParsePort("8080"); err != nil || n != 8080 {
		t.Errorf("got %d, %v", n, err)
	}
	for _, in := range []string{"", "x", "0", "70000"} {
		if _, err := ParsePort(in); !errors.Is(err, ErrPort) { // errors.Is, not ==
			t.Errorf("ParsePort(%q) error = %v, want ErrPort", in, err)
		}
	}
}

func TestGreet(t *T) {
	var sb strings.Builder
	Greeter{FakeClock{9}, &sb}.Greet("Ada")
	Greeter{FakeClock{20}, &sb}.Greet("Bob")
	want := "good morning, Ada\ngood evening, Bob\n"
	if sb.String() != want {
		t.Errorf("got %q, want %q", sb.String(), want)
	}
}

func main() {
	run([]Test{{"Slugify", TestSlugify}, {"ParsePort", TestParsePort}, {"Greet", TestGreet}})

	// A failing test names the input, the result and the expectation.
	broken := &T{}
	broken.Run("case", func(t *T) { t.Errorf("Slugify(%q) = %q, want %q", "A b", "a-b", "a_b") })
	fmt.Println("caught:", broken.msgs[0])
}
```

```text output
PASS Slugify
PASS ParsePort
PASS Greet
3/3 passed
caught: case: Slugify("A b") = "a-b", want "a_b"
```

## Details that bite

- **The real thing.** Put the code in `slug.go` and the tests in `slug_test.go` (same package), rename `T` to `*testing.T`, and run `go test ./...`. The bodies of `TestSlugify` and friends do not change. Add `-run Name/sub` to pick one, `-race` to hunt data races, `-cover` for coverage.
- **`Errorf` continues, `Fatalf` stops.** Use `Errorf` to see every failing case in one run. Use `Fatalf` when the rest of the test cannot make sense, such as after a failed setup.
- **Capture the loop variable.** Since Go 1.22 each iteration has its own `tc`, so a subtest closure is safe even with `t.Parallel()`. Older code copied it (`tc := tc`).
- **Compare errors with `errors.Is` / `errors.As`,** never `err.Error() == "..."`. The message is for humans and changes.
- **Inject, do not stub globals.** `time.Now()` called inside the function is untestable. Take a `Clock` (or a `func() time.Time`) and pass a fake. The same goes for `io.Writer` instead of `os.Stdout`.
- **Fakes beat mocks.** A twelve-line struct that satisfies the interface is easier to read than a recording framework, and it cannot rot silently.

## Exercises

Write `ParseDuration` and `RateLimiter.Allow`. The harness and tests are given. Make every line say `PASS`. A call exactly `window` seconds after an earlier one no longer counts against the limit, and denied calls are not recorded.

```go file=exercise.go
package main

import (
	"errors"
	"fmt"
	"os"
	"strings"
)

var ErrBadDuration = errors.New("bad duration")

type Clock interface{ Now() float64 }

// ParseDuration reads "1h30m", "45s", "2h" into seconds. Reject "", "10",
// "5x", "h" with an error that wraps ErrBadDuration.
func ParseDuration(s string) (int, error) {
	return 0, nil // TODO
}

// RateLimiter allows `limit` calls per `window` seconds. A call made exactly
// `window` seconds after an earlier one no longer counts against the limit.
// Denied calls are not recorded.
type RateLimiter struct {
	limit  int
	window float64
	clock  Clock
}

func NewRateLimiter(limit int, window float64, c Clock) *RateLimiter {
	return &RateLimiter{limit: limit, window: window, clock: c}
}

func (r *RateLimiter) Allow() bool {
	return true // TODO
}

type FakeClock struct{ now float64 }

func (f *FakeClock) Now() float64 { return f.now }

type T struct {
	failed bool
	msgs   []string
}

func (t *T) Errorf(format string, args ...any) {
	t.failed = true
	t.msgs = append(t.msgs, fmt.Sprintf(format, args...))
}

func (t *T) Run(name string, fn func(*T)) {
	sub := &T{}
	fn(sub)
	for _, m := range sub.msgs {
		t.Errorf("%s: %s", name, m)
	}
}

type Test struct {
	Name string
	Fn   func(*T)
}

func run(tests []Test) int {
	passed := 0
	for _, tc := range tests {
		t := &T{}
		tc.Fn(t)
		if t.failed {
			fmt.Printf("FAIL %s: %s\n", tc.Name, strings.Join(t.msgs, "; "))
		} else {
			fmt.Printf("PASS %s\n", tc.Name)
			passed++
		}
	}
	return passed
}

func TestParseDuration(t *T) {
	for _, tc := range []struct {
		in   string
		want int
	}{{"1h30m", 5400}, {"45s", 45}, {"2h", 7200}, {"1m1s", 61}} {
		t.Run(tc.in, func(t *T) {
			if got, err := ParseDuration(tc.in); err != nil || got != tc.want {
				t.Errorf("got %d, %v, want %d", got, err, tc.want)
			}
		})
	}
}

func TestParseDurationInvalid(t *T) {
	for _, in := range []string{"", "abc", "10", "5x", "h"} {
		t.Run(in, func(t *T) {
			if _, err := ParseDuration(in); !errors.Is(err, ErrBadDuration) {
				t.Errorf("error = %v, want ErrBadDuration", err)
			}
		})
	}
}

func TestLimitAndWindow(t *T) {
	clock := &FakeClock{}
	rl := NewRateLimiter(2, 10, clock)
	want := func(label string, got, w bool) {
		if got != w {
			t.Errorf("%s: got %v, want %v", label, got, w)
		}
	}
	want("first", rl.Allow(), true)
	want("second", rl.Allow(), true)
	want("third", rl.Allow(), false)
	clock.now = 9.9
	want("just inside", rl.Allow(), false)
	clock.now = 10
	want("expired", rl.Allow(), true)
}

func TestDeniedDoNotCount(t *T) {
	clock := &FakeClock{}
	rl := NewRateLimiter(1, 5, clock)
	rl.Allow()
	for i := 0; i < 10; i++ {
		rl.Allow()
	}
	clock.now = 5
	if !rl.Allow() {
		t.Errorf("denied calls were counted")
	}
}

func main() {
	tests := []Test{
		{"ParseDuration", TestParseDuration},
		{"ParseDurationInvalid", TestParseDurationInvalid},
		{"LimitAndWindow", TestLimitAndWindow},
		{"DeniedDoNotCount", TestDeniedDoNotCount},
	}
	passed := run(tests)
	fmt.Printf("%d/%d passed\n", passed, len(tests))
	if passed != len(tests) {
		os.Exit(1)
	}
}
```

<details><summary>Solution</summary>

```go file=solution.go
package main

import (
	"errors"
	"fmt"
	"os"
	"strings"
)

var ErrBadDuration = errors.New("bad duration")

type Clock interface{ Now() float64 }

// ParseDuration reads "1h30m", "45s", "2h" into seconds.
func ParseDuration(s string) (int, error) {
	units := map[rune]int{'h': 3600, 'm': 60, 's': 1}
	total, n, seen := 0, 0, false
	for _, r := range s {
		switch {
		case r >= '0' && r <= '9':
			n, seen = n*10+int(r-'0'), true
		case units[r] != 0 && seen:
			total, n, seen = total+n*units[r], 0, false
		default:
			return 0, fmt.Errorf("%w: %q", ErrBadDuration, s)
		}
	}
	if s == "" || seen {
		return 0, fmt.Errorf("%w: %q", ErrBadDuration, s)
	}
	return total, nil
}

// RateLimiter allows `limit` calls per `window` seconds.
type RateLimiter struct {
	limit  int
	window float64
	clock  Clock
	calls  []float64
}

func NewRateLimiter(limit int, window float64, c Clock) *RateLimiter {
	return &RateLimiter{limit: limit, window: window, clock: c}
}

func (r *RateLimiter) Allow() bool {
	now := r.clock.Now()
	for len(r.calls) > 0 && now-r.calls[0] >= r.window {
		r.calls = r.calls[1:]
	}
	if len(r.calls) >= r.limit {
		return false
	}
	r.calls = append(r.calls, now)
	return true
}

type FakeClock struct{ now float64 }

func (f *FakeClock) Now() float64 { return f.now }

type T struct {
	failed bool
	msgs   []string
}

func (t *T) Errorf(format string, args ...any) {
	t.failed = true
	t.msgs = append(t.msgs, fmt.Sprintf(format, args...))
}

func (t *T) Run(name string, fn func(*T)) {
	sub := &T{}
	fn(sub)
	for _, m := range sub.msgs {
		t.Errorf("%s: %s", name, m)
	}
}

type Test struct {
	Name string
	Fn   func(*T)
}

func run(tests []Test) int {
	passed := 0
	for _, tc := range tests {
		t := &T{}
		tc.Fn(t)
		if t.failed {
			fmt.Printf("FAIL %s: %s\n", tc.Name, strings.Join(t.msgs, "; "))
		} else {
			fmt.Printf("PASS %s\n", tc.Name)
			passed++
		}
	}
	return passed
}

func TestParseDuration(t *T) {
	for _, tc := range []struct {
		in   string
		want int
	}{{"1h30m", 5400}, {"45s", 45}, {"2h", 7200}, {"1m1s", 61}} {
		t.Run(tc.in, func(t *T) {
			if got, err := ParseDuration(tc.in); err != nil || got != tc.want {
				t.Errorf("got %d, %v, want %d", got, err, tc.want)
			}
		})
	}
}

func TestParseDurationInvalid(t *T) {
	for _, in := range []string{"", "abc", "10", "5x", "h"} {
		t.Run(in, func(t *T) {
			if _, err := ParseDuration(in); !errors.Is(err, ErrBadDuration) {
				t.Errorf("error = %v, want ErrBadDuration", err)
			}
		})
	}
}

func TestLimitAndWindow(t *T) {
	clock := &FakeClock{}
	rl := NewRateLimiter(2, 10, clock)
	want := func(label string, got, w bool) {
		if got != w {
			t.Errorf("%s: got %v, want %v", label, got, w)
		}
	}
	want("first", rl.Allow(), true)
	want("second", rl.Allow(), true)
	want("third", rl.Allow(), false)
	clock.now = 9.9
	want("just inside", rl.Allow(), false)
	clock.now = 10
	want("expired", rl.Allow(), true)
}

func TestDeniedDoNotCount(t *T) {
	clock := &FakeClock{}
	rl := NewRateLimiter(1, 5, clock)
	rl.Allow()
	for i := 0; i < 10; i++ {
		rl.Allow()
	}
	clock.now = 5
	if !rl.Allow() {
		t.Errorf("denied calls were counted")
	}
}

func main() {
	tests := []Test{
		{"ParseDuration", TestParseDuration},
		{"ParseDurationInvalid", TestParseDurationInvalid},
		{"LimitAndWindow", TestLimitAndWindow},
		{"DeniedDoNotCount", TestDeniedDoNotCount},
	}
	passed := run(tests)
	fmt.Printf("%d/%d passed\n", passed, len(tests))
	if passed != len(tests) {
		os.Exit(1)
	}
}
```

</details>

Next: [14 — Capstone: an LRU cache](14-capstone-lru.md)
