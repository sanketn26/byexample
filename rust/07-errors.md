# Rust 07 — Error Handling

There are no exceptions. A recoverable failure is `Result<T, E>`. Absence
without a reason is `Option<T>`. The `?` operator returns the error to the
caller. `panic!` is for bugs, not for bad input.

## `?` needs a `From` conversion

`?` on a `Result` returns early on `Err`, and it calls `From::from` so the
error type can change on the way out. `Display` is the message a person
reads. `unwrap` and `expect` panic on `Err` or `None`. Fine in a test or a
prototype. A library returns the `Result`.

`?` only compiles in a function whose return type can absorb that error.
`main` itself may return `Result<(), E>`.

```rust file=n01.rs
use std::collections::HashMap;
use std::fmt;
use std::num::ParseIntError;

#[derive(Debug)]
enum ConfigError {
    Missing(String),
    BadNumber(ParseIntError),
    OutOfRange(i64),
}

impl fmt::Display for ConfigError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            ConfigError::Missing(k) => write!(f, "missing key: {k}"),
            ConfigError::BadNumber(e) => write!(f, "bad number: {e}"),
            ConfigError::OutOfRange(n) => write!(f, "{n} is out of range"),
        }
    }
}

impl From<ParseIntError> for ConfigError {
    fn from(e: ParseIntError) -> Self {
        ConfigError::BadNumber(e)
    }
}

fn get_port(cfg: &HashMap<&str, &str>) -> Result<u16, ConfigError> {
    let raw = cfg.get("port").ok_or_else(|| ConfigError::Missing("port".into()))?;
    let n: i64 = raw.parse()?;
    u16::try_from(n).map_err(|_| ConfigError::OutOfRange(n))
}

fn main() {
    let mut cfg = HashMap::new();
    cfg.insert("port", "8080");
    println!("{:?}", get_port(&cfg));
    for value in ["http", "70000"] {
        cfg.insert("port", value);
        println!("{}", get_port(&cfg).unwrap_err());
    }
    cfg.clear();
    println!("{}", get_port(&cfg).unwrap_err());
}
```

```text output
Ok(8080)
bad number: invalid digit found in string
70000 is out of range
missing key: port
```

## `Error::source` chains the cause

Implement `Display` for the reader and `Error::source` for the error that
caused this one. Libraries should expose a concrete error type, often an
enum. Applications can use `Box<dyn Error>` (or the `anyhow` crate) when
they only need to report the failure. Do not use `Option` when the caller
needs to know why it failed: `None` has no reason attached.

```rust file=n02.rs
use std::error::Error;
use std::fmt;
use std::num::ParseIntError;

#[derive(Debug)]
enum ConfigError {
    BadNumber(ParseIntError),
}

impl fmt::Display for ConfigError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            ConfigError::BadNumber(e) => write!(f, "bad number: {e}"),
        }
    }
}

impl Error for ConfigError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            ConfigError::BadNumber(e) => Some(e),
        }
    }
}

fn main() {
    let bad = "x".parse::<i32>().unwrap_err();
    println!("{}", ConfigError::BadNumber(bad).source().is_some());
}
```

```text output
true
```

## `Box<dyn Error>` accepts any error

The `?` in `run` turns a `ParseIntError` into a boxed trait object. The
caller prints it. A returned `Err` from `main` would do the same and then
exit non-zero.

```rust file=n03.rs
use std::error::Error;

fn run() -> Result<(), Box<dyn Error>> {
    let n: i32 = "12x".parse()?;
    println!("{n}");
    Ok(())
}

fn main() {
    if let Err(e) = run() {
        println!("run failed: {e}");
    }
}
```

```text output
run failed: invalid digit found in string
```

## Iterators of `Result` stop at the first error

`sum` on an iterator of `Result` is `Ok` only when every item parses.
`collect` does the same and builds the `Vec` only on success. `Result` is
`#[must_use]`: throwing one away is a warning, and these lessons treat
warnings as errors.

