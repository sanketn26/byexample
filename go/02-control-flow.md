# Go 02 — Control Flow

Go has one loop keyword (`for`), a `switch` that does not fall through, and
no parentheses around conditions. Braces are mandatory.

## Example

```go file=example.go
package main

import (
	"fmt"
	"strings"
)

func main() {
	// if with an init statement; n is scoped to the if/else chain
	if n := 15; n%15 == 0 {
		fmt.Println("fizzbuzz")
	} else if n%3 == 0 {
		fmt.Println("fizz")
	}

	// The three forms of for
	for i := 0; i < 3; i++ { // classic
		fmt.Print(i, " ")
	}
	fmt.Println()

	n := 3
	for n > 0 { // while
		n--
	}
	fmt.Println(n)

	for i := range 3 { // range over an int (Go 1.22+)
		fmt.Print(i, " ")
	}
	fmt.Println()

	// range over a string yields (byte index, rune)
	for i, ch := range "héy" {
		fmt.Print(i, ":", string(ch), " ")
	}
	fmt.Println()

	// switch: no fall-through by default, multiple values per case
	for _, day := range []string{"sat", "mon", "wed"} {
		switch day {
		case "sat", "sun":
			fmt.Println(day, "weekend")
		case "mon":
			fmt.Println(day, "start")
			fallthrough // explicit, and rare
		default:
			fmt.Println(day, "weekday")
		}
	}

	// Labelled break leaves nested loops
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

	// Since Go 1.22 each iteration has its own loop variable
	var fs []func() int
	for i := range 3 {
		fs = append(fs, func() int { return i })
	}
	for _, f := range fs {
		fmt.Print(f(), " ")
	}
	fmt.Println()

	// Type switch
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

	// Tagless switch replaces if/else ladders
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
fizzbuzz
0 1 2 
0
0 1 2 
0:h 1:é 3:y 
sat weekend
mon start
mon weekday
wed weekday
[2 3]
0 1 2 
int 2
string S
float 2.5
nil
other []int
B
```

## Details that bite

- There is no `while`, no ternary operator, and no `do…while`. Use
  `for cond {}`, an `if`, and `for { …; if !cond { break } }`.
- A `break` inside a `switch` inside a `for` only leaves the `switch`. Use a
  label to leave the loop.
- `range` over a string decodes UTF-8: the index jumps by the byte width of
  each rune (note `é` took indexes 1–2).
- `range` over a slice copies each element into the loop variable;
  modifying `v` in `for _, v := range xs` does not change `xs`.
- Before Go 1.22 all iterations shared one loop variable, so closures
  captured the final value. The module's `go` directive in `go.mod` decides
  which behaviour you get.
- `range` over a map visits keys in **random** order, deliberately.

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
