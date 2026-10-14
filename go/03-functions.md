# Go 03 — Functions

Functions are values, can return multiple results, and can be generic. `defer`
schedules cleanup that runs when the surrounding function returns.

## Example

```go file=example.go
package main

import (
	"fmt"
	"strings"
)

func add(a, b int) int { return a + b }

// Multiple results; named results act as documentation (and variables).
func divmod(a, b int) (q, r int) {
	q = a / b
	r = a % b
	return // "naked" return: fine in short functions only
}

// Variadic: nums is a []int inside the function.
func sum(nums ...int) int {
	t := 0
	for _, n := range nums {
		t += n
	}
	return t
}

// Closures capture variables by reference.
func counter() func() int {
	c := 0
	return func() int {
		c++
		return c
	}
}

// Function types give names to signatures.
type Op func(int, int) int

func apply(op Op, a, b int) int { return op(a, b) }

// Generics (Go 1.18+): type parameters with constraints.
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

// defer runs LIFO when the function returns; arguments are evaluated now.
func deferDemo() {
	fmt.Println("start")
	for i := 0; i < 3; i++ {
		defer fmt.Println("deferred", i)
	}
	fmt.Println("end")
}

// A deferred closure may modify named results.
func double() (n int) {
	defer func() { n *= 2 }()
	return 21
}

func fib(n int) int {
	if n < 2 {
		return n
	}
	return fib(n-1) + fib(n-2)
}

func main() {
	fmt.Println(add(2, 3))
	q, r := divmod(17, 5)
	fmt.Println(q, r)
	fmt.Println(sum(), sum(1, 2, 3), sum([]int{4, 5}...))

	c := counter()
	fmt.Println(c(), c(), c())

	ops := map[string]Op{
		"add": add,
		"mul": func(a, b int) int { return a * b },
	}
	fmt.Println(apply(ops["add"], 2, 3), apply(ops["mul"], 2, 3))

	fmt.Println(Map([]int{1, 2, 3}, func(i int) string { return strings.Repeat("*", i) }))
	fmt.Println(Max(3, 7), Max("a", "b"))

	deferDemo()
	fmt.Println(double())
	fmt.Println(fib(10))

	// Immediately invoked function literal
	msg := func(name string) string { return "hi " + name }("go")
	fmt.Println(msg)
}
```

```text output
5
3 2
0 6 9
1 2 3
5 6
[* ** ***]
7 b
start
end
deferred 2
deferred 1
deferred 0
42
55
hi go
```

## Details that bite

- Arguments are **always passed by value**. Slices, maps and channels are
  small headers that point at shared data, so mutation through them is
  visible to the caller — but reassigning the parameter is not.
- `defer` in a loop piles up until the *function* ends, not the iteration.
  Wrap the body in a function literal if you need per-iteration cleanup.
- Deferred call arguments are evaluated at the `defer` statement:
  `defer fmt.Println(x)` prints the value `x` had then.
- Named results are zero-initialised and shadowing them with `:=` inside an
  inner block is a classic bug (`err := …` hides the named `err`).
- Functions are not comparable except to `nil`.
- There are no default or keyword arguments. Use option structs or
  functional options.

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
