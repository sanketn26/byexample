# Rust 07 — Error Handling

No exceptions. Recoverable failures are `Result<T, E>`, absence is
`Option<T>`, and the `?` operator propagates errors upward. `panic!` is for
bugs.

## Example

```rust file=example.rs
use std::collections::HashMap;
use std::error::Error;
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

impl Error for ConfigError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            ConfigError::BadNumber(e) => Some(e),
            _ => None,
        }
    }
}

// `?` calls From::from on the error, so this conversion makes it automatic
impl From<ParseIntError> for ConfigError {
    fn from(e: ParseIntError) -> Self {
        ConfigError::BadNumber(e)
    }
}

fn get_port(cfg: &HashMap<&str, &str>) -> Result<u16, ConfigError> {
    let raw = cfg
        .get("port")
        .ok_or_else(|| ConfigError::Missing("port".into()))?;
    let n: i64 = raw.parse()?; // ParseIntError -> ConfigError
    u16::try_from(n).map_err(|_| ConfigError::OutOfRange(n))
}

// Sum<Result<..>> short-circuits on the first Err
fn sum_all(items: &[&str]) -> Result<i32, ParseIntError> {
    items.iter().map(|s| s.parse::<i32>()).sum()
}

// `?` works on Option too
fn first_even(xs: &[i32]) -> Option<i32> {
    xs.iter().copied().find(|x| x % 2 == 0)
}

fn describe(xs: &[i32]) -> Option<String> {
    let e = first_even(xs)?;
    Some(format!("even {e}"))
}

// Box<dyn Error> accepts any error type: convenient in applications
fn run() -> Result<(), Box<dyn Error>> {
    let n: i32 = "12x".parse()?;
    println!("{n}");
    Ok(())
}

fn main() {
    let mut cfg = HashMap::new();
    cfg.insert("port", "8080");
    println!("{:?}", get_port(&cfg));

    for (key, value) in [("port", "http"), ("port", "70000")] {
        cfg.insert(key, value);
        if let Err(e) = get_port(&cfg) {
            println!("{e}");
        }
    }
    cfg.clear();
    if let Err(e) = get_port(&cfg) {
        println!("{e}");
    }

    println!("{:?} {}", sum_all(&["1", "2", "3"]), sum_all(&["1", "x"]).is_err());
    let r: Result<Vec<i32>, _> = ["1", "2", "3"].iter().map(|s| s.parse::<i32>()).collect();
    println!("{r:?}");
    println!("{:?} {:?}", describe(&[1, 3, 4]), describe(&[1, 3]));

    if let Err(e) = run() {
        println!("run failed: {e}");
    }

    println!("{}", "x".parse::<i32>().unwrap_or(-1));

    let bad = "x".parse::<i32>().unwrap_err();
    println!("{}", ConfigError::BadNumber(bad).source().is_some());

    // A panic unwinds; catch_unwind exists but is for boundaries, not flow
    let caught = std::panic::catch_unwind(|| {
        let v: Vec<i32> = Vec::new();
        v[0]
    });
    println!("{}", caught.is_err());
}
```

```text output
Ok(8080)
bad number: invalid digit found in string
70000 is out of range
missing key: port
Ok(6) true
Ok([1, 2, 3])
Some("even 4") None
run failed: invalid digit found in string
-1
true
true
```

## Details that bite

- `unwrap()` and `expect("why this can't fail")` panic on `Err`/`None`.
  Fine in tests and prototypes; in libraries return the `Result`.
- `?` only works in a function whose return type can absorb the error
  (`Result<_, E>` where `E: From<ParseIntError>`, or `Option`). `main` may
  return `Result<(), Box<dyn Error>>`.
- Libraries should expose a concrete error type (often an enum, or
  `thiserror`); applications can use `Box<dyn Error>` or `anyhow`.
- Implement `Display` for people and `Error::source` to chain causes.
- `Result` is `#[must_use]`: ignoring a returned `Result` is a warning.
- Do not use `Option` for errors that carry a reason; the caller cannot
  tell *why* it failed.
- Panics in threads kill only that thread (see lesson 11); panics across
  an FFI boundary are undefined behaviour unless handled.
- `Option<T>` combinators (`map`, `and_then`, `ok_or`, `unwrap_or_else`)
  usually read better than nested `match`.

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
