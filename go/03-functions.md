# Go 03 — Functions

Functions are values, can return multiple results, and can be generic.
`defer` schedules a call that runs when the surrounding function returns.
There are no default or keyword arguments: pass every value, or take a
variadic list.

## Several results can be named

Named results are ordinary variables, already zeroed, and they document the
return. A bare `return` sends them back. Keep that form to short functions.

```go file=n01.go
package main

import "fmt"

func add(a, b int) int { return a + b }

func divmod(a, b int) (q, r int) {
	q = a / b
	r = a % b
	return
}

func main() {
	fmt.Println(add(2, 3))
	q, r := divmod(17, 5)
	fmt.Println(q, r)
}
```

```text output
5
3 2
```

## Variadic arguments arrive as a slice

Inside the function, `nums ...int` is a `[]int`. Callers pass values one by
one, or unpack a slice with `...`.

```go file=n02.go
package main

import "fmt"

func sum(nums ...int) int {
	t := 0
	for _, n := range nums {
		t += n
	}
	return t
}

func main() {
	fmt.Println(sum(), sum(1, 2, 3), sum([]int{4, 5}...))
}
```

```text output
0 6 9
```

## Closures capture variables, not copies

The returned function shares `c` with the scope that created it. Each call
sees the latest value.

```go file=n03.go
package main

import "fmt"

func counter() func() int {
	c := 0
	return func() int {
		c++
		return c
	}
}

func main() {
	c := counter()
	fmt.Println(c(), c(), c())
}
```

```text output
1 2 3
```

## A function value has a type

A named signature such as `Op` is what you store in a map or pass around.
Functions compare equal only to `nil`; two non-nil functions are not
comparable.

```go file=n04.go
package main

import "fmt"

type Op func(int, int) int

func apply(op Op, a, b int) int { return op(a, b) }

func add(a, b int) int { return a + b }

func main() {
	var missing Op
	ops := map[string]Op{
		"add": add,
		"mul": func(a, b int) int { return a * b },
	}
	fmt.Println(apply(ops["add"], 2, 3), apply(ops["mul"], 2, 3))
	fmt.Println(missing == nil)
}
```

```text output
5 6
true
```

## Type parameters constrain generics

The names in `[T, U any]` stand for types the caller supplies. A constraint
such as `Ordered` lists the types (and their underlying types, via `~`)
that the body may use.

```go file=n05.go
package main

import (
	"fmt"
	"strings"
)

func Map[T, U any](xs []T, f func(T) U) []U {
	out := make([]U, 0, len(xs))
	for _, x := range xs {
		out = append(out, f(x))
	}
	return out
}

type Ordered interface {
	~int | ~float64 | ~string
}

func Max[T Ordered](a, b T) T {
	if a > b {
		return a
	}
	return b
}

func main() {
	fmt.Println(Map([]int{1, 2, 3}, func(i int) string { return strings.Repeat("*", i) }))
	fmt.Println(Max(3, 7), Max("a", "b"))
}
```

```text output
[* ** ***]
7 b
```

## Arguments are copied

The callee receives a copy of each argument. A slice, map, or channel copy
is only the small header, so writes through it are visible to the caller.
Reassigning the parameter is not.

```go file=n06.go
package main

import "fmt"

func mutate(s []int, m map[string]int) {
	s[0] = 9
	m["a"] = 1
	s = []int{7}
	m = map[string]int{"b": 2}
}

func main() {
	s := []int{1}
	m := map[string]int{}
	mutate(s, m)
	fmt.Println(s, m)
}
```

```text output
[9] map[a:1]
```

## `defer` runs when the function returns

Deferred calls run last-in, first-out, after the rest of the function, not
at the end of the loop iteration. Wrap the body in a function literal when
cleanup has to run each time around.

```go file=n07.go
package main

import "fmt"

func deferDemo() {
	fmt.Println("start")
	for i := 0; i < 3; i++ {
		defer fmt.Println("deferred", i)
	}
	fmt.Println("end")
}

func main() {
	deferDemo()
}
```

```text output
start
end
deferred 2
deferred 1
deferred 0
```

## `defer` arguments are evaluated immediately

The values passed to a deferred call are computed at the `defer` line. The
call itself waits.

```go file=n08.go
package main

import "fmt"

func main() {
	x := 1
	defer fmt.Println("later", x)
	x = 2
	fmt.Println("now", x)
}
```

```text output
now 2
later 1
```

## A deferred function can change named results

The deferred call runs after `return 21` has stored `21` in `n`, and it
may still assign to that name.

```go file=n09.go
package main

import "fmt"

func double() (n int) {
	defer func() { n *= 2 }()
	return 21
}

func main() {
	fmt.Println(double())
}
```

```text output
42
```

