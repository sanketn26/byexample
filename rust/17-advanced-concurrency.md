# Rust 17 — Advanced concurrency

A thread per request, with nothing to stop it and nowhere for work to
queue, fails by exhausting memory or file descriptors. Bound the workers.
Bound the channel. Put a deadline on the wait. Make shutdown something the
workers can see. This is the shape of a server in front of the sockets from
the previous lesson. Tokio's runtime is the same shape with a different
scheduler. It does not remove the bound, the deadline, or the shutdown.
Join the workers before the process exits.

## The pool's high-water mark is the bound

Two workers run, and the queue holds the rest. The gate keeps the first
wave inside the job until that many have entered, so `max` does not depend
on the scheduler. `max` is the number you have to be able to explain: it is
how many jobs are in progress at once.

```rust file=n01.rs
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Condvar, Mutex};
use std::sync::mpsc;
use std::thread;

fn run_pool(workers: usize, jobs: &[i32]) -> (Vec<i32>, usize) {
    let n = jobs.len();
    let results = Arc::new(Mutex::new(vec![0; n]));
    let max_in = Arc::new(AtomicUsize::new(0));
    let cur = Arc::new(AtomicUsize::new(0));
    let (tx, rx) = mpsc::channel::<(usize, i32)>();
    let rx = Arc::new(Mutex::new(rx));
    let need = workers.min(n);
    let arrived = Arc::new((Mutex::new(0usize), Condvar::new()));
    let gate = Arc::new((Mutex::new(false), Condvar::new()));

    thread::scope(|s| {
        for _ in 0..workers {
            let rx = Arc::clone(&rx);
            let results = Arc::clone(&results);
            let max_in = Arc::clone(&max_in);
            let cur = Arc::clone(&cur);
            let arrived = Arc::clone(&arrived);
            let gate = Arc::clone(&gate);
            s.spawn(move || loop {
                let next = rx.lock().unwrap().recv();
                let Ok((i, job)) = next else { break };
                let now = cur.fetch_add(1, Ordering::SeqCst) + 1;
                max_in.fetch_max(now, Ordering::SeqCst);
                {
                    let (lock, cv) = &*arrived;
                    let mut g = lock.lock().unwrap();
                    *g += 1;
                    cv.notify_all();
                }
                {
                    let (lock, cv) = &*gate;
                    let mut open = lock.lock().unwrap();
                    while !*open {
                        open = cv.wait(open).unwrap();
                    }
                }
                results.lock().unwrap()[i] = job * job;
                cur.fetch_sub(1, Ordering::SeqCst);
            });
        }
        s.spawn(move || {
            for (i, job) in jobs.iter().copied().enumerate() {
                tx.send((i, job)).unwrap();
            }
        });
        {
            let (lock, cv) = &*arrived;
            let mut g = lock.lock().unwrap();
            while *g < need {
                g = cv.wait(g).unwrap();
            }
        }
        {
            let (lock, cv) = &*gate;
            *lock.lock().unwrap() = true;
            cv.notify_all();
        }
    });

    let results = Arc::try_unwrap(results).unwrap().into_inner().unwrap();
    (results, max_in.load(Ordering::SeqCst))
}

fn main() {
    let (results, max_in) = run_pool(2, &[0, 1, 2, 3]);
    println!("pool {results:?} {max_in}");
}
```

```text output
pool [0, 1, 4, 9] 2
```

## A deadline covers the whole wait

`recv_timeout` fails when the duration is up. A 150 millisecond read
timeout inside a transfer that retries forever is not a deadline. The
budget has to include every retry. `context` in other languages, and
`poll`, are the same idea.

```rust file=n02.rs
use std::sync::mpsc::{self, RecvTimeoutError};
use std::time::Duration;

fn main() {
    let (_tx, rx) = mpsc::channel::<i32>();
    match rx.recv_timeout(Duration::from_millis(30)) {
        Err(RecvTimeoutError::Timeout) => println!("deadline"),
        other => println!("unexpected {other:?}"),
    }
}
```

```text output
deadline
```

## `try_send` is backpressure

