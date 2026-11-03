# Rust 12 — Idiomatic Rust

Idiomatic Rust leans on the type system: iterators instead of index loops,
`Option`/`Result` combinators instead of sentinel values, ownership in
signatures that say what they mean, and types that make invalid states
unrepresentable. Most of this is what `cargo clippy` nudges you towards.

## Example

```rust file=example.rs
use std::collections::HashMap;
use std::fmt;
use std::marker::PhantomData;

// 1. Iterator pipelines instead of manual index loops
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

// 2. Accept the most general borrowed type: &str, &[T], not &String, &Vec<T>
fn count_a(s: &str) -> usize {
    s.chars().filter(|&c| c == 'a').count()
}

// 3. Option combinators instead of nested matches
fn user_domain(email: Option<&str>) -> String {
    email
        .and_then(|e| e.split_once('@'))
        .map(|(_, d)| d.to_lowercase())
        .unwrap_or_else(|| "unknown".to_string())
}

// 4. `?` instead of match-and-return
fn parse_sum(a: &str, b: &str) -> Result<i32, std::num::ParseIntError> {
    Ok(a.parse::<i32>()? + b.parse::<i32>()?)
}

// 5. let-else keeps the happy path unindented
fn first_char_upper(s: &str) -> String {
    let Some(c) = s.chars().next() else {
        return String::new();
    };
    c.to_uppercase().collect()
}

// 6. The entry API instead of get/insert dances
fn count_chars(s: &str) -> HashMap<char, usize> {
    let mut m = HashMap::new();
    for c in s.chars() {
        *m.entry(c).or_insert(0) += 1;
    }
    m
}

// 7. Builder with `impl Into<String>` and Default
#[derive(Debug, Default)]
struct Request {
    url: String,
    method: String,
    retries: u32,
}

impl Request {
    fn new(url: impl Into<String>) -> Self {
        Request { url: url.into(), method: "GET".into(), ..Default::default() }
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

// 8. Newtypes + From make units explicit
struct Meters(f64);
struct Feet(f64);

impl From<Feet> for Meters {
    fn from(f: Feet) -> Self {
        Meters(f.0 * 0.3048)
    }
}

// 9. Type-state: invalid transitions do not compile
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

// 10. Implement Display instead of ad-hoc to_string functions
struct Pt(i32, i32);

impl fmt::Display for Pt {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "({}, {})", self.0, self.1)
    }
}

fn main() {
    let xs = [1, 2, 3, 4];
    println!("1 {} {}", sum_even_squares_c_style(&xs), sum_even_squares(&xs));
    println!("2 {}", count_a("banana"));
    println!("3 {} {}", user_domain(Some("Ann@Example.com")), user_domain(None));
    println!("4 {:?} {}", parse_sum("3", "4"), parse_sum("3", "x").is_err());
    println!("5 {:?} {:?}", first_char_upper("hello"), first_char_upper(""));

    let mut counts: Vec<_> = count_chars("banana").into_iter().collect();
    counts.sort();
    println!("6 {counts:?}");

    let req = Request::new("http://x").method("POST").retries(3);
    println!("7 {:?} {}", req, req.describe());
    println!("8 {:.3}", Meters::from(Feet(10.0)).0);
    println!("9 {}", Door::new().open().close().open().walk_through());
    println!("10 {} {}", Pt(1, 2), Pt(1, 2).to_string().len());

    // 11. collect() builds whatever you ask for
    let lens: HashMap<&str, usize> = ["a", "bb"].iter().map(|w| (*w, w.len())).collect();
    let joined: String = ['h', 'i'].iter().collect();
    let opt = ["1", "2"].iter().map(|s| s.parse().ok()).collect::<Option<Vec<i32>>>();
    println!("11 {joined} {opt:?} {}", lens["bb"]);

    // 12. position / any / all
    let odds = [1, 5, 9];
    println!(
        "12 {:?} {} {}",
        odds.iter().position(|&x| x == 5),
        odds.iter().any(|&x| x > 8),
        odds.iter().all(|&x| x % 2 == 1)
    );

    // 13. mem::take moves a value out of a &mut, leaving Default behind
    let mut name = String::from("x");
    let old = std::mem::take(&mut name);
    println!("13 {old:?} {name:?}");

    // 14. sort_by_key with a tuple key and Reverse
    let mut people = vec![("Al", 30), ("Bo", 25), ("Cy", 30)];
    people.sort_by_key(|&(name, age)| (std::cmp::Reverse(age), name));
    println!("14 {people:?}");
}
```

```text output
1 20 20
2 3
3 example.com unknown
4 Ok(7) true
5 "H" ""
6 [('a', 3), ('b', 1), ('n', 2)]
7 Request { url: "http://x", method: "POST", retries: 3 } POST http://x x3
8 3.048
9 through the open door
10 (1, 2) 6
11 hi Some([1, 2]) 2
12 Some(1) true true
13 "x" ""
14 [("Al", 30), ("Cy", 30), ("Bo", 25)]
```

## The checklist

| Instead of | Write |
|------------|-------|
| `for i in 0..v.len() { v[i] }` | `for x in &v` / `iter().enumerate()` |
| `fn f(s: &String)`, `fn f(v: &Vec<T>)` | `fn f(s: &str)`, `fn f(v: &[T])` |
| `if x.is_some() { x.unwrap() }` | `if let Some(x) = x` |
| `match opt { Some(x) => Some(f(x)), None => None }` | `opt.map(f)` |
| `return Err(e)` after a match | `?` |
| `x.clone()` to silence the borrow checker | restructure, or borrow smaller |
| `unwrap()` in library code | return `Result`/`Option` |
| `String` params you only read | `&str` (or `impl AsRef<str>`) |
| `Box<dyn Trait>` everywhere | generics (`impl Trait`) unless you need dynamic dispatch |
| Sentinel values (`-1`, `""`) | `Option<T>` |
| Stringly-typed enums and flags | `enum` with `match` |
| Manual `Default`/`Debug`/`PartialEq` | `#[derive(...)]` |
| Public fields guarded by comments | private fields + constructor |
| Many `bool` parameters | an enum or options struct |
| `&mut` out-parameters | return a tuple or struct |
| Long functions with comments as headings | small functions with names |
| `as` casts for fallible conversions | `try_from` / `try_into` |

## Details that bite

- `cargo fmt` and `cargo clippy -- -D warnings` are the community's shared
  style guide. Run both in CI.
- Prefer composition and traits over deep generics; a generic function
  with six type parameters is a sign to introduce a struct or a trait.
- Make illegal states unrepresentable (enums with data instead of a struct
  of `Option`s), and push validation into constructors (`parse, don't
  validate`).
- Document with `///` comments; code blocks inside them are compiled and
  run by `cargo test` (doctests), so examples never go stale.
- `#[must_use]`, `#[non_exhaustive]` and `pub(crate)` keep APIs
  honest and small.
- Use crates for what the standard library deliberately omits: `serde`,
  `clap`, `anyhow`/`thiserror`, `tokio`, `rayon`, `itertools`.
- Clippy is sometimes wrong; `#[allow(clippy::lint)]` with a comment
  explaining why is fine.

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
