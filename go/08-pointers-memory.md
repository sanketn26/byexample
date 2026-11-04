# Go 08 — Pointers and Memory

Go has pointers but no pointer arithmetic, and a garbage collector. You
never `free` anything; escape analysis decides what lives on the stack or
the heap. Take a pointer to mutate a value, to share a large struct, to
represent "absent", or because the type holds a `sync.Mutex` (copying a
mutex is a bug, and `go vet` catches it). Slices and maps are already
headers, so pass those by value. You cannot take the address of a map
element, because the map may move it. Leaks come from live references:
a goroutine blocked forever, a global cache, a sub-slice of a huge array,
a timer you never stop. `defer`, closures, and interface conversions often
force a heap allocation; `go build -gcflags=-m` reports them.

## `*` reads and writes the pointee

`&x` is the address of `x`. `*p` is the value there. `pp` is a pointer to
that pointer. Nothing here prints an address, because addresses change
between runs.

```go file=n01.go
package main

import "fmt"

func main() {
	x := 10
	p := &x
	*p = 20
	fmt.Println(x, *p, p == &x)

	pp := &p
	**pp = 30
	fmt.Println(x)
}
```

```text output
20 20 true
30
```

## `new` returns a pointer to a zero value

`new(int)` allocates an `int` set to `0` and gives you its address. It does
not run a constructor.

```go file=n02.go
package main

import "fmt"

func main() {
	n := new(int)
	*n = 5
	fmt.Println(*n)
}
```

```text output
5
```

## Field selectors dereference for you

`n.Val` works when `n` is a `*Node`. You can also point at a field and
write through that pointer. A nil pointer has no fields: reading one
panics.

```go file=n03.go
package main

import "fmt"

type Node struct {
	Val  int
	Next *Node
}

func main() {
	list := &Node{1, &Node{2, &Node{3, nil}}}
	for n := list; n != nil; n = n.Next {
		fmt.Print(n.Val, " ")
	}
	fmt.Println()
	pn := &list.Next.Val
	*pn = 20
	fmt.Println(list.Next.Val)
}
```

```text output
1 2 3 
20
```

## The callee receives a copy

`incVal` increments its own `n`. `incPtr` increments the caller's variable.
That is the whole difference between a value parameter and a pointer
parameter.

```go file=n04.go
package main

import "fmt"

func incVal(n int)  { n++ }
func incPtr(n *int) { *n++ }

func main() {
	v := 10
	incVal(v)
	incPtr(&v)
	fmt.Println(v)
}
```

```text output
11
```

## The slice header is copied; the array may be shared

`append` that does not fit allocates, so the write `s[0] = -1` lands on
the new array and the caller still sees `[0]`. When the value fits in the
capacity, both headers share the array and the caller sees the write.

```go file=n05.go
package main

import "fmt"

func appendInside(s []int) {
	s = append(s, 99)
	s[0] = -1
}

func main() {
	s := make([]int, 1, 1)
	appendInside(s)
	fmt.Println(s)
	s2 := make([]int, 1, 2)
	appendInside(s2)
	fmt.Println(s2, s2[:2])
}
```

```text output
[0]
[-1] [-1 99]
```

## Returning a local's address is safe

The variable escapes to the heap. The caller may use the pointer after the
function has returned.

```go file=n06.go
package main

import "fmt"

func newCounter() *int {
	c := 0
	return &c
}

func main() {
	c := newCounter()
	*c += 2
	fmt.Println(*c)
}
```

```text output
2
```

## Each iteration has its own loop variable

Since Go 1.22, `&i` inside the loop is a different address every time.
Before that, every pointer aliased one variable and all of them saw the
final value. The `go` line in `go.mod` chooses.

```go file=n07.go
package main

import "fmt"

func main() {
	var ptrs []*int
	for i := 0; i < 3; i++ {
		ptrs = append(ptrs, &i)
	}
	for _, q := range ptrs {
		fmt.Print(*q, " ")
	}
	fmt.Println()
}
```

```text output
0 1 2 
```

## A nil pointer dereference panics

The panic is recoverable and is still a bug. The message names the nil
pointer. Do not use a recovered panic as ordinary control flow.

```go file=n08.go
package main

import "fmt"

type Node struct {
	Val  int
	Next *Node
}

func main() {
	defer func() { fmt.Println("recovered:", recover()) }()
	var np *Node
	fmt.Println(np.Val)
}
```

```text output
recovered: runtime error: invalid memory address or nil pointer dereference
```

## Field order changes size and padding

The compiler inserts padding so `int64` stays aligned. Putting the wide
field first makes a smaller struct. `unsafe.Sizeof` reports the size; it
is not a tool for application code.

```go file=n09.go
package main

import (
	"fmt"
	"unsafe"
)

func main() {
	type padded struct {
		a bool
		b int64
		c bool
	}
	type packed struct {
		b int64
		a bool
		c bool
	}
	fmt.Println(unsafe.Sizeof(padded{}), unsafe.Sizeof(packed{}))
}
```