A `sync_channel(2)` holds two values. The third `try_send` fails
immediately. The producer hears about it on this thread. A blocking send
would hide the problem on a thread you may not be able to spare.
`put_nowait`, a `select` with a default, and a ring that refuses the next
push are the same signal.

```rust file=n03.rs
use std::sync::mpsc;

fn main() {
    let (tx, _rx) = mpsc::sync_channel(2);
    let mut accepted = 0;
    for i in 0..5 {
        if tx.try_send(i).is_ok() {
            accepted += 1;
        } else {
            break;
        }
    }
    println!("accepted {accepted}");
}
```

```text output
accepted 2
```

## Shutdown is cooperative

The workers are alive, then told to stop. Setting the flag does nothing to
a worker blocked in a syscall until that syscall is interruptible too:
close the fd, or give the read its own deadline. These workers are blocked
on a condition variable, which `notify_all` wakes. The four queued jobs
stay queued (`stopped 4`) for the caller to drop or drain. Cancelling does
not throw them away.

```rust file=n04.rs
use std::sync::{Arc, Barrier, Condvar, Mutex};
use std::sync::mpsc;
use std::thread;

fn main() {
    let (tx, rx) = mpsc::channel::<i32>();
    for i in 0..4 {
        tx.send(i).unwrap();
    }
    drop(tx);
    let stop = Arc::new((Mutex::new(false), Condvar::new()));
    let started = Arc::new(Barrier::new(3));
    thread::scope(|s| {
        for _ in 0..2 {
            let stop = Arc::clone(&stop);
            let started = Arc::clone(&started);
            s.spawn(move || {
                started.wait();
                let (lock, cv) = &*stop;
                let mut g = lock.lock().unwrap();
                while !*g {
                    g = cv.wait(g).unwrap();
                }
            });
        }
        started.wait();
        let (lock, cv) = &*stop;
        *lock.lock().unwrap() = true;
        cv.notify_all();
    });
    let mut left = 0;
    while rx.try_recv().is_ok() {
        left += 1;
    }
    println!("stopped {left}");
}
```

```text output
stopped 4
```

## Exercises

`map_pool` runs `f` on each job with at most `workers` threads and reports the high-water mark. `deadline` returns `deadline` when a receive times out. `try_put` reports how many of `n` items fit in a bounded channel without blocking.

```rust file=exercise.rs
#![allow(dead_code, unused_imports, unused_variables)]
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::mpsc::{self, RecvTimeoutError};
use std::sync::{Arc, Condvar, Mutex};
use std::thread;
use std::time::{Duration, Instant};

fn map_pool(workers: usize, jobs: &[i32], f: &(dyn Fn(i32) -> i32 + Sync)) -> (Vec<i32>, usize) {
    let _ = (workers, jobs, f);
    todo!()
}



fn deadline() -> &'static str {
    todo!()
}



fn try_put(limit: usize, n: usize) -> usize {
    let _ = (limit, n);
    todo!()
}



fn check(label: &str, got: impl std::fmt::Debug, want: impl std::fmt::Debug) -> bool {
    let gs = format!("{got:?}");
    let ws = format!("{want:?}");
    if gs == ws {
        println!("PASS {label}");
        true
    } else {
        println!("FAIL {label}: got {gs}, want {ws}");
        false
    }
}

fn main() {
    let cur = AtomicUsize::new(0);
    let seen = AtomicUsize::new(0);
    let release = Arc::new((Mutex::new(false), Condvar::new()));
    let f = |i: i32| {
        let c = cur.fetch_add(1, Ordering::SeqCst) + 1;
        seen.fetch_max(c, Ordering::SeqCst);
        if c >= 2 {
            let (lock, cv) = &*release;
            *lock.lock().unwrap() = true;
            cv.notify_all();
        }
        let (lock, cv) = &*release;
        let mut g = lock.lock().unwrap();
        let start = Instant::now();
        while !*g && start.elapsed() < Duration::from_secs(1) {
            let (next, _) = cv.wait_timeout(g, Duration::from_millis(20)).unwrap();
            g = next;
        }
        cur.fetch_sub(1, Ordering::SeqCst);
        i * i
    };
    let (results, max_in) = map_pool(2, &[0, 1, 2, 3], &f);
    let mut ok = check("pool", (results, max_in, seen.load(Ordering::SeqCst)), (vec![0, 1, 4, 9], 2, 2));
    ok &= check("deadline", deadline(), "deadline");
    ok &= check("accepted", try_put(2, 5), 2);
    if !ok {
        std::process::exit(1);
    }
}
```