```rust file=n04.rs
use std::num::ParseIntError;

fn sum_all(items: &[&str]) -> Result<i32, ParseIntError> {
    items.iter().map(|s| s.parse::<i32>()).sum()
}

fn main() {
    println!("{:?} {}", sum_all(&["1", "2", "3"]), sum_all(&["1", "x"]).is_err());
    let r: Result<Vec<i32>, _> = ["1", "2", "3"].iter().map(|s| s.parse::<i32>()).collect();
    println!("{r:?}");
}
```

```text output
Ok(6) true
Ok([1, 2, 3])
```

## `?` works on `Option` too

It returns `None` early. The combinators `map`, `and_then`, `ok_or`, and
`unwrap_or_else` cover the same ground as a nested `match`, and they usually
read better.

```rust file=n05.rs
fn first_even(xs: &[i32]) -> Option<i32> {
    xs.iter().copied().find(|x| x % 2 == 0)
}

fn describe(xs: &[i32]) -> Option<String> {
    let e = first_even(xs)?;
    Some(format!("even {e}"))
}

fn main() {
    println!("{:?} {:?}", describe(&[1, 3, 4]), describe(&[1, 3]));
    let n = Some(2).map(|x| x + 1).and_then(|x| (x > 0).then_some(x));
    println!("{n:?}");
}
```

```text output
Some("even 4") None
Some(3)
```

## `unwrap_or` substitutes a value

`unwrap` would panic on `"x"`. `unwrap_or` returns the fallback instead.
`expect("why")` is `unwrap` with a message, for the cases that really are
bugs.

```rust file=n06.rs
fn main() {
    println!("{}", "42".parse::<i32>().expect("digits"));
    println!("{}", "x".parse::<i32>().unwrap_or(-1));
}
```

```text output
42
-1
```

## `catch_unwind` is a boundary, not a control flow

A panic unwinds the stack. Catch it only at a thread or an FFI edge: a panic
that crosses FFI is undefined behaviour unless something catches it. A panic
inside a thread kills that thread, not the process (lesson 11). The hook
below hides the panic text so the program's own output stays one line.

```rust file=n07.rs
fn main() {
    std::panic::set_hook(Box::new(|_| {}));
    let caught = std::panic::catch_unwind(|| {
        let v: Vec<i32> = Vec::new();
        v[0]
    });
    println!("{}", caught.is_err());
}
```

```text output
true
```

## Exercises

```rust file=exercise.rs
#[derive(Debug, PartialEq)]
enum ParseError {
    NotANumber,
    NotPositive(i64),
    TooLarge,
}

/// Parse a positive number that fits in u32.
/// "abc" -> NotANumber, "-5"/"0" -> NotPositive(n), "99999999999" -> TooLarge.
fn parse_positive(_s: &str) -> Result<u32, ParseError> {
    todo!()
}

#[derive(Debug, PartialEq)]
struct DivideByZero;

fn safe_divide(_a: i32, _b: i32) -> Result<i32, DivideByZero> {
    todo!()
}

/// "3,4" -> Ok((3, 4)); otherwise Err with a short description.
fn parse_pair(_s: &str) -> Result<(i32, i32), String> {
    todo!()
}

/// Sum the entries that parse as i32 and count the ones that do not.
fn sum_valid(_items: &[&str]) -> (i32, usize) {
    todo!()
}

/// Call f(attempt) for attempt in 0..n until it succeeds.
/// If all attempts fail return every error in order.
fn retry<T>(_n: u32, _f: impl FnMut(u32) -> Result<T, String>) -> Result<T, Vec<String>> {
    todo!()
}

/// Return the first word of the first line, or None.
fn first_word_of_first_line(_text: &str) -> Option<&str> {
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
    let results = [
        check("positive ok", parse_positive("42"), Ok(42)),
        check("positive nan", parse_positive("abc"), Err(ParseError::NotANumber)),
        check("positive neg", parse_positive("-5"), Err(ParseError::NotPositive(-5))),
        check("positive zero", parse_positive("0"), Err(ParseError::NotPositive(0))),
        check("positive big", parse_positive("99999999999"), Err(ParseError::TooLarge)),
        check("divide", safe_divide(7, 2), Ok(3)),
        check("divide zero", safe_divide(7, 0), Err(DivideByZero)),
        check("pair", parse_pair("3,4"), Ok((3, 4))),
        check("pair bad", parse_pair("3;4").is_err() && parse_pair("a,4").is_err(), true),
        check("sum_valid", sum_valid(&["1", "x", "5", "", "-2"]), (4, 2)),
        check("retry ok", retry(5, |i| if i < 2 { Err(format!("e{i}")) } else { Ok(i * 10) }), Ok(20)),
        check(
            "retry fail",
            retry::<()>(3, |i| Err(format!("e{i}"))),
            Err(vec!["e0".to_string(), "e1".to_string(), "e2".to_string()]),
        ),
        check("first word", first_word_of_first_line("hello world\nbye"), Some("hello")),
        check("first word none", first_word_of_first_line("   \nbye"), None),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

<details><summary>Solution</summary>

```rust file=solution.rs
#[derive(Debug, PartialEq)]
enum ParseError {
    NotANumber,
    NotPositive(i64),
    TooLarge,
}

