# Rust 13 — Testing

Rust builds testing into the toolchain: `#[test]` functions run by `cargo test` (or `rustc --test file.rs`). Lessons here are plain `rustc` programs, so the example writes a miniature of that harness: run each test, catch the panic, report. The last block of the example is the real `#[cfg(test)]` form wrapping the same functions, and it compiles with `rustc --test`.

## Example

```rust file=example.rs
use std::error::Error;
use std::fmt::{self, Write};
use std::panic::{self, AssertUnwindSafe};

// 1. The code under test: plain functions, no test hooks.
fn slugify(s: &str) -> String {
    let mut out = String::new();
    let mut dash = false;
    for c in s.chars().flat_map(|c| c.to_lowercase()) {
        if c.is_ascii_alphanumeric() {
            out.push(c);
            dash = false;
        } else if !dash && !out.is_empty() {
            out.push('-');
            dash = true;
        }
    }
    while out.ends_with('-') {
        out.pop();
    }
    out
}

#[derive(Debug, PartialEq)]
enum PortError {
    NotANumber,
    OutOfRange(u32),
}

fn parse_port(s: &str) -> Result<u16, PortError> {
    let n: u32 = s.parse().map_err(|_| PortError::NotANumber)?;
    if n == 0 || n > 65535 {
        return Err(PortError::OutOfRange(n));
    }
    Ok(n as u16)
}

fn first(v: &[i32]) -> i32 {
    v[0] // panics on an empty slice
}

// 2. Inject what the code cannot control (time, output) behind a trait.
trait Clock {
    fn hour(&self) -> u32;
}

fn greet(clock: &dyn Clock, name: &str, out: &mut dyn Write) -> fmt::Result {
    let part = if clock.hour() < 12 { "morning" } else { "evening" };
    writeln!(out, "good {part}, {name}")
}

struct FakeClock(u32);

impl Clock for FakeClock {
    fn hour(&self) -> u32 {
        self.0
    }
}

// 3. The tests. Each is a plain function: a panic is a failure, and
// returning Result lets `?` fail a test with the error it hit.
type Outcome = Result<(), Box<dyn Error>>;

fn test_slugify() -> Outcome {
    let cases = [
        ("plain", "Hello World", "hello-world"),
        ("punct", "  Rust, is -- fun!  ", "rust-is-fun"),
        ("empty", "", ""),
        ("digits", "Top 10", "top-10"),
    ];
    for (name, input, want) in cases {
        assert_eq!(slugify(input), want, "case {name}");
    }
    Ok(())
}

fn test_parse_port() -> Outcome {
    assert_eq!(parse_port("8080"), Ok(8080));
    assert_eq!(parse_port("x"), Err(PortError::NotANumber));
    assert_eq!(parse_port("70000"), Err(PortError::OutOfRange(70000)));
    Ok(())
}

fn test_greet() -> Outcome {
    let mut out = String::new();
    greet(&FakeClock(9), "Ada", &mut out)?; // fmt::Error converts via `?`
    greet(&FakeClock(20), "Bob", &mut out)?;
    assert_eq!(out, "good morning, Ada\ngood evening, Bob\n");
    Ok(())
}

fn test_first_panics_on_empty() -> Outcome {
    assert_eq!(first(&[7, 8]), 7);
    assert!(panic::catch_unwind(|| first(&[])).is_err()); // what #[should_panic] does
    Ok(())
}

// 4. A miniature of libtest: run each test, catch a panic, report.
fn run(tests: &[(&str, fn() -> Outcome)]) -> usize {
    panic::set_hook(Box::new(|_| {})); // keep panic noise off stderr
    let mut passed = 0;
    for (name, f) in tests {
        match panic::catch_unwind(AssertUnwindSafe(f)) {
            Ok(Ok(())) => {
                println!("PASS {name}");
                passed += 1;
            }
            Ok(Err(e)) => println!("FAIL {name}: {e}"),
            Err(p) => {
                let msg = p
                    .downcast_ref::<String>()
                    .cloned()
                    .or_else(|| p.downcast_ref::<&str>().map(|s| s.to_string()))
                    .unwrap_or_default();
                println!("FAIL {name}: {}", msg.replace('\n', " | "));
            }
        }
    }
    println!("{passed}/{} passed", tests.len());
    passed
}

fn main() {
    run(&[
        ("slugify", test_slugify),
        ("parse_port", test_parse_port),
        ("greet", test_greet),
        ("first_panics_on_empty", test_first_panics_on_empty),
    ]);

    // A failing assert names both sides.
    run(&[("broken", || {
        assert_eq!(slugify("A b"), "a_b");
        Ok(())
    })]);
}

// The same functions under `rustc --test` (or `cargo test`): no harness to write.
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn slugify_table() -> Outcome {
        test_slugify()
    }

    #[test]
    #[should_panic]
    fn first_of_empty() {
        first(&[]);
    }
}
```

