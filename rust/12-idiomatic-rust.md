# Rust 12 — Idiomatic Rust

Idiomatic Rust pushes work into the type system. Iterators instead of index
loops. `Option` and `Result` instead of sentinel values. Signatures that say
what they borrow. Types that cannot represent an illegal state. `cargo fmt`
and `cargo clippy -- -D warnings` are the shared style guide. Run both in
CI. Clippy is sometimes wrong: `#[allow(clippy::lint)]` with a comment that
says why is fine.

Prefer a small function with a name over a long one whose comments are the
headings. Prefer composition and a trait over a generic with six type
parameters. `#[must_use]`, `#[non_exhaustive]`, and `pub(crate)` keep an API
honest. Reach for crates for what `std` leaves out: `serde`, `clap`,
`anyhow` or `thiserror`, `tokio`, `rayon`, `itertools`.

## An iterator says the same thing as the index loop

`for i in 0..v.len() { v[i] }` is the C habit. `filter` and `map` name the
steps, and they cannot walk off the end. `for x in &v` is the form in
between.

```rust file=n01.rs
fn sum_even_squares_c_style(xs: &[i32]) -> i32 {
    let mut total = 0;
    let mut i = 0;
    while i < xs.len() {
        if xs[i] % 2 == 0 {
            total += xs[i] * xs[i];
        }
        i += 1;
    }
    total
}

fn sum_even_squares(xs: &[i32]) -> i32 {
    xs.iter().filter(|&&x| x % 2 == 0).map(|&x| x * x).sum()
}

fn main() {
    let xs = [1, 2, 3, 4];
    println!("{} {}", sum_even_squares_c_style(&xs), sum_even_squares(&xs));
}
```

```text output
20 20
```

## Take `&str`, not `&String`

A `&str` parameter accepts a literal, a slice, or a `&String`. A `&String`
parameter accepts only the owned kind. The same rule is `&[T]` instead of
`&Vec<T>`. Read-only text does not need an owned `String`, and it does not
need `impl AsRef<str>` unless several string-like types must work.

```rust file=n02.rs
fn count_a(s: &str) -> usize {
    s.chars().filter(|&c| c == 'a').count()
}

fn main() {
    let owned = String::from("banana");
    println!("{} {}", count_a("banana"), count_a(&owned));
}
```

```text output
3 3
```

## Combinators replace the nested match

`and_then`, `map`, and `unwrap_or_else` are the match you would have
written: look inside, transform, or substitute a default. `if x.is_some() {
x.unwrap() }` is `if let Some(x) = x`. A sentinel such as `""` or `-1` is
usually an `Option` that forgot its type. `x.clone()` to silence the borrow
checker is the last resort. Restructure, or borrow something smaller.

```rust file=n03.rs
fn user_domain(email: Option<&str>) -> String {
    email
        .and_then(|e| e.split_once('@'))
        .map(|(_, d)| d.to_lowercase())
        .unwrap_or_else(|| "unknown".to_string())
}

fn main() {
    println!("{} {}", user_domain(Some("Ann@Example.com")), user_domain(None));
}
```

```text output
example.com unknown
```

## `?` replaces match-and-return

In library code, return the `Result`. `unwrap` belongs in a test or in
`main` after you have decided the failure is fatal.

```rust file=n04.rs
fn parse_sum(a: &str, b: &str) -> Result<i32, std::num::ParseIntError> {
    Ok(a.parse::<i32>()? + b.parse::<i32>()?)
}

fn main() {
    println!("{:?} {}", parse_sum("3", "4"), parse_sum("3", "x").is_err());
}
```

```text output
Ok(7) true
```

## `let else` keeps the happy path flat

The `else` arm must diverge: `return`, `break`, or `panic`. The rest of the
function then uses the unwrapped value with no extra indent. Returning a
tuple or a struct beats an `&mut` out-parameter.

```rust file=n05.rs
fn first_char_upper(s: &str) -> String {
    let Some(c) = s.chars().next() else {
        return String::new();
    };
    c.to_uppercase().collect()
}

fn main() {
    println!("{:?} {:?}", first_char_upper("hello"), first_char_upper(""));
}
```

```text output
"H" ""
```

## `entry` updates or inserts in one step

`or_insert` yields a mutable reference to the value that is already there,
or to the one it just inserted. No separate `get` and `insert`.

