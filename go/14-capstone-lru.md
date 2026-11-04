# Go 14 — Capstone: an LRU Cache

A least-recently-used cache keeps the N most recently touched entries and
evicts the stalest. A map finds the node in O(1). A linked list orders it,
front meaning most recent. A slice scan would be O(n) per call.
`container/list` stores `any`, so every access type-asserts; that is the
price of a non-generic standard list. A custom list of `*node[K, V]` is
faster and avoids the assertion. Keys should be small and comparable:
a large struct key is copied on every map operation. The cache is not
goroutine-safe. `Get` mutates recency, so even a read needs the write
lock. Use `sync.Mutex`, not `RWMutex`.

## The cache is a map plus a list

`Put` of a new key pushes a node to the front and records it in the map.
`Keys` walks from the front, so the newest key is first. Capacity here is
3, so nothing is evicted yet.

```go file=n01.go
package main

import (
	"container/list"
	"fmt"
)

type LRU[K comparable, V any] struct {
	cap   int
	order *list.List
	items map[K]*list.Element
}

type entry[K comparable, V any] struct {
	key K
	val V
}

func NewLRU[K comparable, V any](capacity int) *LRU[K, V] {
	return &LRU[K, V]{
		cap:   capacity,
		order: list.New(),
		items: make(map[K]*list.Element, capacity),
	}
}

func (c *LRU[K, V]) Put(key K, val V) {
	c.items[key] = c.order.PushFront(&entry[K, V]{key, val})
}

func (c *LRU[K, V]) Keys() []K {
	keys := make([]K, 0, c.order.Len())
	for el := c.order.Front(); el != nil; el = el.Next() {
		keys = append(keys, el.Value.(*entry[K, V]).key)
	}
	return keys
}

func main() {
	c := NewLRU[string, int](3)
	c.Put("a", 1)
	c.Put("b", 2)
	fmt.Println(c.Keys(), c.order.Len())
}
```

```text output
[b a] 2
```

## `Get` moves the hit to the front

A hit type-asserts the node, moves it, and returns the value. A miss
returns the zero value and false, and does not change the order.

```go file=n02.go
package main

import (
	"container/list"
	"fmt"
)

type LRU[K comparable, V any] struct {
	order *list.List
	items map[K]*list.Element
}

type entry[K comparable, V any] struct {
	key K
	val V
}

func NewLRU[K comparable, V any]() *LRU[K, V] {
	return &LRU[K, V]{order: list.New(), items: map[K]*list.Element{}}
}

func (c *LRU[K, V]) Put(key K, val V) {
	c.items[key] = c.order.PushFront(&entry[K, V]{key, val})
}

func (c *LRU[K, V]) Get(key K) (V, bool) {
	if el, ok := c.items[key]; ok {
		c.order.MoveToFront(el)
		return el.Value.(*entry[K, V]).val, true
	}
	var zero V
	return zero, false
}

func (c *LRU[K, V]) Keys() []K {
	var keys []K
	for el := c.order.Front(); el != nil; el = el.Next() {
		keys = append(keys, el.Value.(*entry[K, V]).key)
	}
	return keys
}

func main() {
	c := NewLRU[string, int]()
	c.Put("a", 1)
	c.Put("b", 2)
	v, ok := c.Get("a")
	fmt.Println(v, ok, c.Keys())
	v, ok = c.Get("missing")
	fmt.Println(v, ok, c.Keys())
}
```

```text output
1 true [a b]
0 false [a b]
```

## `Put` of a new key evicts the back

When the list grows past capacity, the back node is the least recently
used. `Get("a")` moved `a` to the front, so `b` is the one removed when
`c` arrives.