```text output
PASS slugify
PASS parse_port
PASS greet
PASS first_panics_on_empty
4/4 passed
FAIL broken: assertion `left == right` failed |   left: "a-b" |  right: "a_b"
0/1 passed
```

## Details that bite

- **The real thing.** `rustc --edition 2021 --test file.rs && ./file` (or `cargo test`) runs every `#[test]` function in parallel and prints one line each. Unit tests live in a `#[cfg(test)] mod tests` beside the code, which is what lets them reach private functions. Integration tests live in `tests/` and see only the public API.
- **A panic is a failure.** `assert!`, `assert_eq!` and `unwrap()` all panic. `assert_eq!` prints both sides, so prefer it over `assert!(a == b)`. Add a message (`assert_eq!(x, y, "case {name}")`) when a loop hides which case failed.
- **Tests may return `Result`.** `fn t() -> Result<(), Box<dyn Error>>` lets you use `?` instead of `unwrap()`. A returned `Err` fails the test and prints the error.
- **`#[should_panic]`** passes only if the body panics. Add `expected = "substring"` so it cannot pass for the wrong panic. Prefer returning a `Result` from the code and asserting the `Err` when you can.
- **Trait objects are the seam.** Take `&dyn Clock` or a generic `C: Clock`, pass a fake in tests. Use `Cell` or `RefCell` inside the fake when the trait method takes `&self` but the test needs to move time forward.
- **Output is captured.** `println!` inside a passing test is hidden. Run with `-- --nocapture` to see it. Tests share a process and run in parallel, so do not rely on shared global state or on test order.
- **Doc tests.** A fenced block in a `///` comment is compiled and run by `cargo test`, so examples in documentation cannot go stale.

## Exercises

Write `parse_duration` and `RateLimiter::allow`. The harness and tests are given. Make every line say `PASS`. A call exactly `window` seconds after an earlier one no longer counts against the limit, and denied calls are not recorded.

