# Go 17 — Advanced concurrency

A goroutine per request, with nothing to stop it and nowhere for work to
queue, fails by exhausting memory or file descriptors. Bound how many
workers run, and bound how many jobs sit in the queue. A deadline has to
cover the whole operation: a 150ms read timeout inside a transfer that
retries forever is not one. Cancellation is cooperative. Cancelling a
context does nothing to a worker blocked in a syscall until that syscall
is also interruptible: close the connection, or give the read its own
deadline. Join the workers before the process exits. An async runtime puts
a scheduler under this shape; it does not remove the bound, the deadline,
or the shutdown.

## Bound the workers and watch the high-water mark

Two workers pull from one queue. The gate holds the first wave inside the
job until that many have entered, so the high-water mark does not depend
on the scheduler. `max` is the number you have to be able to explain. A
blocking send hides a full queue on a goroutine you may not be able to
spare; the next nugget refuses instead.

```go file=n01.go
package main

import (
	"fmt"
	"sync"
	"sync/atomic"
)

func main() {
	jobs := []int{0, 1, 2, 3}
	type item struct{ i, job int }
	q := make(chan item)
	results := make([]int, len(jobs))
	var mu sync.Mutex
	cur, maxIn := 0, 0
	var arrived sync.WaitGroup
	arrived.Add(2)
	var seen atomic.Int32
	gate := make(chan struct{})
	var wg sync.WaitGroup
	for range 2 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for it := range q {
				mu.Lock()
				cur++
				if cur > maxIn {
					maxIn = cur
				}
				mu.Unlock()
				if seen.Add(1) <= 2 {
					arrived.Done()
				}
				<-gate
				results[it.i] = it.job * it.job
				mu.Lock()
				cur--
				mu.Unlock()
			}
		}()
	}
	go func() {
		for i, job := range jobs {
			q <- item{i, job}
		}
		close(q)
	}()
	arrived.Wait()
	close(gate)
	wg.Wait()
	fmt.Println("pool", results, maxIn)
}
```

```text output
pool [0 1 4 9] 2
```

## A deadline covers the whole wait

`WithTimeout` ends the `select` even though `never` has no sender. The
error is the deadline, not a value. `context`, a receive timeout, and
`poll` are the same idea: one clock for the operation.

```go file=n02.go
package main

import (
	"context"
	"fmt"
	"time"
)

func main() {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Millisecond)
	defer cancel()
	never := make(chan struct{})
	select {
	case <-ctx.Done():
		fmt.Println("deadline")
	case <-never:
		fmt.Println("unexpected")
	}
}
```

```text output
deadline
```

## A full buffer is backpressure

The channel holds two ints. The `default` arm runs when the third send
would block, and the producer learns immediately. A blocking send would
hide that fact. The same choice is `try_send` or a ring that refuses the
next push.

```go file=n03.go
package main

import "fmt"

func main() {
	buf := make(chan int, 2)
	accepted := 0
	for i := 0; i < 5; i++ {
		select {
		case buf <- i:
			accepted++
		default:
		}
	}
	fmt.Println("accepted", accepted)
}
```

```text output
accepted 2
```

## Shutdown leaves the queued jobs in place

The workers are alive, blocked on the context. Cancel tells them to stop.
They exit without taking the four queued values, and `stopped 4` is the
caller deciding whether to drop or drain. Join them before `main` returns.

```go file=n04.go
package main

import (
	"context"
	"fmt"
	"sync"
)

func main() {
	work := make(chan int, 4)
	for i := 0; i < 4; i++ {
		work <- i
	}
	stop, cancel := context.WithCancel(context.Background())
	var started sync.WaitGroup
	started.Add(2)
	var wg sync.WaitGroup
	for range 2 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			started.Done()
			<-stop.Done()
		}()
	}
	started.Wait()
	cancel()
	wg.Wait()
	fmt.Println("stopped", len(work))
}
```

```text output
stopped 4
```

## Exercises

`MapPool` runs `fn` on each job with at most `workers` goroutines and reports the high-water mark. `Until` returns `deadline` when `ctx` fires before any value arrives. `TryPut` reports how many of `n` items fit in a channel of size `limit` without blocking.

