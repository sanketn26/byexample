# Go 02 — Control Flow

Go has one loop keyword (`for`), a `switch` that does not fall through, and
no parentheses around conditions. Braces are mandatory. There is no `while`,
no ternary, and no `do…while`.

## `if` can declare its own variable

The name after `if` lives only for the `if` and its `else` chain. The
condition itself needs no parentheses.

```go file=n01.go
package main

import "fmt"

func main() {
	if n := 15; n%15 == 0 {
		fmt.Println("fizzbuzz")
	} else if n%3 == 0 {
		fmt.Println("fizz")
	}
}
```

```text output
fizzbuzz
```

## `for` is the only loop

The classic form has init, condition, and post. A condition alone is the
`while`. `range` over an integer (Go 1.22) counts from zero. An empty `for`
with a `break` is the `do…while`.

```go file=n02.go
package main

import "fmt"

func main() {
	for i := 0; i < 3; i++ {
		fmt.Print(i, " ")
	}
	fmt.Println()

	n := 3
	for n > 0 {
		n--
	}
	fmt.Println(n)

	for i := range 3 {
		fmt.Print(i, " ")
	}
	fmt.Println()

	k := 0
	for {
		k++
		if k == 2 {
			break
		}
	}
	fmt.Println(k)
}
```

```text output
0 1 2 
0
0 1 2 
2
```

## `range` over a string yields runes

The index is a byte offset, so it jumps by the width of each code point.
`é` occupies bytes 1 and 2, and the next rune starts at 3.

```go file=n03.go
package main

import "fmt"

func main() {
	for i, ch := range "héy" {
		fmt.Print(i, ":", string(ch), " ")
	}
	fmt.Println()
}
```

```text output
0:h 1:é 3:y 
```

## `range` copies each element

The loop variable is a copy. Assigning to it does not write back into the
slice. Assign to `xs[i]` when you mean to change the element.

```go file=n04.go
package main

import "fmt"

func main() {
	xs := []int{1, 2, 3}
	for i, v := range xs {
		v = 0
		fmt.Println(v, xs[i])
	}
}
```

```text output
0 1
0 2
0 3
```

## `switch` does not fall through

A case may list several values. Execution stops at the end of the matching
case unless you write `fallthrough`, which is rare and does not re-test the
next case.

```go file=n05.go
package main

import "fmt"

func main() {
	for _, day := range []string{"sat", "mon", "wed"} {
		switch day {
		case "sat", "sun":
			fmt.Println(day, "weekend")
		case "mon":
			fmt.Println(day, "start")
			fallthrough
		default:
			fmt.Println(day, "weekday")
		}
	}
}
```

```text output
sat weekend
mon start
mon weekday
wed weekday
```

## `break` leaves the `switch`, not the loop

A `break` inside a `switch` that sits inside a `for` ends only the
`switch`. The loop keeps going. Use a label when you mean the loop.

```go file=n06.go
package main

import "fmt"

func main() {
	n := 0
	for i := 0; i < 3; i++ {
		switch {
		case i == 1:
			break
		}
		n++
	}
	fmt.Println(n)
}
```

```text output
3
```

## A label leaves the outer loop

`break outer` exits the named loop, not merely the inner one.

```go file=n07.go
package main

import "fmt"

func main() {
	found := [2]int{}
outer:
	for i := 1; i < 5; i++ {
		for j := 1; j < 5; j++ {
			if i*j == 6 {
				found = [2]int{i, j}
				break outer
			}
		}
	}
	fmt.Println(found)
}
```

```text output
[2 3]
```

## Each iteration has its own variable

Since Go 1.22 a closure takes the value from that iteration, not the final
one. The `go` line in `go.mod` selects the old shared-variable behaviour
on earlier versions.

```go file=n08.go
package main

import "fmt"

func main() {
	var fs []func() int
	for i := range 3 {
		fs = append(fs, func() int { return i })
	}
	for _, f := range fs {
		fmt.Print(f(), " ")
	}
	fmt.Println()
}
```

```text output
0 1 2 
```

## A type switch narrows `any`

The name after `.(type)` has the case's type inside that arm. Several
types may share a case. A `nil` interface matches `case nil`.

```go file=n09.go
package main

import (
	"fmt"
	"strings"
)

func main() {
	for _, v := range []any{1, "s", 2.5, nil, []int{1}} {
		switch x := v.(type) {
		case int:
			fmt.Println("int", x+1)
		case string:
			fmt.Println("string", strings.ToUpper(x))
		case float64, float32:
			fmt.Println("float", x)
		case nil:
			fmt.Println("nil")
		default:
			fmt.Printf("other %T\n", x)
		}
	}
}
```