```rust file=exercise.rs
use std::cell::Cell;
use std::error::Error;
use std::panic::{self, AssertUnwindSafe};
use std::process;

#[derive(Debug, PartialEq)]
struct BadDuration(String);

// parse_duration reads "1h30m", "45s", "2h" into seconds. Reject "", "10",
// "5x" and "h" with BadDuration(input).
fn parse_duration(s: &str) -> Result<u64, BadDuration> {
    let _ = s;
    Ok(0) // TODO
}

trait Clock {
    fn now(&self) -> f64;
}

// RateLimiter allows `limit` calls per `window` seconds. A call made exactly
// `window` seconds after an earlier one no longer counts against the limit.
// Denied calls are not recorded.
struct RateLimiter<'a> {
    limit: usize,
    window: f64,
    clock: &'a dyn Clock,
}

impl<'a> RateLimiter<'a> {
    fn new(limit: usize, window: f64, clock: &'a dyn Clock) -> Self {
        RateLimiter { limit, window, clock }
    }

    fn allow(&mut self) -> bool {
        let _ = (self.limit, self.window, self.clock.now());
        true // TODO
    }
}

struct FakeClock(Cell<f64>);

impl Clock for FakeClock {
    fn now(&self) -> f64 {
        self.0.get()
    }
}

type Outcome = Result<(), Box<dyn Error>>;

fn test_parse_duration() -> Outcome {
    for (input, want) in [("1h30m", 5400), ("45s", 45), ("2h", 7200), ("1m1s", 61)] {
        assert_eq!(parse_duration(input), Ok(want), "input {input:?}");
    }
    Ok(())
}

fn test_parse_duration_invalid() -> Outcome {
    for input in ["", "abc", "10", "5x", "h"] {
        assert_eq!(parse_duration(input), Err(BadDuration(input.to_string())), "input {input:?}");
    }
    Ok(())
}

fn test_limit_and_window() -> Outcome {
    let clock = FakeClock(Cell::new(0.0));
    let mut rl = RateLimiter::new(2, 10.0, &clock);
    assert!(rl.allow(), "first");
    assert!(rl.allow(), "second");
    assert!(!rl.allow(), "third");
    clock.0.set(9.9);
    assert!(!rl.allow(), "just inside the window");
    clock.0.set(10.0);
    assert!(rl.allow(), "expired");
    Ok(())
}

fn test_denied_do_not_count() -> Outcome {
    let clock = FakeClock(Cell::new(0.0));
    let mut rl = RateLimiter::new(1, 5.0, &clock);
    assert!(rl.allow());
    for _ in 0..10 {
        assert!(!rl.allow());
    }
    clock.0.set(5.0);
    assert!(rl.allow(), "denied calls were counted");
    Ok(())
}

fn run(tests: &[(&str, fn() -> Outcome)]) -> usize {
    panic::set_hook(Box::new(|_| {}));
    let mut passed = 0;
    for (name, f) in tests {
        match panic::catch_unwind(AssertUnwindSafe(f)) {
            Ok(Ok(())) => {
                println!("PASS {name}");
                passed += 1;
            }
            Ok(Err(e)) => println!("FAIL {name}: {e}"),
            Err(p) => {
                let msg = p
                    .downcast_ref::<String>()
                    .cloned()
                    .or_else(|| p.downcast_ref::<&str>().map(|s| s.to_string()))
                    .unwrap_or_default();
                println!("FAIL {name}: {}", msg.replace('\n', " | "));
            }
        }
    }
    passed
}

fn main() {
    let tests: [(&str, fn() -> Outcome); 4] = [
        ("parse_duration", test_parse_duration),
        ("parse_duration_invalid", test_parse_duration_invalid),
        ("limit_and_window", test_limit_and_window),
        ("denied_do_not_count", test_denied_do_not_count),
    ];
    let passed = run(&tests);
    println!("{passed}/{} passed", tests.len());
    if passed != tests.len() {
        process::exit(1);
    }
}
```

<details><summary>Solution</summary>

