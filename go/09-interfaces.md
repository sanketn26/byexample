# Go 09 — Interfaces

Interfaces are satisfied implicitly: a type implements an interface by
having the methods, with no declaration. Define small interfaces where they
are used (`io.Reader`, `fmt.Stringer`), accept interfaces, and return
concrete types. Do not add an interface until a second implementation or a
test double appears. `any` drops every static check; prefer generics when
the logic is the same for several types.

## Types satisfy interfaces with no declaration

`Rect` and `Circle` are `Shape` because they have `Area`. `var _ Shape = Rect{}`
fails the build if that stops being true. The method set of `T` has only
value receivers; `*T` has both. Storing a `T` where the methods use pointer
receivers does not compile.

```go file=n01.go
package main

import (
	"fmt"
	"math"
)

type Shape interface {
	Area() float64
}

type Rect struct{ W, H float64 }
type Circle struct{ R float64 }

func (r Rect) Area() float64   { return r.W * r.H }
func (c Circle) Area() float64 { return math.Pi * c.R * c.R }

var _ Shape = Rect{}

func main() {
	shapes := []Shape{Rect{3, 4}, Circle{1}}
	for _, s := range shapes {
		fmt.Printf("%T %.2f\n", s, s.Area())
	}
}
```

```text output
main.Rect 12.00
main.Circle 3.14
```

## Wrap an interface to change the bytes

`upperWriter` is an `io.Writer` because it has `Write`. It forwards to
another writer after upper-casing. Callers pass it anywhere a `Writer` is
wanted.

```go file=n02.go
package main

import (
	"bytes"
	"fmt"
	"io"
	"os"
)

type upperWriter struct{ w io.Writer }

func (u upperWriter) Write(p []byte) (int, error) {
	return u.w.Write(bytes.ToUpper(p))
}

func main() {
	fmt.Fprintf(upperWriter{os.Stdout}, "hello %d\n", 5)
}
```

```text output
HELLO 5
```

## A comma-ok assertion never panics

`v.(T)` panics when `v` does not hold a `T`. The two-result form returns
the zero value and false instead. Use it when the type is only a
possibility.

```go file=n03.go
package main

import "fmt"

func main() {
	var v any = "hi"
	s, ok := v.(string)
	n, ok2 := v.(int)
	fmt.Println(s, ok, n, ok2)
}
```

```text output
hi true 0 false
```

## Three methods are enough to sort

`sort.Interface` is `Len`, `Less`, and `Swap`. A named slice type adds
those methods, and `sort.Sort` does the rest. `byLen` sorts by length, not
by text.

```go file=n04.go
package main

import (
	"fmt"
	"sort"
)

type byLen []string

func (b byLen) Len() int           { return len(b) }
func (b byLen) Less(i, j int) bool { return len(b[i]) < len(b[j]) }
func (b byLen) Swap(i, j int)      { b[i], b[j] = b[j], b[i] }

func main() {
	words := []string{"ccc", "a", "bb"}
	sort.Sort(byLen(words))
	fmt.Println(words)
}
```

```text output
[a bb ccc]
```

## A tiny interface is easy to replace

`greeting` asks only for `Now`. A test passes a clock stuck at 09:00
instead of the real time. A twelve-line fake beats a mock framework.

```go file=n05.go
package main

import (
	"fmt"
	"time"
)

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
	morning := fixedClock{time.Date(2026, 1, 1, 9, 0, 0, 0, time.UTC)}
	fmt.Println(greeting(morning))
}
```

```text output
good morning
```

## An interface holding a nil pointer is not nil

The interface value is `(type, pointer)`. The pointer may be nil while the
type is set, and then `s == nil` is false. Return a bare `nil` when there
is no value. See also the typed-nil trap in the errors lesson.

```go file=n06.go
package main

import "fmt"

type Shape interface{ Area() float64 }

type Rect struct{ W, H float64 }

func (r *Rect) Area() float64 {
	if r == nil {
		return 0
	}
	return r.W * r.H
}

func main() {
	var p *Rect
	var s Shape = p
	fmt.Println(p == nil, s == nil)
}
```

```text output
true false
```

## Comparing uncomparable dynamic types panics

`==` on two interfaces looks at the values inside. Slices, maps, and
functions are not comparable, so the comparison panics at run time even
though the program compiled.

```go file=n07.go
package main

import "fmt"

func main() {
	defer func() { fmt.Println("recovered:", recover()) }()
	var a any = []int{1}
	var b any = []int{1}
	fmt.Println(a == b)
}
```

```text output
recovered: runtime error: comparing uncomparable type []int
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
