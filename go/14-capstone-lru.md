# Go 14 — Capstone: an LRU Cache

A *least-recently-used* cache keeps the N most recently touched entries and
evicts the stalest. It pulls together generics, structs and methods, maps,
`container/list`, and zero-value/constructor design. (The same capstone is in
every language of this course; compare how the data structure changes.)

## Example

```go file=example.go
package main

import (
	"container/list"
	"fmt"
)

// LRU is a fixed-capacity cache. Not safe for concurrent use: wrap it
// with a sync.Mutex if goroutines share it.
type LRU[K comparable, V any] struct {
	cap   int
	order *list.List          // front = most recently used
	items map[K]*list.Element // key -> its node in order
}

type entry[K comparable, V any] struct {
	key K
	val V
}

func NewLRU[K comparable, V any](capacity int) *LRU[K, V] {
	if capacity <= 0 {
		panic("lru: capacity must be positive")
	}
	return &LRU[K, V]{
		cap:   capacity,
		order: list.New(),
		items: make(map[K]*list.Element, capacity),
	}
}

// Get returns the value and marks it as most recently used.
func (c *LRU[K, V]) Get(key K) (V, bool) {
	if el, ok := c.items[key]; ok {
		c.order.MoveToFront(el)
		return el.Value.(*entry[K, V]).val, true
	}
	var zero V
	return zero, false
}

// Put inserts or updates, evicting the least recently used when full.
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

// Keys lists keys from most to least recently used.
func (c *LRU[K, V]) Keys() []K {
	keys := make([]K, 0, c.order.Len())
	for el := c.order.Front(); el != nil; el = el.Next() {
		keys = append(keys, el.Value.(*entry[K, V]).key)
	}
	return keys
}

func (c *LRU[K, V]) Len() int { return c.order.Len() }

func main() {
	c := NewLRU[string, int](2)
	c.Put("a", 1)
	c.Put("b", 2)
	v, ok := c.Get("a") // a becomes the newest
	fmt.Println(v, ok)
	c.Put("c", 3) // evicts b
	v, ok = c.Get("b")
	fmt.Println(v, ok)
	fmt.Println(c.Keys(), c.Len())

	func() {
		defer func() { fmt.Println("recovered:", recover()) }()
		NewLRU[int, int](0)
	}()
}
```

```text output
1 true
0 false
[c a] 2
recovered: lru: capacity must be positive
```

## Details that bite

- `container/list` stores `any`, so every access needs a type assertion;
  that is the price of a non-generic standard list. A custom intrusive
  list of `*node[K, V]` is faster and type-safe.
- A map plus a linked list gives O(1) `Get` and `Put`. A slice scan would
  be O(n) per operation.
- The cache is *not* goroutine-safe: reads mutate recency, so even `Get`
  needs the write lock. A `sync.Mutex` (not `RWMutex`) is correct.
- Hold keys small and comparable; large struct keys are copied on every
  map operation.
- Panicking on invalid constructor arguments is reasonable for
  programmer errors; return an error if the value comes from user input.

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
