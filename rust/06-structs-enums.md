# Rust 06 — Structs, Enums and Pattern Matching

Structs hold data, `impl` blocks add methods, and enums are *sum types*:
each variant can carry different data. `Option` and `Result` are just
enums.

## Example

```rust file=example.rs
use std::f64::consts::PI;
use std::fmt;

#[derive(Debug, Clone, PartialEq, Default)]
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    // Associated function (no self): the usual constructor
    fn new(x: f64, y: f64) -> Self {
        Point { x, y }
    }

    // &self: read-only borrow
    fn dist(&self, other: &Point) -> f64 {
        ((self.x - other.x).powi(2) + (self.y - other.y).powi(2)).sqrt()
    }

    // &mut self: exclusive borrow
    fn scale(&mut self, k: f64) {
        self.x *= k;
        self.y *= k;
    }

    // self: consumes the value
    fn into_tuple(self) -> (f64, f64) {
        (self.x, self.y)
    }
}

impl fmt::Display for Point {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "({}, {})", self.x, self.y)
    }
}

#[derive(Debug)]
enum Shape {
    Circle { r: f64 },
    Rect { w: f64, h: f64 },
    Triangle(f64, f64, f64),
}

impl Shape {
    fn area(&self) -> f64 {
        match self {
            Shape::Circle { r } => PI * r * r,
            Shape::Rect { w, h } => w * h,
            Shape::Triangle(a, b, c) => {
                let s = (a + b + c) / 2.0;
                (s * (s - a) * (s - b) * (s - c)).sqrt()
            }
        }
    }
}

// Newtype: a distinct type with zero runtime cost
struct Meters(f64);

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
enum Level {
    Low = 1,
    Mid,
    High,
}

#[derive(Debug, Default, Clone)]
struct Config {
    name: String,
    retries: u32,
    verbose: bool,
}

fn main() {
    let mut p = Point::new(3.0, 4.0);
    println!("{p} {:.1}", p.dist(&Point::default()));
    p.scale(2.0);
    println!("{p} {:?}", p);
    let q = p.clone();
    println!("{}", p == q);
    println!("{:?}", p.into_tuple());

    let shapes = [
        Shape::Circle { r: 1.0 },
        Shape::Rect { w: 3.0, h: 4.0 },
        Shape::Triangle(3.0, 4.0, 5.0),
    ];
    for s in &shapes {
        print!("{:.2} ", s.area());
    }
    println!();
    println!("{:?}", Shape::Rect { w: 1.0, h: 2.0 });

    let m = Meters(5.0);
    println!("{}", m.0);
    println!("{} {}", Level::Mid as i32, Level::Low < Level::High);

    // Struct update syntax
    let base = Config {
        name: "base".into(),
        retries: 3,
        ..Default::default()
    };
    let custom = Config {
        verbose: true,
        ..base.clone()
    };
    if custom.verbose {
        println!("{} x{}", custom.name, custom.retries);
    }
    println!("{base:?}");

    // Option is just an enum
    let found: Option<&str> = None;
    println!("{}", found.map_or("none".to_string(), |s| s.to_uppercase()));
}
```

```text output
(3, 4) 5.0
(6, 8) Point { x: 6.0, y: 8.0 }
true
(6.0, 8.0)
3.14 12.00 6.00 
Rect { w: 1.0, h: 2.0 }
5
2 true
base x3
Config { name: "base", retries: 3, verbose: false }
none
```

## Details that bite

- `#[derive(...)]` generates trait impls: `Debug`, `Clone`, `Copy`,
  `PartialEq`, `Eq`, `PartialOrd`, `Ord`, `Hash`, `Default`. `Copy`
  requires every field to be `Copy`.
- Fields are private to their module by default; `pub` opens them.
  Privacy is by module, not by type.
- Struct update (`..base`) *moves* any non-`Copy` fields out of `base`;
  clone it first if you still need it.
- `match` on an enum is exhaustive. Adding a variant breaks every match
  that lacks a `_` arm — which is the feature.
- Unit-only enums cast to integers with `as`; the reverse needs a
  `TryFrom` implementation or a match.
- There is no inheritance. Share behaviour with traits (lesson 09) and
  composition.
- Large enums are as big as their largest variant; `Box` the big one if
  size matters.
- Prefer `Option<T>` to sentinel values like `-1` or empty strings.

## Exercises

