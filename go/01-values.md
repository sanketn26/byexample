# Go 01 — Values, Variables and Printing

Go is statically typed, compiled, and has no implicit numeric conversions.
Every variable has a type and a zero value, so nothing is ever uninitialised.
An unused local or an unused import is a compile error.

## `var` and `:=` declare names

`var` can name the type or let the compiler infer it. `:=` declares and
assigns, and it is legal only inside a function. At least one name on the
left must be new. In an inner block that same `:=` shadows the outer name
instead of assigning to it.

```go file=n01.go
package main

import "fmt"

func main() {
	var a int = 10
	var b = 20
	c := 30
	var d, e = "x", true
	fmt.Println(a, b, c, d, e)

	n := 1
	if true {
		n := 2
		fmt.Println(n)
	}
	fmt.Println(n)
}
```

```text output
10 20 30 x true
2
1
```

## Zero values fill what you do not set

A variable with no explicit initializer is still set: numbers to `0`,
strings to `""`, bools to `false`, pointers to `nil`.

```go file=n02.go
package main

import "fmt"

func main() {
	var i int
	var f float64
	var s string
	var p *int
	var ok bool
	fmt.Printf("%d %v %q %v %v\n", i, f, s, p, ok)
}
```

```text output
0 0 "" <nil> false
```

## Integer variables wrap

A variable that passes its range wraps with no panic: incrementing
`int8(127)` yields `-128`, and `uint8(200) + 100` is `44`. The same
overflow written as a constant expression does not compile. Division
truncates toward zero, so `-7/2` is `-3` and `%` takes the sign of the
dividend. `int` and `int64` are different types even on a
64-bit machine; convert with `int64(x)`.

```go file=n03.go
package main

import "fmt"

func main() {
	var small int8 = 127
	small++
	u := uint8(200)
	fmt.Println(small, u+100)

	x := 7
	y := float64(x) / 2
	fmt.Println(y, int(y), x/2, -7/2, -7%3)
}
```

```text output
-128 44
3.5 3 3 -3 -1
```

## Float variables are approximate

`0.1 + 0.2` written as constants prints `0.3`. The same sum of `float64`
variables is not `0.3`. `NaN` is not equal to itself; test it with
`math.IsNaN`.

```go file=n04.go
package main

import (
	"fmt"
	"math"
)

func main() {
	t1, t2 := 0.1, 0.2
	fmt.Println(t1+t2, 0.1+0.2)
	fmt.Println(math.MaxInt64, math.Inf(1), math.Sqrt(2))
	fmt.Println(math.IsNaN(math.NaN()), math.NaN() == math.NaN())
}
```

```text output
0.30000000000000004 0.3
9223372036854775807 +Inf 1.4142135623730951
true false
```

## Constants stay precise until they are used

`iota` counts up from zero inside one `const` block. An untyped constant
may be far wider than any integer variable; the narrowing happens when a
variable finally stores it.

```go file=n05.go
package main

import "fmt"

const Pi2 = 3.14159 * 2

const (
	KB = 1 << (10 * (iota + 1))
	MB
	GB
)

func main() {
	fmt.Println(KB, MB, GB, Pi2)
	const huge = 1 << 100
	fmt.Println(huge >> 98)
}
```

```text output
1024 1048576 1073741824 6.28318
4
```

## `rune` and `byte` are integer aliases

A `rune` is an `int32` code point. A `byte` is a `uint8`. `string` of a
rune prints the character, not the number.

```go file=n06.go
package main

import "fmt"

func main() {
	var r rune = 'é'
	var by byte = 'A'
	fmt.Println(r, by, string(r), string(rune(by)))
}
```

```text output
233 65 é A
```

## `Printf` chooses the detail

`Println` is for humans. `%v`, `%+v`, `%#v`, and `%T` add structure, field
names, the Go form, and the type. `%p` of an untyped `nil` is the stable
text `%!p(<nil>)`, not an address.