fn parse_positive(s: &str) -> Result<u32, ParseError> {
    let n: i64 = s.parse().map_err(|_| ParseError::NotANumber)?;
    if n <= 0 {
        return Err(ParseError::NotPositive(n));
    }
    u32::try_from(n).map_err(|_| ParseError::TooLarge)
}

#[derive(Debug, PartialEq)]
struct DivideByZero;

fn safe_divide(a: i32, b: i32) -> Result<i32, DivideByZero> {
    a.checked_div(b).ok_or(DivideByZero)
}

fn parse_pair(s: &str) -> Result<(i32, i32), String> {
    let (a, b) = s.split_once(',').ok_or_else(|| format!("no comma in {s:?}"))?;
    let a = a.trim().parse().map_err(|e| format!("first: {e}"))?;
    let b = b.trim().parse().map_err(|e| format!("second: {e}"))?;
    Ok((a, b))
}

fn sum_valid(items: &[&str]) -> (i32, usize) {
    items.iter().fold((0, 0), |(sum, bad), s| match s.parse::<i32>() {
        Ok(n) => (sum + n, bad),
        Err(_) => (sum, bad + 1),
    })
}

fn retry<T>(n: u32, mut f: impl FnMut(u32) -> Result<T, String>) -> Result<T, Vec<String>> {
    let mut errors = Vec::new();
    for attempt in 0..n {
        match f(attempt) {
            Ok(v) => return Ok(v),
            Err(e) => errors.push(e),
        }
    }
    Err(errors)
}

fn first_word_of_first_line(text: &str) -> Option<&str> {
    text.lines().next()?.split_whitespace().next()
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
    let results = [
        check("positive ok", parse_positive("42"), Ok(42)),
        check("positive nan", parse_positive("abc"), Err(ParseError::NotANumber)),
        check("positive neg", parse_positive("-5"), Err(ParseError::NotPositive(-5))),
        check("positive zero", parse_positive("0"), Err(ParseError::NotPositive(0))),
        check("positive big", parse_positive("99999999999"), Err(ParseError::TooLarge)),
        check("divide", safe_divide(7, 2), Ok(3)),
        check("divide zero", safe_divide(7, 0), Err(DivideByZero)),
        check("pair", parse_pair("3,4"), Ok((3, 4))),
        check("pair bad", parse_pair("3;4").is_err() && parse_pair("a,4").is_err(), true),
        check("sum_valid", sum_valid(&["1", "x", "5", "", "-2"]), (4, 2)),
        check("retry ok", retry(5, |i| if i < 2 { Err(format!("e{i}")) } else { Ok(i * 10) }), Ok(20)),
        check(
            "retry fail",
            retry::<()>(3, |i| Err(format!("e{i}"))),
            Err(vec!["e0".to_string(), "e1".to_string(), "e2".to_string()]),
        ),
        check("first word", first_word_of_first_line("hello world\nbye"), Some("hello")),
        check("first word none", first_word_of_first_line("   \nbye"), None),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

</details>

Next: [08 — Ownership and borrowing](08-ownership.md)
