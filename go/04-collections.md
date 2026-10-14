# Go 04 — Arrays, Slices and Maps

Arrays are fixed-size values. Slices are views onto arrays and are what you
use day to day. Maps are hash tables.

## Example

```go file=example.go
package main

import (
	"cmp"
	"fmt"
	"maps"
	"slices"
)

type person struct {
	Name string
	Age  int
}

func main() {
	// Arrays are values: assignment copies
	a := [3]int{1, 2, 3}
	b := a
	b[0] = 99
	fmt.Println(a, b, len(a))

	// Slices: pointer + length + capacity
	s := []int{1, 2, 3}
	s = append(s, 4, 5)
	fmt.Println(s, len(s), s[1:3], s[:2], s[3:])

	// Appending within capacity shares the backing array
	base := make([]int, 3, 10)
	t := append(base, 1)
	u := append(base, 2) // overwrites t[3]
	fmt.Println(t, u, len(base), cap(base))

	// A full slice expression caps capacity so append must copy
	w := base[:3:3]
	w = append(w, 7)
	fmt.Println(base[:4], w)

	// copy and delete
	dst := make([]int, 2)
	n := copy(dst, s)
	fmt.Println(n, dst)
	s = append(s[:1], s[2:]...) // remove index 1
	fmt.Println(s)

	// slices package
	nums := []int{5, 2, 8, 1}
	slices.Sort(nums)
	fmt.Println(nums, slices.Contains(nums, 8), slices.Index(nums, 5))
	idx, found := slices.BinarySearch(nums, 5)
	fmt.Println(idx, found, slices.Max(nums))

	// nil vs empty
	var ns []int
	es := []int{}
	fmt.Println(ns == nil, es == nil, len(ns), len(es))

	// Maps
	ages := map[string]int{"ann": 31, "bob": 25}
	ages["cy"] = 40
	v, ok := ages["dan"] // comma-ok distinguishes missing from zero
	fmt.Println(v, ok, len(ages))
	delete(ages, "bob")
	fmt.Println(slices.Sorted(maps.Keys(ages))) // Go 1.23+

	counts := map[rune]int{}
	for _, r := range "banana" {
		counts[r]++ // missing key reads as zero
	}
	fmt.Println(counts) // fmt prints maps sorted by key

	// Writing to a nil map panics
	func() {
		defer func() { fmt.Println("recovered:", recover()) }()
		var m map[string]int
		m["a"] = 1
	}()

	// A set is a map to an empty struct
	set := map[string]struct{}{}
	set["a"] = struct{}{}
	_, in := set["a"]
	fmt.Println(in, len(set))

	// 2-D slice
	grid := make([][]int, 2)
	for i := range grid {
		grid[i] = make([]int, 3)
	}
	grid[1][2] = 5
	fmt.Println(grid)

	// Sorting structs with a comparison function
	people := []person{{"Al", 30}, {"Bo", 25}, {"Cy", 30}}
	slices.SortFunc(people, func(x, y person) int {
		return cmp.Or(cmp.Compare(y.Age, x.Age), cmp.Compare(x.Name, y.Name))
	})
	fmt.Println(people)
}
```

```text output
[1 2 3] [99 2 3] 3
[1 2 3 4 5] 5 [2 3] [1 2] [4 5]
[0 0 0 2] [0 0 0 2] 3 10
[0 0 0 2] [0 0 0 7]
2 [1 2]
[1 3 4 5]
[1 2 5 8] true 2
2 true 8
true false 0 0
0 false 3
[ann cy]
map[97:3 98:1 110:2]
recovered: assignment to entry in nil map
true 1
[[0 0 0] [0 0 5]]
[{Al 30} {Cy 30} {Bo 25}]
```

## Details that bite

- `append` may or may not reallocate. Always assign its result
  (`s = append(s, x)`), and assume the old slice may or may not alias the
  new one.
- Sub-slices keep the **whole** backing array alive. Copy out small pieces
  of huge slices (`slices.Clone`) to let the memory go.
