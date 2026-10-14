# Go 09 — Interfaces

Interfaces are satisfied **implicitly**: a type implements an interface by
having the methods, with no declaration. Small interfaces defined by the
*consumer* are the heart of Go design.

## Example

```go file=example.go
package main

import (
	"bytes"
	"fmt"
	"io"
	"math"
	"os"
	"sort"
	"time"
)

type Shape interface {
	Area() float64
}

type Rect struct{ W, H float64 }
type Circle struct{ R float64 }

func (r Rect) Area() float64   { return r.W * r.H }
func (c Circle) Area() float64 { return math.Pi * c.R * c.R }

// Compile-time proof that Rect satisfies Shape.
var _ Shape = Rect{}

// A Writer that upper-cases everything passing through: wraps another Writer.
type upperWriter struct{ w io.Writer }

func (u upperWriter) Write(p []byte) (int, error) {
	return u.w.Write(bytes.ToUpper(p))
}

// sort.Interface: three methods give you sorting for any collection.
type byLen []string

func (b byLen) Len() int           { return len(b) }
func (b byLen) Less(i, j int) bool { return len(b[i]) < len(b[j]) }
func (b byLen) Swap(i, j int)      { b[i], b[j] = b[j], b[i] }

// Depend on a tiny interface so tests (and callers) can substitute it.
type Clock interface{ Now() time.Time }

type fixedClock struct{ t time.Time }

func (f fixedClock) Now() time.Time { return f.t }

func greeting(c Clock) string {
	if c.Now().Hour() < 12 {
		return "good morning"
	}
	return "good afternoon"
}

func main() {
	shapes := []Shape{Rect{3, 4}, Circle{1}}
	for _, s := range shapes {
		fmt.Printf("%T %.2f\n", s, s.Area())
	}

	fmt.Fprintf(upperWriter{os.Stdout}, "hello %d\n", 5)

	var v any = "hi"
	s, ok := v.(string)
	n, ok2 := v.(int) // comma-ok form never panics
	fmt.Println(s, ok, n, ok2)

	words := []string{"ccc", "a", "bb"}
	sort.Sort(byLen(words))
	fmt.Println(words)

	morning := fixedClock{time.Date(2026, 1, 1, 9, 0, 0, 0, time.UTC)}
	fmt.Println(greeting(morning))
}
```

```text output
main.Rect 12.00
main.Circle 3.14
HELLO 5
hi true 0 false
[a bb ccc]
good morning
```

## Details that bite

- Interfaces hold a *(dynamic type, value)* pair. An interface holding a
  nil pointer is **not** `== nil` (see lesson 07).
- A method set depends on the receiver: `T` has only value-receiver
  methods, `*T` has both. Storing a `T` in an interface when the methods
  have pointer receivers is a compile error.
- Define interfaces where they are *used*, keep them to one or two methods
  (`io.Reader`, `fmt.Stringer`), and "accept interfaces, return structs".
- The empty interface `any` loses all type safety; prefer generics when
  the logic is the same across types.
- Comparing interfaces panics at runtime if the dynamic types are
  uncomparable (slices, maps, funcs).
- Don't create an interface "in case we need it later". Add one when a
  second implementation or a test double appears.

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

type Shape interface {
	Area() float64
}

type Rect struct{ W, H float64 }
type Square struct{ S float64 }

func (r Rect) Area() float64   { return 0 } // TODO
func (s Square) Area() float64 { return 0 } // TODO

// Largest returns the shape with the largest area (nil for an empty slice).
func Largest(shapes []Shape) Shape {
	return nil // TODO
}

// CountingWriter forwards writes to W and counts the bytes written.
type CountingWriter struct {
	W io.Writer
	N int
}

func (c *CountingWriter) Write(p []byte) (int, error) {
	return 0, nil // TODO
}

// Describe returns "int:N", "string:LEN", "slice:LEN", "nil" or "unknown".
func Describe(v any) string {
	return "" // TODO
}

// UpperReader wraps an io.Reader and upper-cases the bytes it yields.
type UpperReader struct{ R io.Reader }

func (u UpperReader) Read(p []byte) (int, error) {
	return 0, io.EOF // TODO
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
	big := Rect{3, 4}
	check("largest", Largest([]Shape{Square{2}, big, Square{3}}), Shape(big))
	check("largest empty", Largest(nil) == nil, true)

	var sb strings.Builder
	cw := &CountingWriter{W: &sb}
	fmt.Fprint(cw, "hello ")
	fmt.Fprint(cw, "world")
	check("counting", []any{cw.N, sb.String()}, []any{11, "hello world"})

	check("describe int", Describe(42), "int:42")
	check("describe string", Describe("abc"), "string:3")
	check("describe slice", Describe([]int{1, 2}), "slice:2")
	check("describe nil", Describe(nil), "nil")
	check("describe other", Describe(1.5), "unknown")

	data, _ := io.ReadAll(UpperReader{strings.NewReader("quiet please")})
	check("upper reader", string(data), "QUIET PLEASE")
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

type Shape interface {
	Area() float64
}

type Rect struct{ W, H float64 }
type Square struct{ S float64 }

func (r Rect) Area() float64   { return r.W * r.H }
func (s Square) Area() float64 { return s.S * s.S }

func Largest(shapes []Shape) Shape {
	var best Shape
	for _, s := range shapes {
		if best == nil || s.Area() > best.Area() {
			best = s
		}
	}
	return best
}

type CountingWriter struct {
	W io.Writer
	N int
}

func (c *CountingWriter) Write(p []byte) (int, error) {
	n, err := c.W.Write(p)
	c.N += n
	return n, err
}

func Describe(v any) string {
	switch x := v.(type) {
	case nil:
		return "nil"
	case int:
		return fmt.Sprintf("int:%d", x)
	case string:
		return fmt.Sprintf("string:%d", len(x))
	case []int:
		return fmt.Sprintf("slice:%d", len(x))
	}
	return "unknown"
}

type UpperReader struct{ R io.Reader }

func (u UpperReader) Read(p []byte) (int, error) {
	n, err := u.R.Read(p)
	for i := 0; i < n; i++ {
		if p[i] >= 'a' && p[i] <= 'z' {
			p[i] -= 'a' - 'A'
		}
	}
	return n, err
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
	big := Rect{3, 4}
	check("largest", Largest([]Shape{Square{2}, big, Square{3}}), Shape(big))
	check("largest empty", Largest(nil) == nil, true)

	var sb strings.Builder
	cw := &CountingWriter{W: &sb}
	fmt.Fprint(cw, "hello ")
	fmt.Fprint(cw, "world")
	check("counting", []any{cw.N, sb.String()}, []any{11, "hello world"})

	check("describe int", Describe(42), "int:42")
	check("describe string", Describe("abc"), "string:3")
	check("describe slice", Describe([]int{1, 2}), "slice:2")
	check("describe nil", Describe(nil), "nil")
	check("describe other", Describe(1.5), "unknown")

	data, _ := io.ReadAll(UpperReader{strings.NewReader("quiet please")})
	check("upper reader", string(data), "QUIET PLEASE")
	if failed {
		os.Exit(1)
	}
}
```

</details>

Next: [10 — Files and I/O](10-files-io.md)
