# Rust 11 — Concurrency

Ownership extends to threads. The compiler rejects a data race. `Send` and
`Sync` are the marker traits that say what may cross a thread; you mostly
see them in an error message. Rust does not prevent deadlocks or logic
races. `Rc` and `RefCell` are not `Send` or `Sync`. Use `Arc` and
`Mutex` or `RwLock`. These are OS threads. Many small I/O tasks want `async`
with an executor such as `tokio`. Data parallelism wants `rayon`.

## `spawn` returns the closure's value through `join`

`thread::spawn` requires a `'static` closure, so a borrowed local will not
compile. `move` the owned values in. `join` waits, and the `Result` is `Err`
if the thread panicked.

```rust file=n01.rs
use std::thread;

fn main() {
    let handles: Vec<_> = (0..4).map(|i| thread::spawn(move || i * 10)).collect();
    let results: Vec<i32> = handles.into_iter().map(|h| h.join().unwrap()).collect();
    println!("{results:?}");
}
```

```text output
[0, 10, 20, 30]
```

## `scope` may borrow locals

The threads in `thread::scope` finish before `scope` returns, so they may
borrow data on the stack. Each iteration hands out a disjoint `&mut`. The
second scope only reads `words`, which is a shared borrow.

```rust file=n02.rs
use std::thread;

fn main() {
    let mut data = vec![0usize; 5];
    thread::scope(|s| {
        for (i, slot) in data.iter_mut().enumerate() {
            s.spawn(move || {
                *slot = i * i;
            });
        }
    });
    println!("{data:?}");

    let words = vec!["a", "bb", "ccc"];
    let total = thread::scope(|s| {
        let h = s.spawn(|| words.iter().map(|w| w.len()).sum::<usize>());
        h.join().unwrap()
    });
    println!("{total}");
}
```

```text output
[0, 1, 4, 9, 16]
6
```

## A channel ends when every sender is dropped

`drop(tx)` matters. The original sender is still alive after the clones, and
`rx.iter()` waits until all of them are gone. Forgetting the drop hangs.
The receive order is not the send order. Sort when you need a stable line.
A `MutexGuard` unlocks when it goes out of scope. Do not hold it across a
blocking call.

```rust file=n03.rs
use std::sync::mpsc;
use std::thread;

fn main() {
    let (tx, rx) = mpsc::channel();
    for id in 0..3 {
        let tx = tx.clone();
        thread::spawn(move || {
            for j in 0..2 {
                tx.send(id * 10 + j).unwrap();
            }
        });
    }
    drop(tx);
    let mut got: Vec<i32> = rx.iter().collect();
    got.sort();
    println!("{got:?}");
}
```

```text output
[0, 1, 10, 11, 20, 21]
```

## `Arc<Mutex<_>>` shares a counter

`Arc` is the shared owner. `Mutex` is the exclusive access. Eight threads
each add 1000, so the counter ends at 8000 no matter how they interleave.

```rust file=n04.rs
use std::sync::{Arc, Mutex};
use std::thread;

fn main() {
    let counter = Arc::new(Mutex::new(0));
    let workers: Vec<_> = (0..8)
        .map(|_| {
            let c = Arc::clone(&counter);
            thread::spawn(move || {
                for _ in 0..1000 {
                    *c.lock().unwrap() += 1;
                }
            })
        })
        .collect();
    for w in workers {
        w.join().unwrap();
    }
    println!("{}", *counter.lock().unwrap());
}
```

```text output
8000
```

## A panic while holding the lock poisons it

The next `lock()` returns `Err`. `unwrap()` would panic again. `into_inner`
on that error recovers the data. The hook hides the panic text. The panic
stays in the thread that raised it. `join` is how the parent hears about it.

```rust file=n05.rs
use std::sync::{Arc, Mutex};
use std::thread;

fn main() {
    std::panic::set_hook(Box::new(|_| {}));
    let m = Arc::new(Mutex::new(1));
    let c = Arc::clone(&m);
    let joined = thread::spawn(move || {
        let _g = c.lock().unwrap();
        panic!("boom");
    })
    .join();
    println!("{} {}", joined.is_err(), m.lock().unwrap_err().into_inner());
}
```

```text output
true 1
```

## Atomics count without a lock

`Ordering::Relaxed` is enough for a counter that nothing else depends on.
Use `SeqCst`, or Acquire and Release, when one atomic has to be ordered
against another variable.

```rust file=n06.rs
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::thread;

fn main() {
    let hits = Arc::new(AtomicUsize::new(0));
    let workers: Vec<_> = (0..8)
        .map(|_| {
            let h = Arc::clone(&hits);
            thread::spawn(move || {
                for _ in 0..1000 {
                    h.fetch_add(1, Ordering::Relaxed);
                }
            })
        })
        .collect();
    for w in workers {
        w.join().unwrap();
    }
    println!("{}", hits.load(Ordering::SeqCst));
}
```