```go file=n03.go
package main

import (
	"container/list"
	"fmt"
)

type LRU[K comparable, V any] struct {
	cap   int
	order *list.List
	items map[K]*list.Element
}

type entry[K comparable, V any] struct {
	key K
	val V
}

func NewLRU[K comparable, V any](capacity int) *LRU[K, V] {
	return &LRU[K, V]{cap: capacity, order: list.New(), items: map[K]*list.Element{}}
}

func (c *LRU[K, V]) Get(key K) (V, bool) {
	if el, ok := c.items[key]; ok {
		c.order.MoveToFront(el)
		return el.Value.(*entry[K, V]).val, true
	}
	var zero V
	return zero, false
}

func (c *LRU[K, V]) Put(key K, val V) {
	if el, ok := c.items[key]; ok {
		el.Value.(*entry[K, V]).val = val
		c.order.MoveToFront(el)
		return
	}
	c.items[key] = c.order.PushFront(&entry[K, V]{key, val})
	if c.order.Len() > c.cap {
		oldest := c.order.Back()
		c.order.Remove(oldest)
		delete(c.items, oldest.Value.(*entry[K, V]).key)
	}
}

func (c *LRU[K, V]) Keys() []K {
	var keys []K
	for el := c.order.Front(); el != nil; el = el.Next() {
		keys = append(keys, el.Value.(*entry[K, V]).key)
	}
	return keys
}

func main() {
	c := NewLRU[string, int](2)
	c.Put("a", 1)
	c.Put("b", 2)
	c.Get("a")
	c.Put("c", 3)
	v, ok := c.Get("b")
	fmt.Println(v, ok)
	fmt.Println(c.Keys(), c.order.Len())
}
```

```text output
0 false
[c a] 2
```

## Updating a key does not grow the cache

`Put` of a key that is already present overwrites the value and moves that
node to the front. Length stays at capacity.

```go file=n04.go
package main

import (
	"container/list"
	"fmt"
)

type LRU[K comparable, V any] struct {
	cap   int
	order *list.List
	items map[K]*list.Element
}

type entry[K comparable, V any] struct {
	key K
	val V
}

func NewLRU[K comparable, V any](capacity int) *LRU[K, V] {
	return &LRU[K, V]{cap: capacity, order: list.New(), items: map[K]*list.Element{}}
}

func (c *LRU[K, V]) Get(key K) (V, bool) {
	el, ok := c.items[key]
	if !ok {
		var zero V
		return zero, false
	}
	c.order.MoveToFront(el)
	return el.Value.(*entry[K, V]).val, true
}

func (c *LRU[K, V]) Put(key K, val V) {
	if el, ok := c.items[key]; ok {
		el.Value.(*entry[K, V]).val = val
		c.order.MoveToFront(el)
		return
	}
	c.items[key] = c.order.PushFront(&entry[K, V]{key, val})
	if c.order.Len() > c.cap {
		oldest := c.order.Back()
		c.order.Remove(oldest)
		delete(c.items, oldest.Value.(*entry[K, V]).key)
	}
}

func (c *LRU[K, V]) Keys() []K {
	var keys []K
	for el := c.order.Front(); el != nil; el = el.Next() {
		keys = append(keys, el.Value.(*entry[K, V]).key)
	}
	return keys
}

func main() {
	c := NewLRU[string, int](2)
	c.Put("a", 1)
	c.Put("b", 2)
	c.Put("a", 9)
	v, ok := c.Get("a")
	fmt.Println(v, ok, c.Keys(), c.order.Len())
}
```

```text output
9 true [a b] 2
```

## A bad capacity is a programmer error

`NewLRU(0)` panics. That is reasonable when the caller is another piece of
the program. If the number comes from user input, return an error instead
of panicking.

```go file=n05.go
package main

import "fmt"

func NewLRU[K comparable, V any](capacity int) {
	if capacity <= 0 {
		panic("lru: capacity must be positive")
	}
}

func main() {
	defer func() { fmt.Println("recovered:", recover()) }()
	NewLRU[int, int](0)
}
```

```text output
recovered: lru: capacity must be positive
```

## Exercises

Implement a **list-backed** version with the same `Get`/`Put`/`Keys`, plus
`Peek`, `Remove` and hit/miss statistics.

