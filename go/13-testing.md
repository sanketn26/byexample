# Go 13 — Testing

Go ships `testing` and `go test`, which finds `TestXxx(t *testing.T)` in
`_test.go` files. These lessons are single files, so each program carries a
miniature `T` with the same `Errorf` and `Run` shape. Put production code
in `slug.go` and the tests in `slug_test.go` (same package), rename `T` to
`*testing.T`, and run `go test ./...`. Add `-run Name/sub` to pick one
subtest, `-race` for data races, and `-cover` for coverage. The test bodies
do not change. `Errorf` keeps going so every failing case shows up;
`Fatalf` stops when the rest of the test cannot make sense, such as after
a failed setup. Fakes beat mocks: a small struct that satisfies the
interface cannot rot the way a recording framework can. Inject that fake.
Do not stub a global, and do not compare `err.Error()` to a string.

## A table of cases, one subtest each

The slice is the whole test. `Run` names the row, and a failure is prefixed
with that name. Since Go 1.22 each iteration has its own `tc`, so the
closure is safe even with `t.Parallel()`. Older code copied it (`tc := tc`).

```go file=n01.go
package main

import (
	"fmt"
	"strings"
)

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

type T struct{ msgs []string }

func (t *T) Errorf(format string, args ...any) {
	t.msgs = append(t.msgs, fmt.Sprintf(format, args...))
}

func (t *T) Run(name string, fn func(*T)) {
	sub := &T{}
	fn(sub)
	for _, m := range sub.msgs {
		t.Errorf("%s: %s", name, m)
	}
}

func main() {
	cases := []struct{ name, in, want string }{
		{"plain", "Hello World", "hello-world"},
		{"punct", "  Go, is -- fun!  ", "go-is-fun"},
		{"empty", "", ""},
		{"digits", "Top 10", "top-10"},
	}
	t := &T{}
	for _, tc := range cases {
		t.Run(tc.name, func(t *T) {
			if got := Slugify(tc.in); got != tc.want {
				t.Errorf("Slugify(%q) = %q, want %q", tc.in, got, tc.want)
			}
		})
	}
	if len(t.msgs) == 0 {
		fmt.Println("PASS Slugify")
	} else {
		fmt.Println("FAIL", t.msgs)
	}
}
```

```text output
PASS Slugify
```

## Compare errors with `errors.Is`

`ParsePort` wraps a sentinel. The test asks `errors.Is`, not `==` and not
the message text. The message is for humans and will change.

```go file=n02.go
package main

import (
	"errors"
	"fmt"
	"strconv"
)

var ErrPort = errors.New("bad port")

func ParsePort(s string) (int, error) {
	n, err := strconv.Atoi(s)
	if err != nil || n < 1 || n > 65535 {
		return 0, fmt.Errorf("%w: %q", ErrPort, s)
	}
	return n, nil
}

func main() {
	ok := true
	if n, err := ParsePort("8080"); err != nil || n != 8080 {
		ok = false
		fmt.Println("got", n, err)
	}
	for _, in := range []string{"", "x", "0", "70000"} {
		if _, err := ParsePort(in); !errors.Is(err, ErrPort) {
			ok = false
			fmt.Printf("ParsePort(%q) error = %v\n", in, err)
		}
	}
	if ok {
		fmt.Println("PASS ParsePort")
	}
}
```

```text output
PASS ParsePort
```

## Inject the clock and the writer

`time.Now` inside the function cannot be tested. `Greeter` takes a `Clock`
and an `io.Writer`. The fake clock returns the hour you set, and a
`strings.Builder` captures the greeting.

```go file=n03.go
package main

import (
	"fmt"
	"io"
	"strings"
)

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

func main() {
	var sb strings.Builder
	Greeter{FakeClock{9}, &sb}.Greet("Ada")
	Greeter{FakeClock{20}, &sb}.Greet("Bob")
	want := "good morning, Ada\ngood evening, Bob\n"
	if sb.String() == want {
		fmt.Println("PASS Greet")
	} else {
		fmt.Printf("got %q, want %q\n", sb.String(), want)
	}
}
```

```text output
PASS Greet
```

## A failure names the input, the result, and the expectation

`Run` folds the subtest name onto the message. The line tells you which
case, what `Slugify` returned, and what the test wanted. That is the whole
report.

```go file=n04.go
package main

import "fmt"

type T struct{ msgs []string }

func (t *T) Errorf(format string, args ...any) {
	t.msgs = append(t.msgs, fmt.Sprintf(format, args...))
}

func (t *T) Run(name string, fn func(*T)) {
	sub := &T{}
	fn(sub)
	for _, m := range sub.msgs {
		t.Errorf("%s: %s", name, m)
	}
}

func main() {
	broken := &T{}
	broken.Run("case", func(t *T) {
		t.Errorf("Slugify(%q) = %q, want %q", "A b", "a-b", "a_b")
	})
	fmt.Println("caught:", broken.msgs[0])
}
```

```text output
caught: case: Slugify("A b") = "a-b", want "a_b"
```

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