```rust file=n06.rs
use std::collections::HashMap;

fn count_chars(s: &str) -> HashMap<char, usize> {
    let mut m = HashMap::new();
    for c in s.chars() {
        *m.entry(c).or_insert(0) += 1;
    }
    m
}

fn main() {
    let mut counts: Vec<_> = count_chars("banana").into_iter().collect();
    counts.sort();
    println!("{counts:?}");
}
```

```text output
[('a', 3), ('b', 1), ('n', 2)]
```

## A builder owns the options

`new` takes `impl Into<String>`, so a literal or a `String` both work.
Each setter consumes `self` and returns it, which is what makes the chain
compile. `Default` is derived, not written by hand. The fields stay private.
A pile of `bool` parameters would be this struct, or an enum, instead.

```rust file=n07.rs
#[derive(Debug, Default)]
struct Request {
    url: String,
    method: String,
    retries: u32,
}

impl Request {
    fn new(url: impl Into<String>) -> Self {
        Request {
            url: url.into(),
            method: "GET".into(),
            ..Default::default()
        }
    }
    fn method(mut self, m: &str) -> Self {
        self.method = m.to_string();
        self
    }
    fn retries(mut self, n: u32) -> Self {
        self.retries = n;
        self
    }
    fn describe(&self) -> String {
        format!("{} {} x{}", self.method, self.url, self.retries)
    }
}

fn main() {
    let req = Request::new("http://x").method("POST").retries(3);
    println!("{req:?} {}", req.describe());
}
```

```text output
Request { url: "http://x", method: "POST", retries: 3 } POST http://x x3
```

## A newtype makes the unit part of the type

`Feet` will not compile where `Meters` is required. `From` is the conversion
you opted into. `as` is the wrong tool for a fallible numeric conversion.
`try_from` fails when the value does not fit.

```rust file=n08.rs
struct Meters(f64);
struct Feet(f64);

impl From<Feet> for Meters {
    fn from(f: Feet) -> Self {
        Meters(f.0 * 0.3048)
    }
}

fn main() {
    println!("{:.3}", Meters::from(Feet(10.0)).0);
    println!("{:?} {:?}", u8::try_from(44i32).ok(), u8::try_from(300i32).ok());
}
```

```text output
3.048
Some(44) None
```

## Type-state makes the illegal call a type error

A closed door has no `walk_through`. An open door has no `open` again. The
state is a type parameter with no runtime data (`PhantomData`). That is
"parse, don't validate" applied to a sequence: bad states are not
representable, so a stringly flag never has to be checked. `Box<dyn Trait>`
is the wrong default for this. A generic, or a distinct type, is free.
Dynamic dispatch is for a heterogeneous collection.

```rust file=n09.rs
use std::marker::PhantomData;

struct Open;
struct Closed;

struct Door<State> {
    _state: PhantomData<State>,
}

impl Door<Closed> {
    fn new() -> Self {
        Door { _state: PhantomData }
    }
    fn open(self) -> Door<Open> {
        Door { _state: PhantomData }
    }
}

impl Door<Open> {
    fn walk_through(&self) -> &'static str {
        "through the open door"
    }
    fn close(self) -> Door<Closed> {
        Door { _state: PhantomData }
    }
}

fn main() {
    println!("{}", Door::new().open().close().open().walk_through());
}
```

```text output
through the open door
```

## `Display` is the text, not an ad-hoc method

Implement `Display` and you get `to_string` and `{}`. Document the type with
`///` comments. A code block in one of those comments is a doctest: `cargo
test` compiles it, so the example cannot rot quietly.

```rust file=n10.rs
use std::fmt;

struct Pt(i32, i32);

impl fmt::Display for Pt {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "({}, {})", self.0, self.1)
    }
}

fn main() {
    println!("{} {}", Pt(1, 2), Pt(1, 2).to_string().len());
}
```

```text output
(1, 2) 6
```

## `collect` builds the collection you name

The same iterator becomes a `HashMap`, a `String`, or an `Option<Vec<_>>`.
The `Option` form is `None` if any element is `None`.

```rust file=n11.rs
use std::collections::HashMap;

fn main() {
    let lens: HashMap<&str, usize> = ["a", "bb"].iter().map(|w| (*w, w.len())).collect();
    let joined: String = ['h', 'i'].iter().collect();
    let opt = ["1", "2"].iter().map(|s| s.parse().ok()).collect::<Option<Vec<i32>>>();
    println!("{joined} {opt:?} {}", lens["bb"]);
}
```

