# Go 11 — Concurrency

Goroutines are cheap, channels move data between them, and `sync` / `atomic`
protect shared state. Go's motto: *share memory by communicating*.

## Example

```go file=example.go
package main

import (
	"context"
	"fmt"
	"sort"
	"sync"
	"sync/atomic"
	"time"
)

func gen(nums ...int) <-chan int {
	out := make(chan int)
	go func() {
		defer close(out) // the sender closes
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
	// WaitGroup + writing to distinct slice indexes needs no lock
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

	// Unbuffered channel: send and receive rendezvous
	ch := make(chan string)
	go func() { ch <- "ping" }()
	fmt.Println(<-ch)

	// Buffered channel, close, range
	jobs := make(chan int, 3)
	for i := 1; i <= 3; i++ {
		jobs <- i
	}
	close(jobs)
	sum := 0
	for j := range jobs {
		sum += j
	}
	v, ok := <-jobs // receiving from a closed, drained channel
	fmt.Println(sum, v, ok)

	// Worker pool
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
	sort.Ints(got) // completion order is not deterministic
	fmt.Println(got)

	// Mutex-protected counter and an atomic one
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

	// select with a timeout
	quiet := make(chan int)
	select {
	case v := <-quiet:
		fmt.Println(v)
	case <-time.After(20 * time.Millisecond):
		fmt.Println("timeout")
	}

	// select with default: non-blocking receive
	select {
	case v := <-quiet:
		fmt.Println(v)
	default:
		fmt.Println("nothing ready")
	}

	// context cancellation
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

	// sync.Once
	var once sync.Once
	for i := 0; i < 3; i++ {
		once.Do(func() { fmt.Println("init once") })
	}

	// Pipeline
	for v := range square(gen(1, 2, 3)) {
		fmt.Print(v, " ")
	}
	fmt.Println()
}
```

```text output
[0 1 4 9 16]
ping
6 0 false
[10 20 30 40 50 60]
10000 10000
timeout
nothing ready
context canceled
context deadline exceeded
init once
1 4 9 
```

## Details that bite

- Run with `go run -race` / `go test -race`; the race detector finds
  unsynchronised access that tests may never trigger.
- Only the **sender** closes a channel. Sending on a closed channel
  panics; receiving from one returns zero values immediately.
- A nil channel blocks forever in `select` — handy for disabling a case.
- Goroutine leaks: a goroutine blocked on a channel nobody will ever use
  stays forever. Always give goroutines a way to stop (`context`, a done
  channel, closing the input).
- `wg.Add` must happen *before* the `go` statement, never inside the
  goroutine.
- `main` returning ends the program even if goroutines are running.
- All goroutines asleep at once is `fatal error: all goroutines are
  asleep - deadlock!`.
- Prefer a mutex for protecting state and channels for passing ownership
  or signalling; mixing them up leads to over-complicated designs.

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
