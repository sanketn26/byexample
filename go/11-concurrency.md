# Go 11 — Concurrency

Goroutines are cheap, channels move data between them, and `sync` or
`atomic` protects shared state. Share memory by communicating. Run
`go test -race` (or `go run -race`); the race detector finds unsynchronised
access that a lucky schedule hides. `main` returning ends the process even
if other goroutines are still running. If every goroutine is blocked, the
runtime aborts with `fatal error: all goroutines are asleep - deadlock!`.

## `WaitGroup` waits, and the index needs no lock

`Add` happens before `go`, never inside the goroutine. Each iteration owns
its `i` (Go 1.22), and each goroutine writes a different index, so no mutex
is required. A goroutine blocked on a channel nobody uses leaks; give it a
`context`, a done channel, or a closed input.

```go file=n01.go
package main

import (
	"fmt"
	"sync"
)

func main() {
	var wg sync.WaitGroup
	results := make([]int, 5)
	for i := range 5 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			results[i] = i * i
		}()
	}
	wg.Wait()
	fmt.Println(results)
}
```

```text output
[0 1 4 9 16]
```

## An unbuffered send waits for a receiver

The send and the receive meet. Nobody proceeds until the other side is
there. Buffer the channel when the sender should not wait.

```go file=n02.go
package main

import "fmt"

func main() {
	ch := make(chan string)
	go func() { ch <- "ping" }()
	fmt.Println(<-ch)
}
```

```text output
ping
```

## Only the sender closes a channel

`range` stops at the close. A receive on a closed, empty channel returns
the zero value and `false` immediately. Sending on a closed channel
panics. Receiving from a closed one does not.

```go file=n03.go
package main

import "fmt"

func main() {
	jobs := make(chan int, 3)
	for i := 1; i <= 3; i++ {
		jobs <- i
	}
	close(jobs)
	sum := 0
	for j := range jobs {
		sum += j
	}
	v, ok := <-jobs
	fmt.Println(sum, v, ok)
}
```

```text output
6 0 false
```

## A pool of workers shares one jobs channel

Three goroutines range the input. A fourth closes the output after
`Wait`, which is safe only because the workers have finished sending.
Completion order is not deterministic, so sort before printing.

```go file=n04.go
package main

import (
	"fmt"
	"sort"
	"sync"
)

func main() {
	in := make(chan int)
	out := make(chan int)
	var pool sync.WaitGroup
	for w := 0; w < 3; w++ {
		pool.Add(1)
		go func() {
			defer pool.Done()
			for n := range in {
				out <- n * 10
			}
		}()
	}
	go func() {
		for i := 1; i <= 6; i++ {
			in <- i
		}
		close(in)
	}()
	go func() { pool.Wait(); close(out) }()
	var got []int
	for r := range out {
		got = append(got, r)
	}
	sort.Ints(got)
	fmt.Println(got)
}
```

```text output
[10 20 30 40 50 60]
```

## A mutex or an atomic guards a shared counter

Prefer a mutex when the state is a structure, and a channel when you are
handing off ownership or a signal. `atomic.Int64` is enough for this
counter. One hundred goroutines each add one hundred.

```go file=n05.go
package main

import (
	"fmt"
	"sync"
	"sync/atomic"
)

func main() {
	var mu sync.Mutex
	var atom atomic.Int64
	counter := 0
	var cw sync.WaitGroup
	for i := 0; i < 100; i++ {
		cw.Add(1)
		go func() {
			defer cw.Done()
			for k := 0; k < 100; k++ {
				mu.Lock()
				counter++
				mu.Unlock()
				atom.Add(1)
			}
		}()
	}
	cw.Wait()
	fmt.Println(counter, atom.Load())
}
```

```text output
10000 10000
```

## `select` waits for the first ready case

`time.After` fires when nothing arrives in time. A `default` arm makes the
same select non-blocking: it runs when no other case is ready.

```go file=n06.go
package main

import (
	"fmt"
	"time"
)

func main() {
	quiet := make(chan int)
	select {
	case v := <-quiet:
		fmt.Println(v)
	case <-time.After(20 * time.Millisecond):
		fmt.Println("timeout")
	}

	select {
	case v := <-quiet:
		fmt.Println(v)
	default:
		fmt.Println("nothing ready")
	}
}
```

```text output
timeout
nothing ready
```

## A nil channel case never fires

In a `select` with a `default`, the nil case is simply not chosen. Drop
the `default` and that receive blocks forever, which is how you disable a
case without removing it: assign the channel to nil.

```go file=n07.go
package main

import "fmt"

func main() {
	var ch chan int
	select {
	case v := <-ch:
		fmt.Println(v)
	default:
		fmt.Println("nothing ready")
	}
}
```

```text output
nothing ready
```

## `context` cancels and times out

`cancel` makes `ctx.Done()` ready and sets `context.Canceled`. A timeout
sets `context.DeadlineExceeded`. Pass the context down; do not store it in
a struct.

```go file=n08.go
package main

import (
	"context"
	"fmt"
	"time"
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan struct{})
	go func() {
		defer close(done)
		<-ctx.Done()
	}()
	cancel()
	<-done
	fmt.Println(ctx.Err())

	ctx2, cancel2 := context.WithTimeout(context.Background(), 20*time.Millisecond)
	defer cancel2()
	<-ctx2.Done()
	fmt.Println(ctx2.Err())
}
```

```text output
context canceled
context deadline exceeded
```

## `sync.Once` runs a function one time

The first `Do` calls it. Later `Do`s on the same `Once` return immediately,
even from other goroutines.

