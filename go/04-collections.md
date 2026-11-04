# Go 04 — Arrays, Slices and Maps

Arrays are fixed-size values. Slices are views onto arrays and are what you
use day to day. Maps are hash tables. A map is not safe for concurrent
writes; guard it with a mutex, or pass values on a channel instead.

## Arrays are copied on assignment

The size is part of the type. `b := a` duplicates every element, so later
writes to `b` leave `a` alone.

```go file=n01.go
package main

import "fmt"

func main() {
	a := [3]int{1, 2, 3}
	b := a
	b[0] = 99
	fmt.Println(a, b, len(a))
}
```

```text output
[1 2 3] [99 2 3] 3
```

## A slice is a header

The header is a pointer, a length, and a capacity. `append` may allocate a
new array, so always keep its result: `s = append(s, x)`. Slicing shares
the array the header points at.

```go file=n02.go
package main

import "fmt"

func main() {
	s := []int{1, 2, 3}
	s = append(s, 4, 5)
	fmt.Println(s, len(s), s[1:3], s[:2], s[3:])
}
```

```text output
[1 2 3 4 5] 5 [2 3] [1 2] [4 5]
```

## `append` within capacity shares the array

Both results point at `base`'s array, so the second `append` overwrites the
element the first one just wrote. Do not keep using a slice after another
`append` into the same spare capacity.

```go file=n03.go
package main

import "fmt"

func main() {
	base := make([]int, 3, 10)
	t := append(base, 1)
	u := append(base, 2)
	fmt.Println(t, u, len(base), cap(base))
}
```

```text output
[0 0 0 2] [0 0 0 2] 3 10
```

## A full slice expression forces a copy

`base[:3:3]` sets length and capacity to 3. The next `append` no longer
fits, so it allocates. The `2` written past `len(base)` stays in the old
array.

```go file=n04.go
package main

import "fmt"

func main() {
	base := make([]int, 3, 10)
	_ = append(base, 2)
	w := base[:3:3]
	w = append(w, 7)
	fmt.Println(base[:4], w)
}
```

```text output
[0 0 0 2] [0 0 0 7]
```

## `copy` and reslicing edit the elements

`copy` stops at the shorter length and returns how many elements moved.
Cutting out index 1 is `append(s[:1], s[2:]...)`, which slides the tail
down inside the same array.

```go file=n05.go
package main

import "fmt"

func main() {
	s := []int{1, 2, 3, 4, 5}
	dst := make([]int, 2)
	n := copy(dst, s)
	fmt.Println(n, dst)
	s = append(s[:1], s[2:]...)
	fmt.Println(s)
}
```

```text output
2 [1 2]
[1 3 4 5]
```

## A sub-slice keeps the whole array alive

`sub` and `base` share storage, so a write through the small slice changes
the large one. `slices.Clone` copies the piece you want to keep and lets
the rest of a huge array be collected.

```go file=n06.go
package main

import (
	"fmt"
	"slices"
)

func main() {
	base := []int{1, 2, 3, 4}
	sub := base[:2]
	sub[0] = 9
	fmt.Println(base)
	kept := slices.Clone(base[2:])
	kept[0] = 0
	fmt.Println(base, kept)
}
```

```text output
[9 2 3 4]
[9 2 3 4] [0 4]
```

## The slices package sorts and searches

`Sort` orders the slice in place. `BinarySearch` needs that order and
reports the index and whether the value was present.

```go file=n07.go
package main

import (
	"fmt"
	"slices"
)

func main() {
	nums := []int{5, 2, 8, 1}
	slices.Sort(nums)
	fmt.Println(nums, slices.Contains(nums, 8), slices.Index(nums, 5))
	idx, found := slices.BinarySearch(nums, 5)
	fmt.Println(idx, found, slices.Max(nums))
}
```

```text output
[1 2 5 8] true 2
2 true 8
```

## A nil slice is not an empty slice