```text output
8000
```

## `RwLock` allows many readers or one writer

Two `read` guards may overlap. A `write` guard waits until they are dropped.
The reads here finish before the write, because the guards live in the inner
block.

```rust file=n07.rs
use std::sync::{Arc, RwLock};

fn main() {
    let cfg = Arc::new(RwLock::new(String::from("v1")));
    {
        let r1 = cfg.read().unwrap();
        let r2 = cfg.read().unwrap();
        println!("{} {}", *r1, *r2);
    }
    *cfg.write().unwrap() = "v2".to_string();
    println!("{}", cfg.read().unwrap());
}
```

```text output
v1 v1
v2
```

## A pool is a channel of jobs and a channel of results

Each worker locks the receiver, takes one job, and sends the square back.
Closing the job channel is the shutdown signal: `recv` returns `Err` and the
worker breaks. The squares can arrive in any order, so sort them.

```rust file=n08.rs
use std::sync::{Arc, Mutex};
use std::sync::mpsc;
use std::thread;

fn main() {
    let (job_tx, job_rx) = mpsc::channel::<u32>();
    let job_rx = Arc::new(Mutex::new(job_rx));
    let (res_tx, res_rx) = mpsc::channel();
    let pool: Vec<_> = (0..3)
        .map(|_| {
            let rx = Arc::clone(&job_rx);
            let tx = res_tx.clone();
            thread::spawn(move || loop {
                let job = rx.lock().unwrap().recv();
                match job {
                    Ok(n) => tx.send(n * n).unwrap(),
                    Err(_) => break,
                }
            })
        })
        .collect();
    drop(res_tx);
    for n in 1..=6 {
        job_tx.send(n).unwrap();
    }
    drop(job_tx);
    let mut squares: Vec<u32> = res_rx.iter().collect();
    squares.sort();
    println!("{squares:?}");
    for w in pool {
        w.join().unwrap();
    }
}
```

```text output
[1, 4, 9, 16, 25, 36]
```

## `recv_timeout` fails when nobody sends

The sender is kept alive and unused, so the channel stays open and the wait
ends as a timeout rather than as a disconnect. The port number of a socket
changes every run. A duration you chose does not.

```rust file=n09.rs
use std::sync::mpsc;
use std::time::Duration;

fn main() {
    let (_keep_alive, rx) = mpsc::channel::<i32>();
    match rx.recv_timeout(Duration::from_millis(20)) {
        Err(mpsc::RecvTimeoutError::Timeout) => println!("timeout"),
        other => println!("{other:?}"),
    }
}
```

```text output
timeout
```

## Exercises

```rust file=exercise.rs
#![allow(dead_code)] // the stubs below do not use their fields yet
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

/// Apply f to every element on its own thread; keep the input order.
fn parallel_map(_data: Vec<i32>, _f: fn(i32) -> i32) -> Vec<i32> {
    todo!()
}

/// Sum `data` using `threads` scoped threads over chunks.
fn parallel_sum(_data: &[i64], _threads: usize) -> i64 {
    todo!()
}

/// A word counter that can be cloned and shared between threads.
#[derive(Clone)]
struct SharedCounts {
    inner: Arc<Mutex<HashMap<String, u32>>>,
}

impl SharedCounts {
    fn new() -> Self {
        SharedCounts { inner: Arc::new(Mutex::new(HashMap::new())) }
    }
    fn incr(&self, _key: &str) {
        todo!()
    }
    fn get(&self, _key: &str) -> u32 {
        todo!()
    }
}

/// Stage 1 squares each number, stage 2 keeps only the even results.
/// Each stage runs on its own thread, connected by channels.
fn pipeline(_input: Vec<i32>) -> Vec<i32> {
    todo!()
}

/// Run f on another thread; None if it takes longer than `limit`.
fn with_timeout<T: Send + 'static>(
    _limit: Duration,
    _f: impl FnOnce() -> T + Send + 'static,
) -> Option<T> {
    todo!()
}

fn check<T: PartialEq + std::fmt::Debug>(label: &str, got: T, want: T) -> bool {
    let ok = got == want;
    if ok {
        println!("PASS {label}");
    } else {
        println!("FAIL {label}: got {got:?}, want {want:?}");
    }
    ok
}

fn main() {
    let counts = SharedCounts::new();
    let hs: Vec<_> = (0..10)
        .map(|_| {
            let c = counts.clone();
            thread::spawn(move || {
                for _ in 0..100 {
                    c.incr("hits");
                }
            })
        })
        .collect();
    for h in hs {
        h.join().unwrap();
    }
    let big: Vec<i64> = (1..=1000).collect();
    let results = [
        check("parallel_map", parallel_map(vec![1, 2, 3, 4], |x| x * x), vec![1, 4, 9, 16]),
        check("parallel_sum", parallel_sum(&big, 4), 500_500),
        check("parallel_sum 1", parallel_sum(&big, 1), 500_500),
        check("parallel_sum empty", parallel_sum(&[], 3), 0),
        check("shared counts", (counts.get("hits"), counts.get("none")), (1000, 0)),
        check("pipeline", pipeline(vec![1, 2, 3, 4, 5]), vec![4, 16]),
        check("timeout ok", with_timeout(Duration::from_millis(200), || 7), Some(7)),
        check(
            "timeout hit",
            with_timeout(Duration::from_millis(20), || {
                thread::sleep(Duration::from_millis(300));
                1
            }),
            None,
        ),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

<details><summary>Solution</summary>

```rust file=solution.rs
use std::collections::HashMap;
use std::sync::mpsc;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