```rust file=solution.rs
use std::cell::Cell;
use std::collections::VecDeque;
use std::error::Error;
use std::panic::{self, AssertUnwindSafe};
use std::process;

#[derive(Debug, PartialEq)]
struct BadDuration(String);

// parse_duration reads "1h30m", "45s", "2h" into seconds.
fn parse_duration(s: &str) -> Result<u64, BadDuration> {
    let bad = || BadDuration(s.to_string());
    let (mut total, mut n, mut seen) = (0u64, 0u64, false);
    for c in s.chars() {
        match c {
            '0'..='9' => {
                n = n * 10 + c.to_digit(10).unwrap() as u64;
                seen = true;
            }
            'h' | 'm' | 's' if seen => {
                total += n * match c {
                    'h' => 3600,
                    'm' => 60,
                    _ => 1,
                };
                n = 0;
                seen = false;
            }
            _ => return Err(bad()),
        }
    }
    if s.is_empty() || seen {
        return Err(bad());
    }
    Ok(total)
}

trait Clock {
    fn now(&self) -> f64;
}

// RateLimiter allows `limit` calls per `window` seconds.
struct RateLimiter<'a> {
    limit: usize,
    window: f64,
    clock: &'a dyn Clock,
    calls: VecDeque<f64>,
}

impl<'a> RateLimiter<'a> {
    fn new(limit: usize, window: f64, clock: &'a dyn Clock) -> Self {
        RateLimiter { limit, window, clock, calls: VecDeque::new() }
    }

    fn allow(&mut self) -> bool {
        let now = self.clock.now();
        while self.calls.front().is_some_and(|&t| now - t >= self.window) {
            self.calls.pop_front();
        }
        if self.calls.len() >= self.limit {
            return false;
        }
        self.calls.push_back(now);
        true
    }
}

struct FakeClock(Cell<f64>);

impl Clock for FakeClock {
    fn now(&self) -> f64 {
        self.0.get()
    }
}

type Outcome = Result<(), Box<dyn Error>>;

fn test_parse_duration() -> Outcome {
    for (input, want) in [("1h30m", 5400), ("45s", 45), ("2h", 7200), ("1m1s", 61)] {
        assert_eq!(parse_duration(input), Ok(want), "input {input:?}");
    }
    Ok(())
}

fn test_parse_duration_invalid() -> Outcome {
    for input in ["", "abc", "10", "5x", "h"] {
        assert_eq!(parse_duration(input), Err(BadDuration(input.to_string())), "input {input:?}");
    }
    Ok(())
}

fn test_limit_and_window() -> Outcome {
    let clock = FakeClock(Cell::new(0.0));
    let mut rl = RateLimiter::new(2, 10.0, &clock);
    assert!(rl.allow(), "first");
    assert!(rl.allow(), "second");
    assert!(!rl.allow(), "third");
    clock.0.set(9.9);
    assert!(!rl.allow(), "just inside the window");
    clock.0.set(10.0);
    assert!(rl.allow(), "expired");
    Ok(())
}

fn test_denied_do_not_count() -> Outcome {
    let clock = FakeClock(Cell::new(0.0));
    let mut rl = RateLimiter::new(1, 5.0, &clock);
    assert!(rl.allow());
    for _ in 0..10 {
        assert!(!rl.allow());
    }
    clock.0.set(5.0);
    assert!(rl.allow(), "denied calls were counted");
    Ok(())
}

fn run(tests: &[(&str, fn() -> Outcome)]) -> usize {
    panic::set_hook(Box::new(|_| {}));
    let mut passed = 0;
    for (name, f) in tests {
        match panic::catch_unwind(AssertUnwindSafe(f)) {
            Ok(Ok(())) => {
                println!("PASS {name}");
                passed += 1;
            }
            Ok(Err(e)) => println!("FAIL {name}: {e}"),
            Err(p) => {
                let msg = p
                    .downcast_ref::<String>()
                    .cloned()
                    .or_else(|| p.downcast_ref::<&str>().map(|s| s.to_string()))
                    .unwrap_or_default();
                println!("FAIL {name}: {}", msg.replace('\n', " | "));
            }
        }
    }
    passed
}

fn main() {
    let tests: [(&str, fn() -> Outcome); 4] = [
        ("parse_duration", test_parse_duration),
        ("parse_duration_invalid", test_parse_duration_invalid),
        ("limit_and_window", test_limit_and_window),
        ("denied_do_not_count", test_denied_do_not_count),
    ];
    let passed = run(&tests);
    println!("{passed}/{} passed", tests.len());
    if passed != tests.len() {
        process::exit(1);
    }
}
```

</details>

Next: [14 — Capstone: an LRU cache](14-capstone-lru.md)