```go file=n09.go
package main

import (
	"fmt"
	"sync"
)

func main() {
	var once sync.Once
	for i := 0; i < 3; i++ {
		once.Do(func() { fmt.Println("init once") })
	}
}
```

```text output
init once
```

## A pipeline is a chain of channels

The sender closes. The next stage ranges until that close, then closes its
own output. `square(gen(...))` is both stages.

```go file=n10.go
package main

import "fmt"

func gen(nums ...int) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out)
		for _, n := range nums {
			out <- n
		}
	}()
	return out
}

func square(in <-chan int) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out)
		for n := range in {
			out <- n * n
		}
	}()
	return out
}

func main() {
	for v := range square(gen(1, 2, 3)) {
		fmt.Print(v, " ")
	}
	fmt.Println()
}
```

```text output
1 4 9 
```

## Exercises

```go file=exercise.go
package main

import (
	"fmt"
	"os"
	"reflect"
	"sync"
	"time"
)

// ParallelMap applies f to every element concurrently and returns the
// results in input order.
func ParallelMap(xs []int, f func(int) int) []int {
	return nil // TODO
}

// SafeCounter is safe for concurrent use. The zero value is ready.
type SafeCounter struct {
	mu sync.Mutex
	m  map[string]int
}

func (c *SafeCounter) Inc(key string)     {}
func (c *SafeCounter) Get(key string) int { return -1 }

// Pool runs f over jobs with exactly `workers` goroutines and returns
// results in input order.
func Pool(jobs []int, workers int, f func(int) int) []int {
	return nil // TODO
}

// First returns the result of whichever function finishes first.
// It must not leak goroutines blocked forever on send.
func First(fns ...func() string) string {
	return "" // TODO
}

// WithTimeout runs fn; if it takes longer than d, returns (0, false).
func WithTimeout(d time.Duration, fn func() int) (int, bool) {
	return 0, false // TODO
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
	check("parallelmap", ParallelMap([]int{1, 2, 3, 4}, func(n int) int { return n * n }), []int{1, 4, 9, 16})

	var c SafeCounter
	var wg sync.WaitGroup
	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func() { defer wg.Done(); c.Inc("k") }()
	}
	wg.Wait()
	check("safecounter", c.Get("k"), 50)

	check("pool", Pool([]int{1, 2, 3, 4, 5, 6}, 3, func(n int) int { return n + 100 }),
		[]int{101, 102, 103, 104, 105, 106})

	slow := func() string { time.Sleep(200 * time.Millisecond); return "slow" }
	fast := func() string { time.Sleep(5 * time.Millisecond); return "fast" }
	check("first", First(slow, fast), "fast")

	v, ok := WithTimeout(100*time.Millisecond, func() int { return 7 })
	check("timeout ok", []any{v, ok}, []any{7, true})
	_, ok = WithTimeout(10*time.Millisecond, func() int { time.Sleep(300 * time.Millisecond); return 1 })
	check("timeout hit", ok, false)
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
	"sync"
	"time"
)

func ParallelMap(xs []int, f func(int) int) []int {
	out := make([]int, len(xs))
	var wg sync.WaitGroup
	for i, x := range xs {
		wg.Add(1)
		go func() {
			defer wg.Done()
			out[i] = f(x)
		}()
	}
	wg.Wait()
	return out
}

type SafeCounter struct {
	mu sync.Mutex
	m  map[string]int
}

func (c *SafeCounter) Inc(key string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.m == nil {
		c.m = map[string]int{}
	}
	c.m[key]++
}

func (c *SafeCounter) Get(key string) int {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.m[key]
}

func Pool(jobs []int, workers int, f func(int) int) []int {
	out := make([]int, len(jobs))
	idx := make(chan int)
	var wg sync.WaitGroup
	for w := 0; w < workers; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for i := range idx {
				out[i] = f(jobs[i])
			}
		}()
	}
	for i := range jobs {
		idx <- i
	}
	close(idx)
	wg.Wait()
	return out
}

func First(fns ...func() string) string {
	res := make(chan string, len(fns)) // buffered: losers never block
	for _, fn := range fns {
		go func() { res <- fn() }()
	}
	return <-res
}

func WithTimeout(d time.Duration, fn func() int) (int, bool) {
	res := make(chan int, 1)
	go func() { res <- fn() }()
	select {
	case v := <-res:
		return v, true
	case <-time.After(d):
		return 0, false
	}
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
	check("parallelmap", ParallelMap([]int{1, 2, 3, 4}, func(n int) int { return n * n }), []int{1, 4, 9, 16})

	var c SafeCounter
	var wg sync.WaitGroup
	for i := 0; i < 50; i++ {
		wg.Add(1)
		go func() { defer wg.Done(); c.Inc("k") }()
	}
	wg.Wait()
	check("safecounter", c.Get("k"), 50)

	check("pool", Pool([]int{1, 2, 3, 4, 5, 6}, 3, func(n int) int { return n + 100 }),
		[]int{101, 102, 103, 104, 105, 106})

	slow := func() string { time.Sleep(200 * time.Millisecond); return "slow" }
	fast := func() string { time.Sleep(5 * time.Millisecond); return "fast" }
	check("first", First(slow, fast), "fast")

	v, ok := WithTimeout(100*time.Millisecond, func() int { return 7 })
	check("timeout ok", []any{v, ok}, []any{7, true})
	_, ok = WithTimeout(10*time.Millisecond, func() int { time.Sleep(300 * time.Millisecond); return 1 })
	check("timeout hit", ok, false)
	if failed {
		os.Exit(1)
	}
}
```

</details>

Next: [12 — Idiomatic Go](12-idiomatic-go.md)