```go file=exercise.go
package main

import (
	"context"
	"fmt"
	"os"
	"sync"
	"sync/atomic"
	"time"
)

func MapPool(workers int, jobs []int, fn func(int) int) ([]int, int) {
	return nil, 0
}

func Until(ctx context.Context) string {
	return ""
}

func TryPut(limit, n int) int {
	return 0
}


var failed bool

func check(label string, got, want any) {
	if fmt.Sprint(got) == fmt.Sprint(want) {
		fmt.Println("PASS", label)
		return
	}
	failed = true
	fmt.Printf("FAIL %s: got %v, want %v\n", label, got, want)
}

func main() {
	var cur atomic.Int32
	var maxSeen atomic.Int32
	release := make(chan struct{})
	var once sync.Once
	fn := func(i int) int {
		c := cur.Add(1)
		for {
			m := maxSeen.Load()
			if c <= m || maxSeen.CompareAndSwap(m, c) {
				break
			}
		}
		if c >= 2 {
			once.Do(func() { close(release) })
		}
		select {
		case <-release:
		case <-time.After(time.Second):
		}
		cur.Add(-1)
		return i * i
	}
	results, maxIn := MapPool(2, []int{0, 1, 2, 3}, fn)
	check("pool", []any{results, maxIn, int(maxSeen.Load())}, []any{[]int{0, 1, 4, 9}, 2, int32(2)})

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Millisecond)
	defer cancel()
	check("deadline", Until(ctx), "deadline")
	check("accepted", TryPut(2, 5), 2)
	if failed {
		os.Exit(1)
	}
}
```

<details><summary>Solution</summary>

```go file=solution.go
package main

import (
	"context"
	"fmt"
	"os"
	"sync"
	"sync/atomic"
	"time"
)

func MapPool(workers int, jobs []int, fn func(int) int) ([]int, int) {
	type item struct{ i, job int }
	q := make(chan item)
	results := make([]int, len(jobs))
	var mu sync.Mutex
	cur, maxIn := 0, 0
	var wg sync.WaitGroup
	wg.Add(workers)
	for range workers {
		go func() {
			defer wg.Done()
			for it := range q {
				mu.Lock()
				cur++
				if cur > maxIn {
					maxIn = cur
				}
				mu.Unlock()
				results[it.i] = fn(it.job)
				mu.Lock()
				cur--
				mu.Unlock()
			}
		}()
	}
	for i, job := range jobs {
		q <- item{i, job}
	}
	close(q)
	wg.Wait()
	return results, maxIn
}

func Until(ctx context.Context) string {
	never := make(chan struct{})
	select {
	case <-ctx.Done():
		return "deadline"
	case <-never:
		return "ok"
	}
}

func TryPut(limit, n int) int {
	buf := make(chan int, limit)
	accepted := 0
	for i := 0; i < n; i++ {
		select {
		case buf <- i:
			accepted++
		default:
			return accepted
		}
	}
	return accepted
}

var failed bool

func check(label string, got, want any) {
	if fmt.Sprint(got) == fmt.Sprint(want) {
		fmt.Println("PASS", label)
		return
	}
	failed = true
	fmt.Printf("FAIL %s: got %v, want %v\n", label, got, want)
}

func main() {
	var cur atomic.Int32
	var maxSeen atomic.Int32
	release := make(chan struct{})
	var once sync.Once
	fn := func(i int) int {
		c := cur.Add(1)
		for {
			m := maxSeen.Load()
			if c <= m || maxSeen.CompareAndSwap(m, c) {
				break
			}
		}
		if c >= 2 {
			once.Do(func() { close(release) })
		}
		select {
		case <-release:
		case <-time.After(time.Second):
		}
		cur.Add(-1)
		return i * i
	}
	results, maxIn := MapPool(2, []int{0, 1, 2, 3}, fn)
	check("pool", []any{results, maxIn, int(maxSeen.Load())}, []any{[]int{0, 1, 4, 9}, 2, int32(2)})

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Millisecond)
	defer cancel()
	check("deadline", Until(ctx), "deadline")
	check("accepted", TryPut(2, 5), 2)
	if failed {
		os.Exit(1)
	}
}
```

</details>

Back to the [course index](README.md)
