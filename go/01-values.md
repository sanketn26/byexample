# Go 01 — Values, Variables and Printing

Go is statically typed, compiled, and has no implicit numeric conversions.
Every variable has a type and a *zero value*, so nothing is ever uninitialised.

## Example

```go file=example.go
package main

import (
	"fmt"
	"math"
)

// Package-level declarations; constants can be untyped.
const Pi2 = 3.14159 * 2
const (
	KB = 1 << (10 * (iota + 1)) // iota counts up inside a const block
	MB
	GB
)

func main() {
	// Declaration forms
	var a int = 10
	var b = 20 // type inferred
	c := 30    // short form, only inside functions
	var d, e = "x", true
	fmt.Println(a, b, c, d, e)

	// Zero values
	var i int
	var f float64
	var s string
	var p *int
	var ok bool
	fmt.Printf("%d %v %q %v %v\n", i, f, s, p, ok)

	// Sized numeric types and explicit conversion
	var small int8 = 127
	small++ // wraps around, no panic
	u := uint8(200)
	fmt.Println(small, u+100)
	x := 7
	y := float64(x) / 2
	fmt.Println(y, int(y), x/2, -7/2, -7%3)

	// Floats
	t1, t2 := 0.1, 0.2
	fmt.Println(t1+t2, 0.1+0.2, math.MaxInt64, math.Inf(1), math.Sqrt(2))
	fmt.Println(math.IsNaN(math.NaN()), math.NaN() == math.NaN())

	// Constants are arbitrary precision until used
	fmt.Println(KB, MB, GB, Pi2)
	const huge = 1 << 100
	fmt.Println(huge >> 98)

	// Runes and bytes
	var r rune = 'é'
	var by byte = 'A'
	fmt.Println(r, by, string(r), string(rune(by)))

	// Printf verbs
	type point struct{ X, Y int }
	pt := point{1, 2}
	fmt.Printf("%v | %+v | %#v | %T\n", pt, pt, pt, pt)
	fmt.Printf("%5d|%-5d|%05d|%x|%X|%o|%b\n", 42, 42, 42, 255, 255, 8, 5)
	fmt.Printf("%8.3f|%e|%g|%s|%q|%c|%U\n", math.Pi, 1234.5678, 1e21, "go", "go", 'G', 'G')
	fmt.Printf("%t %p\n", true, nil)
	fmt.Println(fmt.Sprintf("%03d-%s", 7, "x"))

	// Multiple assignment and swap
	m, n := 1, 2
	m, n = n, m
	fmt.Println(m, n)

	// Blank identifier discards values
	_, second := 1, 2
	fmt.Println(second)
}
```

```text output
10 20 30 x true
0 0 "" <nil> false
-128 44
3.5 3 3 -3 -1
0.30000000000000004 0.3 9223372036854775807 +Inf 1.4142135623730951
true false
1024 1048576 1073741824 6.28318
4
233 65 é A
{1 2} | {X:1 Y:2} | main.point{X:1, Y:2} | main.point
   42|42   |00042|ff|FF|10|101
   3.142|1.234568e+03|1e+21|go|"go"|G|U+0047
true %!p(<nil>)
007-x
2 1
2
```

## Details that bite

- `:=` declares *and* assigns; at least one name on the left must be new.
  Inside an inner scope it **shadows** an outer variable instead of
  assigning — a classic source of bugs.
- `0.1+0.2` written as constants is exact (prints `0.3`); the same sum on
  float64 *variables* gives `0.30000000000000004`.
- Integer division truncates toward zero: `-7/2 == -3`, and `%` takes the
  sign of the dividend.
- Overflow wraps silently for variables (`u+100` above gives 44), but a
  *constant* expression that overflows is a compile error:
  `uint8(200) + 100` does not build.
- `int` is 64-bit on 64-bit platforms but is a distinct type from `int64`;
  you must convert explicitly.
- `byte` is an alias for `uint8`, `rune` an alias for `int32`.
- Unused local variables and unused imports are **compile errors**.
- Println's output format is for humans; use `%v`/`%+v`/`%#v` to choose
  detail.

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