```rust file=exercise.rs
#![allow(dead_code)] // the stubs below do not use their fields yet

/// A LIFO stack of i32.
struct Stack {
    items: Vec<i32>,
}

impl Stack {
    fn new() -> Self {
        todo!()
    }
    fn push(&mut self, _v: i32) {
        todo!()
    }
    fn pop(&mut self) -> Option<i32> {
        todo!()
    }
    fn peek(&self) -> Option<&i32> {
        todo!()
    }
    fn len(&self) -> usize {
        todo!()
    }
    fn is_empty(&self) -> bool {
        todo!()
    }
}

#[derive(Debug, PartialEq)]
struct Rect {
    w: f64,
    h: f64,
}

impl Rect {
    fn area(&self) -> f64 {
        todo!()
    }
    fn perimeter(&self) -> f64 {
        todo!()
    }
    /// Returns a new Rect scaled by k; the original is unchanged.
    fn scaled(&self, _k: f64) -> Rect {
        todo!()
    }
}

#[derive(Debug, Clone, Copy)]
enum Temperature {
    Celsius(f64),
    Fahrenheit(f64),
}

impl Temperature {
    fn to_celsius(self) -> f64 {
        todo!()
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum Light {
    Red,
    Green,
    Yellow,
}

impl Light {
    /// Red -> Green -> Yellow -> Red
    fn next(self) -> Light {
        todo!()
    }
    /// Seconds the light stays on: Red 30, Green 25, Yellow 5.
    fn seconds(self) -> u32 {
        todo!()
    }
}

#[derive(Debug, PartialEq)]
enum Command {
    Move { dx: i32, dy: i32 },
    Say(String),
    Quit,
}

/// "move 1 -2" | "say hello world" | "quit" ; anything else is None.
fn parse_command(_line: &str) -> Option<Command> {
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
    let mut s = Stack::new();
    let empty_before = s.is_empty();
    s.push(1);
    s.push(2);
    let top = s.peek().copied();
    let popped = s.pop();
    let r = Rect { w: 2.0, h: 3.0 };
    let results = [
        check("stack empty", empty_before, true),
        check("stack peek", top, Some(2)),
        check("stack pop", (popped, s.len()), (Some(2), 1)),
        check("stack empty pop", Stack::new().pop(), None),
        check("rect", (r.area(), r.perimeter()), (6.0, 10.0)),
        check("rect scaled", r.scaled(2.0), Rect { w: 4.0, h: 6.0 }),
        check("celsius", Temperature::Celsius(20.0).to_celsius(), 20.0),
        check("fahrenheit", Temperature::Fahrenheit(212.0).to_celsius(), 100.0),
        check("light next", Light::Yellow.next(), Light::Red),
        check("light seconds", Light::Green.seconds(), 25),
        check("cmd move", parse_command("move 1 -2"), Some(Command::Move { dx: 1, dy: -2 })),
        check("cmd say", parse_command("say hello world"), Some(Command::Say("hello world".into()))),
        check("cmd quit", parse_command("quit"), Some(Command::Quit)),
        check("cmd bad", parse_command("jump"), None),
        check("cmd bad args", parse_command("move x y"), None),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

<details><summary>Solution</summary>

```rust file=solution.rs
struct Stack {
    items: Vec<i32>,
}

impl Stack {
    fn new() -> Self {
        Stack { items: Vec::new() }
    }
    fn push(&mut self, v: i32) {
        self.items.push(v);
    }
    fn pop(&mut self) -> Option<i32> {
        self.items.pop()
    }
    fn peek(&self) -> Option<&i32> {
        self.items.last()
    }
    fn len(&self) -> usize {
        self.items.len()
    }
    fn is_empty(&self) -> bool {
        self.items.is_empty()
    }
}

#[derive(Debug, PartialEq)]
struct Rect {
    w: f64,
    h: f64,
}

impl Rect {
    fn area(&self) -> f64 {
        self.w * self.h
    }
    fn perimeter(&self) -> f64 {
        2.0 * (self.w + self.h)
    }
    fn scaled(&self, k: f64) -> Rect {
        Rect { w: self.w * k, h: self.h * k }
    }
}

#[derive(Debug, Clone, Copy)]
enum Temperature {
    Celsius(f64),
    Fahrenheit(f64),
}

impl Temperature {
    fn to_celsius(self) -> f64 {
        match self {
            Temperature::Celsius(c) => c,
            Temperature::Fahrenheit(f) => (f - 32.0) * 5.0 / 9.0,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum Light {
    Red,
    Green,
    Yellow,
}

impl Light {
    fn next(self) -> Light {
        match self {
            Light::Red => Light::Green,
            Light::Green => Light::Yellow,
            Light::Yellow => Light::Red,
        }
    }
    fn seconds(self) -> u32 {
        match self {
            Light::Red => 30,
            Light::Green => 25,
            Light::Yellow => 5,
        }
    }
}

#[derive(Debug, PartialEq)]
enum Command {
    Move { dx: i32, dy: i32 },
    Say(String),
    Quit,
}

fn parse_command(line: &str) -> Option<Command> {
    let (verb, rest) = line.split_once(' ').unwrap_or((line, ""));
    match verb {
        "quit" if rest.is_empty() => Some(Command::Quit),
        "say" if !rest.is_empty() => Some(Command::Say(rest.to_string())),
        "move" => {
            let mut it = rest.split_whitespace();
            let dx = it.next()?.parse().ok()?;
            let dy = it.next()?.parse().ok()?;
            Some(Command::Move { dx, dy })
        }
        _ => None,
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
    let mut s = Stack::new();
    let empty_before = s.is_empty();
    s.push(1);
    s.push(2);
    let top = s.peek().copied();
    let popped = s.pop();
    let r = Rect { w: 2.0, h: 3.0 };
    let results = [
        check("stack empty", empty_before, true),
        check("stack peek", top, Some(2)),
        check("stack pop", (popped, s.len()), (Some(2), 1)),
        check("stack empty pop", Stack::new().pop(), None),
        check("rect", (r.area(), r.perimeter()), (6.0, 10.0)),
        check("rect scaled", r.scaled(2.0), Rect { w: 4.0, h: 6.0 }),
        check("celsius", Temperature::Celsius(20.0).to_celsius(), 20.0),
        check("fahrenheit", Temperature::Fahrenheit(212.0).to_celsius(), 100.0),
        check("light next", Light::Yellow.next(), Light::Red),
        check("light seconds", Light::Green.seconds(), 25),
        check("cmd move", parse_command("move 1 -2"), Some(Command::Move { dx: 1, dy: -2 })),
        check("cmd say", parse_command("say hello world"), Some(Command::Say("hello world".into()))),
        check("cmd quit", parse_command("quit"), Some(Command::Quit)),
        check("cmd bad", parse_command("jump"), None),
        check("cmd bad args", parse_command("move x y"), None),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

</details>

Next: [07 — Errors](07-errors.md)