Both have length zero. Only the nil slice compares equal to `nil`. Slices
cannot be compared with `==` otherwise, and they cannot be map keys.
Arrays can.

```go file=n08.go
package main

import "fmt"

func main() {
	var ns []int
	es := []int{}
	fmt.Println(ns == nil, es == nil, len(ns), len(es))
	fmt.Println([2]int{1, 2} == [2]int{1, 2})
}
```

```text output
true false 0 0
true
```

## Comma-ok tells a missing key from a zero

Reading a missing key returns the zero value. The second result is false
when the key was absent. `delete` of a missing key does nothing.

```go file=n09.go
package main

import "fmt"

func main() {
	ages := map[string]int{"ann": 31, "bob": 25}
	ages["cy"] = 40
	v, ok := ages["dan"]
	fmt.Println(v, ok, len(ages))
	delete(ages, "bob")
	delete(ages, "nope")
	fmt.Println(len(ages), ages["ann"])
}
```

```text output
0 false 3
2 31
```

## `fmt` prints map keys in sorted order

Ranging a map yourself is random; printing the map is not. A missing key
reads as zero, which is why `counts[r]++` works on the first sight of a
letter.

```go file=n10.go
package main

import (
	"fmt"
	"maps"
	"slices"
)

func main() {
	ages := map[string]int{"ann": 31, "cy": 40}
	fmt.Println(slices.Sorted(maps.Keys(ages)))

	counts := map[rune]int{}
	for _, r := range "banana" {
		counts[r]++
	}
	fmt.Println(counts)
}
```

```text output
[ann cy]
map[97:3 98:1 110:2]
```

## Writing a nil map panics

A nil map can be read. The first write panics. `make` or a composite
literal allocates the table.

```go file=n11.go
package main

import "fmt"

func main() {
	defer func() { fmt.Println("recovered:", recover()) }()
	var m map[string]int
	m["a"] = 1
}
```

```text output
recovered: assignment to entry in nil map
```

## A set is a map to an empty struct

`struct{}` carries no data, so the map records presence only. The comma-ok
form answers membership.

```go file=n12.go
package main

import "fmt"

func main() {
	set := map[string]struct{}{}
	set["a"] = struct{}{}
	_, in := set["a"]
	fmt.Println(in, len(set))
}
```

```text output
true 1
```

## Make each row of a grid

A `[][]int` starts as nil rows. Allocate every row, or the first index
panics.

```go file=n13.go
package main

import "fmt"

func main() {
	grid := make([][]int, 2)
	for i := range grid {
		grid[i] = make([]int, 3)
	}
	grid[1][2] = 5
	fmt.Println(grid)
}
```

```text output
[[0 0 0] [0 0 5]]
```

## Sort structs with a comparison function

`SortFunc` asks for an `int`: negative when the first value belongs first.
`cmp.Or` tries the age comparison, then the name, and keeps the first
non-zero result. Ages here sort descending.

```go file=n14.go
package main

import (
	"cmp"
	"fmt"
	"slices"
)

type person struct {
	Name string
	Age  int
}

func main() {
	people := []person{{"Al", 30}, {"Bo", 25}, {"Cy", 30}}
	slices.SortFunc(people, func(x, y person) int {
		return cmp.Or(cmp.Compare(y.Age, x.Age), cmp.Compare(x.Name, y.Name))
	})
	fmt.Println(people)
}
```

```text output
[{Al 30} {Cy 30} {Bo 25}]
```

## Map values are not addressable

`m[k].N = 2` does not compile, because the map may move the entry. Copy
the struct out, change the copy, and store it back. Storing pointers is
the other fix.

```go file=n15.go
package main

import "fmt"

type pair struct{ N int }

func main() {
	m := map[string]pair{"a": {1}}
	p := m["a"]
	p.N = 2
	m["a"] = p
	fmt.Println(m["a"].N)
}
```

```text output
2
```

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