fn parallel_map(data: Vec<i32>, f: fn(i32) -> i32) -> Vec<i32> {
    let handles: Vec<_> = data
        .into_iter()
        .map(|x| thread::spawn(move || f(x)))
        .collect();
    handles.into_iter().map(|h| h.join().unwrap()).collect()
}

fn parallel_sum(data: &[i64], threads: usize) -> i64 {
    if data.is_empty() {
        return 0;
    }
    let chunk = data.len().div_ceil(threads.max(1));
    thread::scope(|s| {
        let handles: Vec<_> = data
            .chunks(chunk)
            .map(|c| s.spawn(move || c.iter().sum::<i64>()))
            .collect();
        handles.into_iter().map(|h| h.join().unwrap()).sum()
    })
}

#[derive(Clone)]
struct SharedCounts {
    inner: Arc<Mutex<HashMap<String, u32>>>,
}

impl SharedCounts {
    fn new() -> Self {
        SharedCounts { inner: Arc::new(Mutex::new(HashMap::new())) }
    }
    fn incr(&self, key: &str) {
        *self.inner.lock().unwrap().entry(key.to_string()).or_insert(0) += 1;
    }
    fn get(&self, key: &str) -> u32 {
        self.inner.lock().unwrap().get(key).copied().unwrap_or(0)
    }
}

fn pipeline(input: Vec<i32>) -> Vec<i32> {
    let (tx1, rx1) = mpsc::channel();
    let (tx2, rx2) = mpsc::channel();
    let (tx3, rx3) = mpsc::channel();

    let feeder = thread::spawn(move || {
        for x in input {
            tx1.send(x).unwrap();
        }
    });
    let squarer = thread::spawn(move || {
        for x in rx1 {
            tx2.send(x * x).unwrap();
        }
    });
    let filter = thread::spawn(move || {
        for x in rx2 {
            if x % 2 == 0 {
                tx3.send(x).unwrap();
            }
        }
    });

    let out: Vec<i32> = rx3.iter().collect();
    for h in [feeder, squarer, filter] {
        h.join().unwrap();
    }
    out
}

fn with_timeout<T: Send + 'static>(
    limit: Duration,
    f: impl FnOnce() -> T + Send + 'static,
) -> Option<T> {
    let (tx, rx) = mpsc::channel();
    thread::spawn(move || {
        let _ = tx.send(f());
    });
    rx.recv_timeout(limit).ok()
}

fn check<T: PartialEq + std::fmt::Debug>(label: &str, got: T, want: T) -> bool {
    let ok = got == want;
    if ok {
        println!("PASS {label}");
    } else {
        println!("FAIL {label}: got {got:?}, want {want:?}");
    }
    ok
}

fn main() {
    let counts = SharedCounts::new();
    let hs: Vec<_> = (0..10)
        .map(|_| {
            let c = counts.clone();
            thread::spawn(move || {
                for _ in 0..100 {
                    c.incr("hits");
                }
            })
        })
        .collect();
    for h in hs {
        h.join().unwrap();
    }
    let big: Vec<i64> = (1..=1000).collect();
    let results = [
        check("parallel_map", parallel_map(vec![1, 2, 3, 4], |x| x * x), vec![1, 4, 9, 16]),
        check("parallel_sum", parallel_sum(&big, 4), 500_500),
        check("parallel_sum 1", parallel_sum(&big, 1), 500_500),
        check("parallel_sum empty", parallel_sum(&[], 3), 0),
        check("shared counts", (counts.get("hits"), counts.get("none")), (1000, 0)),
        check("pipeline", pipeline(vec![1, 2, 3, 4, 5]), vec![4, 16]),
        check("timeout ok", with_timeout(Duration::from_millis(200), || 7), Some(7)),
        check(
            "timeout hit",
            with_timeout(Duration::from_millis(20), || {
                thread::sleep(Duration::from_millis(300));
                1
            }),
            None,
        ),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

</details>

Next: [12 — Idiomatic Rust](12-idiomatic-rust.md)