```go file=exercise.go
package main

import (
	"fmt"
	"os"
	"reflect"
)

// SimpleLRU stores items in a slice, newest first. O(n) per operation is
// fine here.
type SimpleLRU struct {
	// TODO: fields
}

func NewSimpleLRU(capacity int) *SimpleLRU { return &SimpleLRU{} }

// Get returns the value and marks it as most recently used (counts a hit
// or a miss).
func (c *SimpleLRU) Get(key string) (int, bool) { return 0, false }

// Put inserts or updates and marks the key most recently used, evicting the
// oldest when over capacity.
func (c *SimpleLRU) Put(key string, v int) {}

// Peek returns the value without changing recency or statistics.
func (c *SimpleLRU) Peek(key string) (int, bool) { return 0, false }

// Remove deletes key and reports whether it was present.
func (c *SimpleLRU) Remove(key string) bool { return true }

// Stats returns hits and misses counted by Get.
func (c *SimpleLRU) Stats() (hits, misses int) { return -1, -1 }

// Keys lists keys from most to least recently used.
func (c *SimpleLRU) Keys() []string { return nil }

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
	c := NewSimpleLRU(2)
	c.Put("a", 1)
	c.Put("b", 2)
	v, ok := c.Get("a")
	check("get", []any{v, ok}, []any{1, true})
	c.Put("c", 3)
	_, ok = c.Get("b")
	check("evicted", ok, false)
	check("keys", c.Keys(), []string{"c", "a"})
	v, ok = c.Peek("a")
	check("peek", []any{v, ok}, []any{1, true})
	check("peek keeps order", c.Keys(), []string{"c", "a"})
	h, m := c.Stats()
	check("stats", []int{h, m}, []int{1, 1})
	c.Put("a", 10)
	v, _ = c.Get("a")
	check("update", []any{v, c.Keys()}, []any{10, []string{"a", "c"}})
	check("remove", []any{c.Remove("c"), c.Remove("zzz"), c.Keys()},
		[]any{true, false, []string{"a"}})
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
	"slices"
)

type item struct {
	key string
	val int
}

type SimpleLRU struct {
	cap    int
	items  []item // newest first
	hits   int
	misses int
}

func NewSimpleLRU(capacity int) *SimpleLRU {
	if capacity <= 0 {
		panic("capacity must be positive")
	}
	return &SimpleLRU{cap: capacity}
}

func (c *SimpleLRU) index(key string) int {
	return slices.IndexFunc(c.items, func(it item) bool { return it.key == key })
}

func (c *SimpleLRU) Get(key string) (int, bool) {
	i := c.index(key)
	if i < 0 {
		c.misses++
		return 0, false
	}
	c.hits++
	it := c.items[i]
	c.items = slices.Delete(c.items, i, i+1)
	c.items = slices.Insert(c.items, 0, it)
	return it.val, true
}

func (c *SimpleLRU) Put(key string, v int) {
	if i := c.index(key); i >= 0 {
		c.items = slices.Delete(c.items, i, i+1)
	}
	c.items = slices.Insert(c.items, 0, item{key, v})
	if len(c.items) > c.cap {
		c.items = c.items[:c.cap]
	}
}

func (c *SimpleLRU) Peek(key string) (int, bool) {
	if i := c.index(key); i >= 0 {
		return c.items[i].val, true
	}
	return 0, false
}

func (c *SimpleLRU) Remove(key string) bool {
	i := c.index(key)
	if i < 0 {
		return false
	}
	c.items = slices.Delete(c.items, i, i+1)
	return true
}

func (c *SimpleLRU) Stats() (hits, misses int) { return c.hits, c.misses }

func (c *SimpleLRU) Keys() []string {
	keys := make([]string, len(c.items))
	for i, it := range c.items {
		keys[i] = it.key
	}
	return keys
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
	c := NewSimpleLRU(2)
	c.Put("a", 1)
	c.Put("b", 2)
	v, ok := c.Get("a")
	check("get", []any{v, ok}, []any{1, true})
	c.Put("c", 3)
	_, ok = c.Get("b")
	check("evicted", ok, false)
	check("keys", c.Keys(), []string{"c", "a"})
	v, ok = c.Peek("a")
	check("peek", []any{v, ok}, []any{1, true})
	check("peek keeps order", c.Keys(), []string{"c", "a"})
	h, m := c.Stats()
	check("stats", []int{h, m}, []int{1, 1})
	c.Put("a", 10)
	v, _ = c.Get("a")
	check("update", []any{v, c.Keys()}, []any{10, []string{"a", "c"}})
	check("remove", []any{c.Remove("c"), c.Remove("zzz"), c.Keys()},
		[]any{true, false, []string{"a"}})
	if failed {
		os.Exit(1)
	}
}
```

</details>

Next: [15 — Streaming](15-streaming.md)