```text output
24 16
```

## A mutex is not copied

`sync.Mutex` must not be copied after its first use. `go vet` reports
that copy. A method that locks the mutex takes a pointer receiver, and
callers pass a pointer, so the lock and the counter stay one value.

```go file=n10.go
package main

import (
	"fmt"
	"sync"
)

type counter struct {
	mu sync.Mutex
	n  int
}

func (c *counter) inc() {
	c.mu.Lock()
	c.n++
	c.mu.Unlock()
}

func main() {
	var c counter
	c.inc()
	c.inc()
	fmt.Println(c.n)
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

// Swap exchanges the values pointed to by a and b.
func Swap(a, b *int) {
	// TODO
}

type Node struct {
	Val  int
	Next *Node
}

// Reverse reverses a singly linked list in place and returns the new head.
func Reverse(head *Node) *Node {
	return head // TODO
}

// ToSlice collects the values of a list.
func ToSlice(head *Node) []int {
	return nil // TODO
}

type Tree struct {
	Val         int
	Left, Right *Tree
}

// Insert adds v into a binary search tree (ignoring duplicates)
// and returns the root. Insert(nil, v) creates a tree.
func Insert(root *Tree, v int) *Tree {
	return root // TODO
}

// InOrder returns the values in ascending order.
func InOrder(root *Tree) []int {
	return nil // TODO
}

type Config struct {
	Name string
	Tags []string
	Next *Config
}

// Clone deep-copies c, including Tags and the Next chain. nil -> nil.
func Clone(c *Config) *Config {
	return c // TODO
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
	a, b := 1, 2
	Swap(&a, &b)
	check("swap", []int{a, b}, []int{2, 1})

	l := &Node{1, &Node{2, &Node{3, nil}}}
	check("reverse", ToSlice(Reverse(l)), []int{3, 2, 1})
	check("reverse nil", Reverse(nil) == nil, true)

	var root *Tree
	for _, v := range []int{5, 2, 8, 1, 9, 2, 7} {
		root = Insert(root, v)
	}
	check("inorder", InOrder(root), []int{1, 2, 5, 7, 8, 9})

	orig := &Config{"a", []string{"x"}, &Config{Name: "b"}}
	cp := Clone(orig)
	cp.Tags[0] = "changed"
	cp.Next.Name = "changed"
	check("clone original untouched", []any{orig.Tags[0], orig.Next.Name}, []any{"x", "b"})
	check("clone nil", Clone(nil) == nil, true)
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

func Swap(a, b *int) {
	*a, *b = *b, *a
}

type Node struct {
	Val  int
	Next *Node
}

func Reverse(head *Node) *Node {
	var prev *Node
	for head != nil {
		head.Next, prev, head = prev, head, head.Next
	}
	return prev
}

func ToSlice(head *Node) []int {
	var out []int
	for n := head; n != nil; n = n.Next {
		out = append(out, n.Val)
	}
	return out
}

type Tree struct {
	Val         int
	Left, Right *Tree
}

func Insert(root *Tree, v int) *Tree {
	if root == nil {
		return &Tree{Val: v}
	}
	switch {
	case v < root.Val:
		root.Left = Insert(root.Left, v)
	case v > root.Val:
		root.Right = Insert(root.Right, v)
	}
	return root
}

func InOrder(root *Tree) []int {
	if root == nil {
		return nil
	}
	out := InOrder(root.Left)
	out = append(out, root.Val)
	return append(out, InOrder(root.Right)...)
}

type Config struct {
	Name string
	Tags []string
	Next *Config
}

func Clone(c *Config) *Config {
	if c == nil {
		return nil
	}
	cp := *c
	cp.Tags = append([]string(nil), c.Tags...)
	cp.Next = Clone(c.Next)
	return &cp
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
	a, b := 1, 2
	Swap(&a, &b)
	check("swap", []int{a, b}, []int{2, 1})

	l := &Node{1, &Node{2, &Node{3, nil}}}
	check("reverse", ToSlice(Reverse(l)), []int{3, 2, 1})
	check("reverse nil", Reverse(nil) == nil, true)

	var root *Tree
	for _, v := range []int{5, 2, 8, 1, 9, 2, 7} {
		root = Insert(root, v)
	}
	check("inorder", InOrder(root), []int{1, 2, 5, 7, 8, 9})

	orig := &Config{"a", []string{"x"}, &Config{Name: "b"}}
	cp := Clone(orig)
	cp.Tags[0] = "changed"
	cp.Next.Name = "changed"
	check("clone original untouched", []any{orig.Tags[0], orig.Next.Name}, []any{"x", "b"})
	check("clone nil", Clone(nil) == nil, true)
	if failed {
		os.Exit(1)
	}
}
```

</details>

Next: [09 — Interfaces](09-interfaces.md)