## `:=` can shadow a named result

A named result is already declared. `:=` in an inner block creates a new
variable and leaves the result untouched. Assign with `=` when you mean
the result.

```go file=n10.go
package main

import (
	"errors"
	"fmt"
)

func parse() (n int, err error) {
	{
		n, err := 7, errors.New("boom")
		fmt.Println("inner", n, err)
	}
	return
}

func main() {
	fmt.Println(parse())
}
```

```text output
inner 7 boom
0 <nil>
```

## Recursion is an ordinary call

The function calls itself with a smaller argument. There is no special
keyword. The base case returns before the calls.

```go file=n11.go
package main

import "fmt"

func fib(n int) int {
	if n < 2 {
		return n
	}
	return fib(n-1) + fib(n-2)
}

func main() {
	fmt.Println(fib(10))
}
```

```text output
55
```

## A function literal can run at once

Parentheses after the closing brace call the function before the statement
ends. It is the same as binding a name and calling it on the next line.

```go file=n12.go
package main

import "fmt"

func main() {
	msg := func(name string) string { return "hi " + name }("go")
	fmt.Println(msg)
}
```

```text output
hi go
```

## Exercises

```go file=exercise.go
package main

import (
	"fmt"
	"os"
	"reflect"
)

// Filter returns the elements for which keep returns true.
func Filter[T any](xs []T, keep func(T) bool) []T {
	return nil // TODO
}

// Reduce folds xs into a single value starting from init.
func Reduce[T, A any](xs []T, init A, f func(A, T) A) A {
	var zero A
	return zero // TODO
}

// MakeAccumulator returns a func that adds its argument to a running total.
func MakeAccumulator(start int) func(int) int {
	return func(int) int { return 0 } // TODO
}

// Memoize caches results of f by argument.
func Memoize(f func(int) int) func(int) int {
	return f // TODO
}

// MinMax returns the smallest and largest of xs; ok is false if xs is empty.
func MinMax(xs ...int) (lo, hi int, ok bool) {
	return // TODO
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
	even := func(n int) bool { return n%2 == 0 }
	check("filter", Filter([]int{1, 2, 3, 4}, even), []int{2, 4})
	check("reduce", Reduce([]string{"a", "bb", "ccc"}, 0, func(n int, s string) int { return n + len(s) }), 6)

	acc := MakeAccumulator(10)
	acc(5)
	check("accumulator", acc(5), 20)

	calls := 0
	sq := Memoize(func(n int) int { calls++; return n * n })
	sq(4)
	check("memoize", []int{sq(4), calls}, []int{16, 1})

	lo, hi, ok := MinMax(3, 9, -2, 5)
	check("minmax", []any{lo, hi, ok}, []any{-2, 9, true})
	_, _, ok = MinMax()
	check("minmax empty", ok, false)
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
	"reflect"
)

func Filter[T any](xs []T, keep func(T) bool) []T {
	var out []T
	for _, x := range xs {
		if keep(x) {
			out = append(out, x)
		}
	}
	return out
}

func Reduce[T, A any](xs []T, init A, f func(A, T) A) A {
	acc := init
	for _, x := range xs {
		acc = f(acc, x)
	}
	return acc
}

func MakeAccumulator(start int) func(int) int {
	total := start
	return func(n int) int {
		total += n
		return total
	}
}

func Memoize(f func(int) int) func(int) int {
	cache := map[int]int{}
	return func(n int) int {
		if v, ok := cache[n]; ok {
			return v
		}
		v := f(n)
		cache[n] = v
		return v
	}
}

func MinMax(xs ...int) (lo, hi int, ok bool) {
	if len(xs) == 0 {
		return
	}
	lo, hi = xs[0], xs[0]
	for _, x := range xs[1:] {
		lo = min(lo, x)
		hi = max(hi, x)
	}
	return lo, hi, true
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
	even := func(n int) bool { return n%2 == 0 }
	check("filter", Filter([]int{1, 2, 3, 4}, even), []int{2, 4})
	check("reduce", Reduce([]string{"a", "bb", "ccc"}, 0, func(n int, s string) int { return n + len(s) }), 6)

	acc := MakeAccumulator(10)
	acc(5)
	check("accumulator", acc(5), 20)

	calls := 0
	sq := Memoize(func(n int) int { calls++; return n * n })
	sq(4)
	check("memoize", []int{sq(4), calls}, []int{16, 1})

	lo, hi, ok := MinMax(3, 9, -2, 5)
	check("minmax", []any{lo, hi, ok}, []any{-2, 9, true})
	_, _, ok = MinMax()
	check("minmax empty", ok, false)
	if failed {
		os.Exit(1)
	}
}
```

</details>

Next: [04 — Collections](04-collections.md)