```text output
hi Some([1, 2]) 2
```

## `position`, `any`, and `all` are the early-exit loops

`position` returns the index. `any` and `all` stop as soon as the answer is
known.

```rust file=n12.rs
fn main() {
    let odds = [1, 5, 9];
    println!(
        "{:?} {} {}",
        odds.iter().position(|&x| x == 5),
        odds.iter().any(|&x| x > 8),
        odds.iter().all(|&x| x % 2 == 1)
    );
}
```

```text output
Some(1) true true
```

## `mem::take` moves out of a mutable borrow

It leaves `Default::default()` in place. For a `String`, that is empty. You
do not clone, and you do not need to own the container.

```rust file=n13.rs
fn main() {
    let mut name = String::from("x");
    let old = std::mem::take(&mut name);
    println!("{old:?} {name:?}");
}
```

```text output
"x" ""
```

## A tuple key sorts by more than one field

`Reverse(age)` is descending age. The name is the tie break, ascending.
`sort_by_key` calls the closure once per element.

```rust file=n14.rs
fn main() {
    let mut people = vec![("Al", 30), ("Bo", 25), ("Cy", 30)];
    people.sort_by_key(|&(name, age)| (std::cmp::Reverse(age), name));
    println!("{people:?}");
}
```

```text output
[("Al", 30), ("Cy", 30), ("Bo", 25)]
```

## `must_use` and `non_exhaustive` are part of the signature

Throwing away a `#[must_use]` value is a warning. `#[non_exhaustive]` means
another crate's `match` needs a wildcard, so you can add a variant later
without breaking that crate's build. Inside this crate the match can still
be exhaustive. `pub(crate)` keeps a helper visible to the crate and hidden
outside it.

```rust file=n15.rs
#[must_use]
fn answer() -> i32 {
    42
}

#[non_exhaustive]
enum Color {
    Red,
}

pub(crate) fn label(c: Color) -> &'static str {
    match c {
        Color::Red => "red",
    }
}

fn main() {
    println!("{} {}", answer(), label(Color::Red));
}
```

```text output
42 red
```

## `parse` returns a `Result`

`"42".parse::<i32>()` is how a string becomes a number. A bad string is
`Err`, so the caller decides what a typo means.

```rust file=n16.rs
fn main() {
    let n: i32 = "42".parse().unwrap();
    let bad = "no".parse::<i32>();
    println!("{n} {}", bad.is_err());
}
```

```text output
42 true
```

## A missing environment variable has a default

`env::var` returns `Err` when the name is unset. `unwrap_or_else`
supplies the fallback at that point.

```rust file=n17.rs
use std::env;

fn main() {
    // SAFETY: this example sets the variable in this process only.
    unsafe { env::set_var("APP_PORT", "8080") };
    let port = env::var("APP_PORT").unwrap_or_else(|_| "80".into());
    let missing = env::var("APP_MISSING").unwrap_or_else(|_| "80".into());
    println!("{port} {missing}");
}
```

```text output
8080 80
```

## Exercises