<details><summary>Solution</summary>

```rust file=solution.rs
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::mpsc::{self, RecvTimeoutError};
use std::sync::{Arc, Condvar, Mutex};
use std::thread;
use std::time::{Duration, Instant};

fn map_pool(workers: usize, jobs: &[i32], f: &(dyn Fn(i32) -> i32 + Sync)) -> (Vec<i32>, usize) {
    let n = jobs.len();
    let results = Arc::new(Mutex::new(vec![0; n]));
    let max_in = Arc::new(AtomicUsize::new(0));
    let cur = Arc::new(AtomicUsize::new(0));
    let (tx, rx) = mpsc::sync_channel::<(usize, i32)>(n.max(1));
    for (i, job) in jobs.iter().copied().enumerate() {
        tx.send((i, job)).unwrap();
    }
    drop(tx);
    let rx = Arc::new(Mutex::new(rx));
    thread::scope(|s| {
        for _ in 0..workers {
            let rx = Arc::clone(&rx);
            let results = Arc::clone(&results);
            let max_in = Arc::clone(&max_in);
            let cur = Arc::clone(&cur);
            s.spawn(move || loop {
                let next = { rx.lock().unwrap().recv() };
                let Ok((i, job)) = next else { break };
                let now = cur.fetch_add(1, Ordering::SeqCst) + 1;
                max_in.fetch_max(now, Ordering::SeqCst);
                let value = f(job);
                results.lock().unwrap()[i] = value;
                cur.fetch_sub(1, Ordering::SeqCst);
            });
        }
    });
    let results = Arc::try_unwrap(results).unwrap().into_inner().unwrap();
    (results, max_in.load(Ordering::SeqCst))
}

fn deadline() -> &'static str {
    let (_tx, rx) = mpsc::channel::<i32>();
    match rx.recv_timeout(Duration::from_millis(30)) {
        Err(RecvTimeoutError::Timeout) => "deadline",
        _ => "ok",
    }
}

fn try_put(limit: usize, n: usize) -> usize {
    let (tx, _rx) = mpsc::sync_channel(limit);
    let mut accepted = 0;
    for i in 0..n {
        if tx.try_send(i).is_ok() {
            accepted += 1;
        } else {
            break;
        }
    }
    accepted
}

fn check(label: &str, got: impl std::fmt::Debug, want: impl std::fmt::Debug) -> bool {
    let gs = format!("{got:?}");
    let ws = format!("{want:?}");
    if gs == ws {
        println!("PASS {label}");
        true
    } else {
        println!("FAIL {label}: got {gs}, want {ws}");
        false
    }
}

fn main() {
    let cur = AtomicUsize::new(0);
    let seen = AtomicUsize::new(0);
    let release = Arc::new((Mutex::new(false), Condvar::new()));
    let f = |i: i32| {
        let c = cur.fetch_add(1, Ordering::SeqCst) + 1;
        seen.fetch_max(c, Ordering::SeqCst);
        if c >= 2 {
            let (lock, cv) = &*release;
            *lock.lock().unwrap() = true;
            cv.notify_all();
        }
        let (lock, cv) = &*release;
        let mut g = lock.lock().unwrap();
        let start = Instant::now();
        while !*g && start.elapsed() < Duration::from_secs(1) {
            let (next, _) = cv.wait_timeout(g, Duration::from_millis(20)).unwrap();
            g = next;
        }
        cur.fetch_sub(1, Ordering::SeqCst);
        i * i
    };
    let (results, max_in) = map_pool(2, &[0, 1, 2, 3], &f);
    let mut ok = check("pool", (results, max_in, seen.load(Ordering::SeqCst)), (vec![0, 1, 4, 9], 2, 2));
    ok &= check("deadline", deadline(), "deadline");
    ok &= check("accepted", try_put(2, 5), 2);
    if !ok {
        std::process::exit(1);
    }
}
```

</details>

Back to the [course index](README.md)
