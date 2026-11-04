# Rust 06 — Structs, Enums and Pattern Matching

A struct holds fields together. An `impl` block adds functions and methods.
An enum is a sum type: each variant can carry different data. `Option` and
`Result` are enums from the standard library, not special syntax.

## Methods borrow, or they consume

`Point::new` is an associated function: no `self`. `&self` reads, `&mut self`
changes, and `self` takes ownership so the value cannot be used again.
`#[derive]` writes `Debug`, `Clone`, `PartialEq`, and `Default` for you.
`Copy` is only available when every field is `Copy`.

```rust file=n01.rs
#[derive(Debug, Clone, PartialEq, Default)]
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    fn new(x: f64, y: f64) -> Self {
        Point { x, y }
    }

    fn dist(&self, other: &Point) -> f64 {
        ((self.x - other.x).powi(2) + (self.y - other.y).powi(2)).sqrt()
    }

    fn scale(&mut self, k: f64) {
        self.x *= k;
        self.y *= k;
    }

    fn into_tuple(self) -> (f64, f64) {
        (self.x, self.y)
    }
}

fn main() {
    let mut p = Point::new(3.0, 4.0);
    println!("{:.1}", p.dist(&Point::default()));
    p.scale(2.0);
    let q = p.clone();
    println!("{} {:?}", p == q, p.into_tuple());
}
```

```text output
5.0
true (6.0, 8.0)
```

## `Display` is what `{}` prints

`Debug` (`{:?}`) is the derived dump. `Display` is the text you write for
people, and nothing derives it for you.

```rust file=n02.rs
use std::fmt;

#[derive(Debug)]
struct Point {
    x: f64,
    y: f64,
}

impl fmt::Display for Point {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "({}, {})", self.x, self.y)
    }
}

fn main() {
    let p = Point { x: 3.0, y: 4.0 };
    println!("{p} {p:?}");
}
```

```text output
(3, 4) Point { x: 3.0, y: 4.0 }
```

## Fields are private to the module

Privacy follows the module, not the type. A field without `pub` is visible
in the same module and hidden from every other one. Methods on the type are
how other modules are supposed to reach it.

```rust file=n03.rs
mod geo {
    pub struct Point {
        x: f64,
    }

    impl Point {
        pub fn new(x: f64) -> Self {
            Point { x }
        }

        pub fn x(&self) -> f64 {
            self.x
        }
    }
}

fn main() {
    let p = geo::Point::new(3.0);
    println!("{}", p.x());
}
```

```text output
3
```

## An enum carries different data per variant

`match` on an enum is exhaustive. Add a variant and every match that has no
`_` arm stops compiling. That is the feature. There is no inheritance.
Share behaviour with traits (lesson 09) and with composition.

```rust file=n04.rs
use std::f64::consts::PI;

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

fn main() {
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
}
```

```text output
3.14 12.00 6.00 
Rect { w: 1.0, h: 2.0 }
```

## A big variant sets the size of the enum

Every value of an enum is as large as the largest variant, plus a tag.
`Box` the big payload when most values are the small ones.

```rust file=n05.rs
enum Big {
    Small(u8),
    Large([u8; 64]),
}

enum Boxed {
    Small(u8),
    Large(Box<[u8; 64]>),
}

fn main() {
    let small = Big::Small(1);
    let wide = Big::Large([0; 64]);
    let slim_small = Boxed::Small(2);
    let slim = Boxed::Large(Box::new([7; 64]));
    let tag = match small {
        Big::Small(n) => n as usize,
        Big::Large(buf) => buf.len(),
    };
    let n = match wide {
        Big::Large(buf) => buf.len(),
        Big::Small(n) => n as usize,
    };
    let other = match slim_small {
        Boxed::Small(n) => n,
        Boxed::Large(buf) => buf[0],
    };
    let first = match slim {
        Boxed::Large(buf) => buf[0],
        Boxed::Small(n) => n,
    };
    println!(
        "{} {} {tag} {n} {other} {first}",
        std::mem::size_of::<Big>(),
        std::mem::size_of::<Boxed>()
    );
}
```

```text output
65 16 1 64 2 7
```

## A newtype is a different type at no runtime cost

`Meters` is not an `f64`. You cannot pass one where the other is required,
and the wrapper disappears in the generated code. Reach for it instead of a
bare number when the unit matters.

```rust file=n06.rs
struct Meters(f64);

fn main() {
    let m = Meters(5.0);
    println!("{}", m.0);
}
```

```text output
5
```

## A fieldless enum casts one way

`as` turns `Level::Mid` into an integer. The other direction is not a cast.
Write a `match`, or implement `TryFrom`. `Copy` here is free because every
variant is empty.

```rust file=n07.rs
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
enum Level {
    Low = 1,
    Mid,
    High,
}

fn from_i32(n: i32) -> Option<Level> {
    match n {
        1 => Some(Level::Low),
        2 => Some(Level::Mid),
        3 => Some(Level::High),
        _ => None,
    }
}

fn main() {
    let mid = Level::Mid;
    let copy = mid;
    println!("{} {} {:?}", mid as i32, Level::Low < Level::High, from_i32(copy as i32));
}
```

```text output
2 true Some(Mid)
```

## `..base` moves non-`Copy` fields

Struct update copies the fields you do not name. A `String` is not `Copy`,
so `..base` moves it out of `base`. Clone first when you still need the
original. `Default` fills whatever you do not set.

```rust file=n08.rs
#[derive(Debug, Default, Clone)]
struct Config {
    name: String,
    retries: u32,
    verbose: bool,
}

fn main() {
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
}
```

```text output
base x3
Config { name: "base", retries: 3, verbose: false }
```

## Prefer `Option` to a sentinel

`None` means absent. `-1` or `""` means absent only by a comment, and both
are easy to mix up with real data.

```rust file=n09.rs
fn main() {
    let found: Option<&str> = None;
    println!("{}", found.map_or("none".to_string(), |s| s.to_uppercase()));
}
```

```text output
none
```

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