- Slices cannot be compared with `==` (only to `nil`) and cannot be map
  keys; arrays can.
- `delete` on a missing key is a no-op; reading a missing key yields the
  zero value, so use `v, ok := m[k]` when the difference matters.
- Maps are not safe for concurrent writes; guard with a mutex or use
  channels.
- Modifying a struct held in a map directly (`m[k].f = 1`) does not compile;
  store pointers or copy, modify, and reassign.

## Exercises

```go file=exercise.go
package main

import (
	"fmt"
	"os"
	"reflect"
)

// Reverse reverses s in place.
func Reverse(s []int) {
	// TODO
}

// Unique returns xs without duplicates, keeping first occurrences.
func Unique(xs []int) []int {
	return nil // TODO
}

// WordCount returns lowercase word frequencies (split on whitespace).
func WordCount(text string) map[string]int {
	return nil // TODO
}

// Rotate returns a NEW slice rotated left by k (k may exceed len).
func Rotate(xs []int, k int) []int {
	return nil // TODO
}

// GroupByLen maps word length to words, keeping input order.
func GroupByLen(words []string) map[int][]string {
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
	r := []int{1, 2, 3, 4}
	Reverse(r)
	check("reverse", r, []int{4, 3, 2, 1})
	check("unique", Unique([]int{3, 1, 3, 2, 1}), []int{3, 1, 2})
	check("wordcount", WordCount("The cat the  hat"), map[string]int{"the": 2, "cat": 1, "hat": 1})
	orig := []int{1, 2, 3, 4, 5}
	check("rotate", Rotate(orig, 7), []int{3, 4, 5, 1, 2})
	check("rotate immutable", orig, []int{1, 2, 3, 4, 5})
	check("rotate empty", len(Rotate(nil, 3)), 0)
	check("group", GroupByLen([]string{"a", "bb", "c", "dd", "eee"}),
		map[int][]string{1: {"a", "c"}, 2: {"bb", "dd"}, 3: {"eee"}})
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
	"strings"
)

func Reverse(s []int) {
	for i, j := 0, len(s)-1; i < j; i, j = i+1, j-1 {
		s[i], s[j] = s[j], s[i]
	}
}

func Unique(xs []int) []int {
	seen := make(map[int]struct{}, len(xs))
	var out []int
	for _, x := range xs {
		if _, ok := seen[x]; !ok {
			seen[x] = struct{}{}
			out = append(out, x)
		}
	}
	return out
}

func WordCount(text string) map[string]int {
	counts := map[string]int{}
	for _, w := range strings.Fields(text) {
		counts[strings.ToLower(w)]++
	}
	return counts
}

func Rotate(xs []int, k int) []int {
	n := len(xs)
	out := make([]int, n)
	if n == 0 {
		return out
	}
	k %= n
	copy(out, xs[k:])
	copy(out[n-k:], xs[:k])
	return out
}

func GroupByLen(words []string) map[int][]string {
	g := map[int][]string{}
	for _, w := range words {
		g[len(w)] = append(g[len(w)], w)
	}
	return g
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
	r := []int{1, 2, 3, 4}
	Reverse(r)
	check("reverse", r, []int{4, 3, 2, 1})
	check("unique", Unique([]int{3, 1, 3, 2, 1}), []int{3, 1, 2})
	check("wordcount", WordCount("The cat the  hat"), map[string]int{"the": 2, "cat": 1, "hat": 1})
	orig := []int{1, 2, 3, 4, 5}
	check("rotate", Rotate(orig, 7), []int{3, 4, 5, 1, 2})
	check("rotate immutable", orig, []int{1, 2, 3, 4, 5})
	check("rotate empty", len(Rotate(nil, 3)), 0)
	check("group", GroupByLen([]string{"a", "bb", "c", "dd", "eee"}),
		map[int][]string{1: {"a", "c"}, 2: {"bb", "dd"}, 3: {"eee"}})
	if failed {
		os.Exit(1)
	}
}
```

</details>

Next: [05 — Strings](05-strings.md)
