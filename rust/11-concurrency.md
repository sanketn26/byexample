# Rust 11 — Concurrency

Rust's ownership rules extend to threads: the compiler rejects data races at
compile time ("fearless concurrency"). The `Send` and `Sync` marker traits
say what may cross threads; you mostly just see them in error messages.

## Example

```rust file=example.rs
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::mpsc;
use std::sync::{Arc, Mutex, RwLock};
use std::thread;
use std::time::Duration;

fn main() {
    // spawn + join returns the closure's value
    let handles: Vec<_> = (0..4).map(|i| thread::spawn(move || i * 10)).collect();
    let results: Vec<i32> = handles.into_iter().map(|h| h.join().unwrap()).collect();
    println!("{results:?}");

    // Scoped threads may borrow local data, because they must finish first
    let mut data = vec![0usize; 5];
    thread::scope(|s| {
        for (i, slot) in data.iter_mut().enumerate() {
            s.spawn(move || {
                *slot = i * i; // each thread owns a disjoint &mut
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

    // Message passing: many producers, one consumer
    let (tx, rx) = mpsc::channel();
    for id in 0..3 {
        let tx = tx.clone();
        thread::spawn(move || {
            for j in 0..2 {
                tx.send(id * 10 + j).unwrap();
            }
        });
    }
    drop(tx); // the iterator below ends when every sender is gone
    let mut got: Vec<i32> = rx.iter().collect();
    got.sort();
    println!("{got:?}");

    // Shared state: Arc for shared ownership, Mutex for exclusive access
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

    // Atomics for simple counters and flags
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

    // RwLock: many readers or one writer
    let cfg = Arc::new(RwLock::new(String::from("v1")));
    {
        let r1 = cfg.read().unwrap();
        let r2 = cfg.read().unwrap();
        println!("{} {}", *r1, *r2);
    }
    *cfg.write().unwrap() = "v2".to_string();
    println!("{}", cfg.read().unwrap());

    // A small worker pool: jobs in, results out
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
                    Err(_) => break, // channel closed: no more work
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

    // A panic stays inside its thread and shows up in join()
    let r = thread::spawn(|| {
        panic!("boom");
    })
    .join();
    println!("{}", r.is_err());

    // Timeouts
    let (_keep_alive, rx2) = mpsc::channel::<i32>();
    match rx2.recv_timeout(Duration::from_millis(20)) {
        Err(mpsc::RecvTimeoutError::Timeout) => println!("timeout"),
        other => println!("{other:?}"),
    }
}
```

```text output
[0, 10, 20, 30]
[0, 1, 4, 9, 16]
6
[0, 1, 10, 11, 20, 21]
8000
8000
v1 v1
v2
[1, 4, 9, 16, 25, 36]
true
timeout
```

## Details that bite

- `thread::spawn` requires `'static` closures, so borrowed locals do not
  work: `move` ownership in, or use `thread::scope`.
- `Rc` and `RefCell` are not `Send`/`Sync`; use `Arc` and `Mutex`/`RwLock`.
  The compiler tells you exactly which type is the problem.
- A `MutexGuard` is released when it goes out of scope. Holding it across
  a blocking call or `.await` serialises everything.
- A thread that panics while holding a lock *poisons* it; later
  `lock()` returns `Err`. `unwrap()` propagates the panic; use
  `into_inner()` on the error to recover the data.
- Deadlock is still possible (lock ordering, a channel that never
  closes). Rust prevents data races, not deadlocks or logic races.
- Channels close when all `Sender`s are dropped: forgetting to `drop(tx)`
  makes `rx.iter()` hang forever.
- `Ordering::Relaxed` is enough for independent counters; use
  `SeqCst` (or Acquire/Release) when ordering between variables matters.
- Threads are OS threads. For large numbers of I/O tasks use `async`
  (with an executor such as `tokio`); for data parallelism use `rayon`.

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
