# Go 08 — Pointers and Memory

Go has pointers but no pointer arithmetic, and a garbage collector. You never
`free` anything; escape analysis decides what lives on the stack or heap.

## Example

```go file=example.go
package main

import (
	"fmt"
	"unsafe"
)

type Node struct {
	Val  int
	Next *Node
}

func incVal(n int) { n++ }
func incPtr(n *int) { *n++ }

// A slice is a (pointer, len, cap) header passed by value.
func appendInside(s []int) {
	s = append(s, 99)
	s[0] = -1
}

// Returning the address of a local is fine: it escapes to the heap.
func newCounter() *int {
	c := 0
	return &c
}

func main() {
	x := 10
	p := &x // p is a *int holding x's address
	*p = 20
	fmt.Println(x, *p, p == &x)

	pp := &p
	**pp = 30
	fmt.Println(x)

	n := new(int) // allocates a zeroed int, returns *int
	*n = 5
	fmt.Println(*n)

	// Linked list; field access auto-dereferences
	list := &Node{1, &Node{2, &Node{3, nil}}}
	for n := list; n != nil; n = n.Next {
		fmt.Print(n.Val, " ")
	}
	fmt.Println()
	pn := &list.Next.Val // pointer to a field
	*pn = 20
	fmt.Println(list.Next.Val)

	// Value vs pointer parameters
	v := 10
	incVal(v)
	incPtr(&v)
	fmt.Println(v)

	// Slices: the header is copied, the backing array is shared
	s := make([]int, 1, 1)
	appendInside(s) // append reallocates, so s[0] = -1 hits the new array
	fmt.Println(s)
	s2 := make([]int, 1, 2)
	appendInside(s2) // fits in capacity: shared array is modified
	fmt.Println(s2, s2[:2])

	c := newCounter()
	*c += 2
	fmt.Println(*c)

	// Go 1.22+: each iteration of a for loop has its own variable
	var ptrs []*int
	for i := 0; i < 3; i++ {
		ptrs = append(ptrs, &i)
	}
	for _, q := range ptrs {
		fmt.Print(*q, " ")
	}
	fmt.Println()

	// nil pointer dereference panics, recoverable but usually a bug
	func() {
		defer func() { fmt.Println("recovered:", recover()) }()
		var np *Node
		fmt.Println(np.Val)
	}()

	// Layout and padding: field order changes the size
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
20 20 true
30
5
1 2 3 
20
11
[0]
[-1] [-1 99]
2
0 1 2 
recovered: runtime error: invalid memory address or nil pointer dereference
24 16
```

## Details that bite

- Pointers to `nil` maps/slices/interfaces are rarely what you want; slices
  and maps are already reference-like, so pass them by value.
- Use pointers for: mutation, large structs, optional values, and types
  containing a mutex (copying a `sync.Mutex` is a bug; `go vet` catches it).
- Taking the address of a map element (`&m[k]`) is illegal because the map
  may move entries.
- Memory leaks in Go come from *live references*: goroutines blocked
  forever, global caches, sub-slices of huge arrays, un-stopped timers.
- `defer`, closures and interface conversions often cause heap
  allocation. Inspect with `go build -gcflags=-m`.
- `unsafe` is outside the compatibility promise; keep it out of
  application code.

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