```text output
int 2
string S
float 2.5
nil
other []int
```

## A tagless `switch` replaces an if-else ladder

With no value after `switch`, each case is a boolean. The first true case
runs.

```go file=n10.go
package main

import "fmt"

func main() {
	score := 83
	switch {
	case score >= 90:
		fmt.Println("A")
	case score >= 80:
		fmt.Println("B")
	default:
		fmt.Println("C")
	}
}
```

```text output
B
```

## `range` over a map is unordered

Go visits map keys in a deliberate random order. Sort the keys when the
output has to be stable.

```go file=n11.go
package main

import (
	"fmt"
	"slices"
)

func main() {
	m := map[string]int{"b": 2, "a": 1}
	var keys []string
	for k := range m {
		keys = append(keys, k)
	}
	slices.Sort(keys)
	fmt.Println(keys)
}
```

```text output
[a b]
```

## Exercises

```go file=exercise.go
package main

import (
	"fmt"
	"os"
	"reflect"
)

// FizzBuzz returns the strings for 1..n.
func FizzBuzz(n int) []string {
	return nil // TODO
}

// CollatzSteps counts steps to reach 1; returns -1 for n < 1.
func CollatzSteps(n int) int {
	return 0 // TODO
}

// FirstRepeat returns the first value that appears a second time.
func FirstRepeat(xs []int) (int, bool) {
	return 0, false // TODO
}

// Primes returns all primes <= limit in ascending order.
func Primes(limit int) []int {
	return nil // TODO
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
	check("fizzbuzz", FizzBuzz(15)[10:], []string{"11", "Fizz", "13", "14", "FizzBuzz"})
	check("collatz 1", CollatzSteps(1), 0)
	check("collatz 27", CollatzSteps(27), 111)
	check("collatz 0", CollatzSteps(0), -1)
	v, ok := FirstRepeat([]int{3, 1, 4, 1, 5, 3})
	check("repeat", []any{v, ok}, []any{1, true})
	_, ok = FirstRepeat([]int{1, 2, 3})
	check("no repeat", ok, false)
	check("primes", Primes(30), []int{2, 3, 5, 7, 11, 13, 17, 19, 23, 29})
	check("primes small", Primes(1), []int(nil))
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
	"strconv"
)

func FizzBuzz(n int) []string {
	var out []string
	for i := 1; i <= n; i++ {
		switch {
		case i%15 == 0:
			out = append(out, "FizzBuzz")
		case i%3 == 0:
			out = append(out, "Fizz")
		case i%5 == 0:
			out = append(out, "Buzz")
		default:
			out = append(out, strconv.Itoa(i))
		}
	}
	return out
}

func CollatzSteps(n int) int {
	if n < 1 {
		return -1
	}
	steps := 0
	for n != 1 {
		if n%2 == 0 {
			n /= 2
		} else {
			n = 3*n + 1
		}
		steps++
	}
	return steps
}

func FirstRepeat(xs []int) (int, bool) {
	seen := map[int]bool{}
	for _, x := range xs {
		if seen[x] {
			return x, true
		}
		seen[x] = true
	}
	return 0, false
}

func Primes(limit int) []int {
	var out []int
	if limit < 2 {
		return out
	}
	composite := make([]bool, limit+1)
	for i := 2; i <= limit; i++ {
		if composite[i] {
			continue
		}
		out = append(out, i)
		for j := i * i; j <= limit; j += i {
			composite[j] = true
		}
	}
	return out
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
	check("fizzbuzz", FizzBuzz(15)[10:], []string{"11", "Fizz", "13", "14", "FizzBuzz"})
	check("collatz 1", CollatzSteps(1), 0)
	check("collatz 27", CollatzSteps(27), 111)
	check("collatz 0", CollatzSteps(0), -1)
	v, ok := FirstRepeat([]int{3, 1, 4, 1, 5, 3})
	check("repeat", []any{v, ok}, []any{1, true})
	_, ok = FirstRepeat([]int{1, 2, 3})
	check("no repeat", ok, false)
	check("primes", Primes(30), []int{2, 3, 5, 7, 11, 13, 17, 19, 23, 29})
	check("primes small", Primes(1), []int(nil))
	if failed {
		os.Exit(1)
	}
}
```

</details>

Next: [03 — Functions](03-functions.md)