```rust file=exercise.rs
#![allow(dead_code)] // builder fields are unused until you fill in the stubs

/// "ada lovelace" -> "AL". Skip extra whitespace. Iterators only.
fn initials(_name: &str) -> String {
    todo!()
}

/// Parse every item or fail with a message naming the first bad item:
/// parse_all(&["1", "x"]) == Err("bad item \"x\"").
fn parse_all(_items: &[&str]) -> Result<Vec<i32>, String> {
    todo!()
}

/// Sort descending and remove duplicates.
fn dedupe_sorted_desc(_xs: Vec<i32>) -> Vec<i32> {
    todo!()
}

/// Mean of the values, None when empty.
fn average(_xs: &[f64]) -> Option<f64> {
    todo!()
}

/// Group consecutive equal values: [1,1,2,3,3] -> [[1,1],[2],[3,3]].
fn group_consecutive(_xs: &[i32]) -> Vec<Vec<i32>> {
    todo!()
}

/// A SQL-ish query builder.
/// Query::new("users").order_by("id").limit(5).build()
///   == "SELECT * FROM users ORDER BY id LIMIT 5"
/// Query::new("users").build() == "SELECT * FROM users"
struct Query {
    table: String,
    order: Option<String>,
    limit: Option<u32>,
}

impl Query {
    fn new(_table: impl Into<String>) -> Self {
        todo!()
    }
    fn order_by(self, _column: &str) -> Self {
        todo!()
    }
    fn limit(self, _n: u32) -> Self {
        todo!()
    }
    fn build(&self) -> String {
        todo!()
    }
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
        check("initials", initials("  ada   byron lovelace "), "ABL".to_string()),
        check("parse_all", parse_all(&["1", "2", "3"]), Ok(vec![1, 2, 3])),
        check("parse_all bad", parse_all(&["1", "x", "y"]), Err("bad item \"x\"".to_string())),
        check("dedupe", dedupe_sorted_desc(vec![3, 1, 3, 2, 1]), vec![3, 2, 1]),
        check("average", average(&[1.0, 2.0, 6.0]), Some(3.0)),
        check("average empty", average(&[]), None),
        check(
            "group",
            group_consecutive(&[1, 1, 2, 3, 3]),
            vec![vec![1, 1], vec![2], vec![3, 3]],
        ),
        check("group empty", group_consecutive(&[]), Vec::<Vec<i32>>::new()),
        check(
            "query",
            Query::new("users").order_by("id").limit(5).build(),
            "SELECT * FROM users ORDER BY id LIMIT 5".to_string(),
        ),
        check("query bare", Query::new("users").build(), "SELECT * FROM users".to_string()),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

<details><summary>Solution</summary>

```rust file=solution.rs
fn initials(name: &str) -> String {
    name.split_whitespace()
        .filter_map(|w| w.chars().next())
        .flat_map(|c| c.to_uppercase())
        .collect()
}

fn parse_all(items: &[&str]) -> Result<Vec<i32>, String> {
    items
        .iter()
        .map(|s| s.parse::<i32>().map_err(|_| format!("bad item {s:?}")))
        .collect()
}

fn dedupe_sorted_desc(mut xs: Vec<i32>) -> Vec<i32> {
    xs.sort_unstable_by(|a, b| b.cmp(a));
    xs.dedup();
    xs
}

fn average(xs: &[f64]) -> Option<f64> {
    if xs.is_empty() {
        None
    } else {
        Some(xs.iter().sum::<f64>() / xs.len() as f64)
    }
}

fn group_consecutive(xs: &[i32]) -> Vec<Vec<i32>> {
    let mut groups: Vec<Vec<i32>> = Vec::new();
    for &x in xs {
        match groups.last_mut() {
            Some(g) if g[0] == x => g.push(x),
            _ => groups.push(vec![x]),
        }
    }
    groups
}

struct Query {
    table: String,
    order: Option<String>,
    limit: Option<u32>,
}

impl Query {
    fn new(table: impl Into<String>) -> Self {
        Query { table: table.into(), order: None, limit: None }
    }
    fn order_by(mut self, column: &str) -> Self {
        self.order = Some(column.to_string());
        self
    }
    fn limit(mut self, n: u32) -> Self {
        self.limit = Some(n);
        self
    }
    fn build(&self) -> String {
        let mut sql = format!("SELECT * FROM {}", self.table);
        if let Some(col) = &self.order {
            sql.push_str(&format!(" ORDER BY {col}"));
        }
        if let Some(n) = self.limit {
            sql.push_str(&format!(" LIMIT {n}"));
        }
        sql
    }
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
        check("initials", initials("  ada   byron lovelace "), "ABL".to_string()),
        check("parse_all", parse_all(&["1", "2", "3"]), Ok(vec![1, 2, 3])),
        check("parse_all bad", parse_all(&["1", "x", "y"]), Err("bad item \"x\"".to_string())),
        check("dedupe", dedupe_sorted_desc(vec![3, 1, 3, 2, 1]), vec![3, 2, 1]),
        check("average", average(&[1.0, 2.0, 6.0]), Some(3.0)),
        check("average empty", average(&[]), None),
        check(
            "group",
            group_consecutive(&[1, 1, 2, 3, 3]),
            vec![vec![1, 1], vec![2], vec![3, 3]],
        ),
        check("group empty", group_consecutive(&[]), Vec::<Vec<i32>>::new()),
        check(
            "query",
            Query::new("users").order_by("id").limit(5).build(),
            "SELECT * FROM users ORDER BY id LIMIT 5".to_string(),
        ),
        check("query bare", Query::new("users").build(), "SELECT * FROM users".to_string()),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

</details>

Next: [13 — Testing](13-testing.md)
