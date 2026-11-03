# Go 17 — Advanced concurrency

A goroutine per request, with nothing to stop it and nowhere for work to queue, fails by exhausting memory. Bound the workers, bound the queue, put a `context` deadline on the whole operation, and make shutdown visible. This is the shape of a server in front of the sockets from the previous lesson.

## Example

```go file=example.go
package main

import (
	"context"
	"fmt"
	"sync"
	"sync/atomic"
	"time"
)

func runPool(workers int, jobs []int) ([]int, int) {
	type item struct{ i, job int }
	q := make(chan item)
	results := make([]int, len(jobs))
	var mu sync.Mutex
	cur, maxIn := 0, 0
	need := workers
	if need > len(jobs) {
		need = len(jobs)
	}
	var arrived sync.WaitGroup
	arrived.Add(need)
	var seen atomic.Int32
	gate := make(chan struct{})
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
				if int(seen.Add(1)) <= need {
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
	return results, maxIn
}

func main() {
	results, maxIn := runPool(2, []int{0, 1, 2, 3})
	fmt.Println("pool", results, maxIn)

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Millisecond)
	defer cancel()
	never := make(chan struct{})
	select {
	case <-ctx.Done():
		fmt.Println("deadline")
	case <-never:
		fmt.Println("unexpected")
	}

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

	work := make(chan int, 4)
	for i := 0; i < 4; i++ {
		work <- i
	}
	stop, cancelStop := context.WithCancel(context.Background())
	var started sync.WaitGroup
	started.Add(2)
	var wg sync.WaitGroup
	wg.Add(2)
	for range 2 {
		go func() {
			defer wg.Done()
			started.Done()
			<-stop.Done()
		}()
	}
	started.Wait()
	cancelStop()
	wg.Wait()
	fmt.Println("stopped", len(work))
}
```

```text output
pool [0 1 4 9] 2
deadline
accepted 2
stopped 4
```

## Details that bite

- Bound two numbers: how many workers run, and how many jobs sit in the
  queue. One thread, goroutine or task per request, with no ceiling,
  dies by running out of memory or file descriptors.
- `max` in the pool output is the number you have to be able to explain.
  The example holds the first wave of workers inside the job until that
  many have entered, so the high-water mark is observable instead of
  depending on the scheduler.
- A full bounded channel (`put_nowait`, `select`/`default`, `try_send`,
  a ring that refuses the next push) is backpressure. The producer hears
  about it now. A blocking send hides the problem on a thread you may
  not be able to spare.
- A deadline covers the whole operation. A 150ms read timeout inside a
  transfer that retries forever is not one. `context`, `recv_timeout`
  and `poll` are the same idea.
- Cancellation is cooperative. Cancelling a context or setting a flag
  does nothing to a worker blocked in a syscall until that syscall is
  also interruptible: close the fd, or give the read its own deadline.
  The example's workers are alive, then told to stop, and the four
  queued jobs stay queued (`stopped 4`) for the caller to drop or drain.
- Join the workers before the process exits. Rust async runtimes add a
  scheduler under this shape; they do not remove the bound, the deadline
  or the shutdown.

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