```go file=n07.go
package main

import (
	"fmt"
	"math"
)

type point struct{ X, Y int }

func main() {
	pt := point{1, 2}
	fmt.Printf("%v | %+v | %#v | %T\n", pt, pt, pt, pt)
	fmt.Printf("%5d|%-5d|%05d|%x|%X|%o|%b\n", 42, 42, 42, 255, 255, 8, 5)
	fmt.Printf("%8.3f|%e|%g|%s|%q|%c|%U\n", math.Pi, 1234.5678, 1e21, "go", "go", 'G', 'G')
	fmt.Printf("%t %p\n", true, nil)
	fmt.Println(fmt.Sprintf("%03d-%s", 7, "x"))
}
```

```text output
{1 2} | {X:1 Y:2} | main.point{X:1, Y:2} | main.point
   42|42   |00042|ff|FF|10|101
   3.142|1.234568e+03|1e+21|go|"go"|G|U+0047
true %!p(<nil>)
007-x
```

## One statement can assign many names

The right-hand side runs first, so a swap needs no temporary. `_` throws a
value away.

```go file=n08.go
package main

import "fmt"

func main() {
	m, n := 1, 2
	m, n = n, m
	fmt.Println(m, n)
	_, second := 1, 2
	fmt.Println(second)
}
```

```text output
2 1
2
```

## Exercises

```go file=exercise.go
package main

import (
	"fmt"
	"os"
)

// CelsiusToFahrenheit converts degrees Celsius to Fahrenheit.
func CelsiusToFahrenheit(c float64) float64 {
	return 0 // TODO
}

// DivMod returns floor quotient and non-negative remainder for b > 0,
// i.e. DivMod(-7, 2) == (-4, 1) (Go's / and % truncate toward zero).
func DivMod(a, b int) (int, int) {
	return 0, 0 // TODO
}

// Wrap8 returns n as it would be stored in an int8 (wrapping around).
func Wrap8(n int) int8 {
	return 0 // TODO
}

// Describe returns "negative", "zero" or "positive".
func Describe(n int) string {
	return "" // TODO
}

var failed bool

func check[T comparable](label string, got, want T) {
	if got == want {
		fmt.Println("PASS", label)
		return
	}
	failed = true
	fmt.Printf("FAIL %s: got %v, want %v\n", label, got, want)
}

func main() {
	check("c2f(100)", CelsiusToFahrenheit(100), 212.0)
	check("c2f(-40)", CelsiusToFahrenheit(-40), -40.0)
	q, r := DivMod(-7, 2)
	check("divmod q", q, -4)
	check("divmod r", r, 1)
	q, r = DivMod(7, 2)
	check("divmod pos", [2]int{q, r}, [2]int{3, 1})
	check("wrap8(130)", Wrap8(130), int8(-126))
	check("wrap8(-129)", Wrap8(-129), int8(127))
	check("describe", Describe(-3)+Describe(0)+Describe(9), "negativezeropositive")
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
	"os"
)

func CelsiusToFahrenheit(c float64) float64 {
	return c*9/5 + 32
}

func DivMod(a, b int) (int, int) {
	q, r := a/b, a%b
	if r < 0 {
		q--
		r += b
	}
	return q, r
}

func Wrap8(n int) int8 {
	return int8(n)
}

func Describe(n int) string {
	switch {
	case n < 0:
		return "negative"
	case n == 0:
		return "zero"
	default:
		return "positive"
	}
}

var failed bool

func check[T comparable](label string, got, want T) {
	if got == want {
		fmt.Println("PASS", label)
		return
	}
	failed = true
	fmt.Printf("FAIL %s: got %v, want %v\n", label, got, want)
}

func main() {
	check("c2f(100)", CelsiusToFahrenheit(100), 212.0)
	check("c2f(-40)", CelsiusToFahrenheit(-40), -40.0)
	q, r := DivMod(-7, 2)
	check("divmod q", q, -4)
	check("divmod r", r, 1)
	q, r = DivMod(7, 2)
	check("divmod pos", [2]int{q, r}, [2]int{3, 1})
	check("wrap8(130)", Wrap8(130), int8(-126))
	check("wrap8(-129)", Wrap8(-129), int8(127))
	check("describe", Describe(-3)+Describe(0)+Describe(9), "negativezeropositive")
	if failed {
		os.Exit(1)
	}
}
```

</details>

Next: [02 — Control flow](02-control-flow.md)
