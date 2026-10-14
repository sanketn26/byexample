# Rust 09 — Traits and Generics

Traits describe shared behaviour. Generics with trait bounds give you
zero-cost static dispatch; `dyn Trait` gives you runtime polymorphism when
you need a heterogeneous collection.

## Example

```rust file=example.rs
use std::fmt::{self, Display};
use std::ops::{Add, Mul};

// A trait with a required and a default method
trait Shape {
    fn area(&self) -> f64;

    fn name(&self) -> String {
        "shape".to_string()
    }

    fn describe(&self) -> String {
        format!("{} {:.2}", self.name(), self.area())
    }
}

struct Circle(f64);
struct Square(f64);

impl Shape for Circle {
    fn area(&self) -> f64 {
        std::f64::consts::PI * self.0 * self.0
    }
    fn name(&self) -> String {
        "circle".to_string()
    }
}

impl Shape for Square {
    fn area(&self) -> f64 {
        self.0 * self.0
    }
}

// Static dispatch: monomorphised, no runtime cost
fn print_it(s: &impl Shape) -> String {
    s.describe()
}

// Dynamic dispatch: a heterogeneous collection behind a vtable
fn total_area(shapes: &[Box<dyn Shape>]) -> f64 {
    shapes.iter().map(|s| s.area()).sum()
}

// Operator overloading is just trait implementation
#[derive(Debug, Clone, Copy, PartialEq)]
struct V2 {
    x: i32,
    y: i32,
}

impl Add for V2 {
    type Output = V2;
    fn add(self, o: V2) -> V2 {
        V2 { x: self.x + o.x, y: self.y + o.y }
    }
}

impl Mul<i32> for V2 {
    type Output = V2;
    fn mul(self, k: i32) -> V2 {
        V2 { x: self.x * k, y: self.y * k }
    }
}

// Implementing Iterator gives you map/filter/sum/... for free
struct Countdown(u32);

impl Iterator for Countdown {
    type Item = u32;
    fn next(&mut self) -> Option<u32> {
        if self.0 == 0 {
            None
        } else {
            self.0 -= 1;
            Some(self.0 + 1)
        }
    }
}

// From/Into for conversions
struct Celsius(f64);
struct Fahrenheit(f64);

impl From<Celsius> for Fahrenheit {
    fn from(c: Celsius) -> Self {
        Fahrenheit(c.0 * 9.0 / 5.0 + 32.0)
    }
}

// A generic type with bounds on its methods
struct Stack<T> {
    items: Vec<T>,
}

impl<T: Display> Stack<T> {
    fn render(&self) -> String {
        self.items.iter().map(|i| i.to_string()).collect::<Vec<_>>().join(",")
    }
}

// A blanket impl: every Display type gets .shout()
trait Shout {
    fn shout(&self) -> String;
}

impl<T: Display> Shout for T {
    fn shout(&self) -> String {
        format!("{self}!")
    }
}

// A where clause keeps long bounds readable
fn show_all<T>(items: &[T]) -> String
where
    T: fmt::Debug,
{
    format!("{items:?}")
}

fn main() {
    println!("{} | {}", print_it(&Circle(1.0)), print_it(&Square(2.0)));

    let shapes: Vec<Box<dyn Shape>> = vec![Box::new(Circle(1.0)), Box::new(Square(2.0))];
    println!("{:.2}", total_area(&shapes));

    println!("{:?}", Countdown(3).collect::<Vec<_>>());
    println!("{}", Countdown(5).filter(|n| n % 2 == 1).sum::<u32>());

    let v = V2 { x: 1, y: 2 } + V2 { x: 3, y: 4 } * 2;
    println!("{v:?}");

    let f: Fahrenheit = Celsius(0.0).into();
    println!("{} {}", f.0, Fahrenheit::from(Celsius(100.0)).0);

    let st = Stack { items: vec![1, 2, 3] };
    println!("{}", st.render());

    println!("{} {}", 42.shout(), "hi".shout());
    println!("{}", show_all(&["a", "b"]));
}
```

```text output
circle 3.14 | shape 4.00
7.14
[3, 2, 1]
9
V2 { x: 7, y: 10 }
32 212
1,2,3
42! hi!
["a", "b"]
```

## Details that bite

- **Orphan rule**: you can implement a trait for a type only if you own the
  trait *or* the type. You cannot implement `Display` for `Vec<T>`; wrap
  it in a newtype.
- Not every trait can be a trait object: methods must not be generic or
  return `Self` (object safety).
- `impl Trait` in argument position is sugar for a generic; in return
  position it hides one concrete type. `dyn Trait` is the type-erased,
  pay-for-a-vtable option and must live behind a pointer (`&`, `Box`,
  `Rc`).
- Generics are monomorphised: fast code, bigger binaries.
- Trait methods are only callable when the trait is in scope (`use`).
- Use associated types (`type Item`) when each implementor has one natural
  choice; use generic parameters (`Add<Rhs>`) when many are valid.
- Derive what you can (`Debug`, `Clone`, `PartialEq`, `Default`, `Hash`);
  hand-write only when behaviour differs.
- Lifetimes and trait bounds combine: `T: Display + 'static`,
  `F: Fn(&str) -> &str`.

## Exercises

```rust file=exercise.rs
#![allow(dead_code)] // fields are unused until you implement the stubs
use std::fmt;
use std::ops::{Add, Sub};
use std::str::FromStr;

trait Area {
    fn area(&self) -> f64;
}

struct Circle {
    r: f64,
}

struct Rect {
    w: f64,
    h: f64,
}

// Replace each todo!() below. Circle area is 3.14159 * r * r.
impl Area for Circle {
    fn area(&self) -> f64 {
        todo!()
    }
}

impl Area for Rect {
    fn area(&self) -> f64 {
        todo!()
    }
}

/// Sum the areas of any mix of shapes.
fn total_area(_shapes: &[&dyn Area]) -> f64 {
    todo!()
}

/// Money in cents. Implement Add, Sub and Display ("$12.34", "-$0.50").
#[derive(Debug, Clone, Copy, PartialEq)]
struct Money(i64);

// Replace each todo!() below.
impl Add for Money {
    type Output = Money;
    fn add(self, _o: Money) -> Money {
        todo!()
    }
}

impl Sub for Money {
    type Output = Money;
    fn sub(self, _o: Money) -> Money {
        todo!()
    }
}

impl fmt::Display for Money {
    fn fmt(&self, _f: &mut fmt::Formatter) -> fmt::Result {
        todo!()
    }
}

/// An iterator over the Fibonacci numbers 0, 1, 1, 2, 3, ...
struct Fib {
    a: u64,
    b: u64,
}

impl Fib {
    fn new() -> Self {
        Fib { a: 0, b: 1 }
    }
}

impl Iterator for Fib {
    type Item = u64;
    fn next(&mut self) -> Option<u64> {
        todo!()
    }
}

/// The element with the largest key, None when empty (first one wins ties).
fn max_by_key_generic<T, K: PartialOrd>(_xs: &[T], _key: impl Fn(&T) -> K) -> Option<&T> {
    todo!()
}

#[derive(Debug, PartialEq)]
struct Point {
    x: i32,
    y: i32,
}

// "3,4".parse::<Point>() must work (Err = String), and so must
// Point::from((3, 4)).
impl FromStr for Point {
    type Err = String;
    fn from_str(_s: &str) -> Result<Self, String> {
        todo!()
    }
}

impl From<(i32, i32)> for Point {
    fn from(_t: (i32, i32)) -> Self {
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
    let c = Circle { r: 1.0 };
    let r = Rect { w: 2.0, h: 3.0 };
    let total = total_area(&[&c, &r]);
    let results = [
        check("total area", (total * 1000.0).round(), 9142.0),
        check("money add", (Money(150) + Money(275)).0, 425),
        check("money sub", (Money(100) - Money(150)).0, -50),
        check("money display", format!("{} {}", Money(1234), Money(-50)), "$12.34 -$0.50".to_string()),
        check("fib", Fib::new().take(10).collect::<Vec<_>>(), vec![0, 1, 1, 2, 3, 5, 8, 13, 21, 34]),
        check("fib adaptors", Fib::new().filter(|n| n % 2 == 0).take(4).sum::<u64>(), 44),
        check("max_by_key", max_by_key_generic(&["aa", "b", "cccc", "dd"], |s| s.len()), Some(&"cccc")),
        check("max_by_key empty", max_by_key_generic(&[] as &[i32], |x| *x), None),
        check("parse point", "3,4".parse::<Point>(), Ok(Point { x: 3, y: 4 })),
        check("parse point bad", "3;4".parse::<Point>().is_err(), true),
        check("from tuple", Point::from((1, 2)), Point { x: 1, y: 2 }),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

<details><summary>Solution</summary>

```rust file=solution.rs
use std::fmt;
use std::ops::{Add, Sub};
use std::str::FromStr;

trait Area {
    fn area(&self) -> f64;
}

struct Circle {
    r: f64,
}

struct Rect {
    w: f64,
    h: f64,
}

impl Area for Circle {
    fn area(&self) -> f64 {
        3.14159 * self.r * self.r
    }
}

impl Area for Rect {
    fn area(&self) -> f64 {
        self.w * self.h
    }
}

fn total_area(shapes: &[&dyn Area]) -> f64 {
    shapes.iter().map(|s| s.area()).sum()
}

#[derive(Debug, Clone, Copy, PartialEq)]
struct Money(i64);

impl Add for Money {
    type Output = Money;
    fn add(self, o: Money) -> Money {
        Money(self.0 + o.0)
    }
}

impl Sub for Money {
    type Output = Money;
    fn sub(self, o: Money) -> Money {
        Money(self.0 - o.0)
    }
}

impl fmt::Display for Money {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        let sign = if self.0 < 0 { "-" } else { "" };
        let abs = self.0.abs();
        write!(f, "{sign}${}.{:02}", abs / 100, abs % 100)
    }
}

struct Fib {
    a: u64,
    b: u64,
}

impl Fib {
    fn new() -> Self {
        Fib { a: 0, b: 1 }
    }
}

impl Iterator for Fib {
    type Item = u64;
    fn next(&mut self) -> Option<u64> {
        let out = self.a;
        (self.a, self.b) = (self.b, self.a + self.b);
        Some(out)
    }
}

fn max_by_key_generic<T, K: PartialOrd>(xs: &[T], key: impl Fn(&T) -> K) -> Option<&T> {
    let mut best: Option<(&T, K)> = None;
    for x in xs {
        let k = key(x);
        match &best {
            Some((_, bk)) if !(k > *bk) => {}
            _ => best = Some((x, k)),
        }
    }
    best.map(|(x, _)| x)
}

#[derive(Debug, PartialEq)]
struct Point {
    x: i32,
    y: i32,
}

impl FromStr for Point {
    type Err = String;
    fn from_str(s: &str) -> Result<Self, String> {
        let (a, b) = s.split_once(',').ok_or("expected x,y")?;
        Ok(Point {
            x: a.trim().parse().map_err(|e| format!("x: {e}"))?,
            y: b.trim().parse().map_err(|e| format!("y: {e}"))?,
        })
    }
}

impl From<(i32, i32)> for Point {
    fn from((x, y): (i32, i32)) -> Self {
        Point { x, y }
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
    let c = Circle { r: 1.0 };
    let r = Rect { w: 2.0, h: 3.0 };
    let total = total_area(&[&c, &r]);
    let results = [
        check("total area", (total * 1000.0).round(), 9142.0),
        check("money add", (Money(150) + Money(275)).0, 425),
        check("money sub", (Money(100) - Money(150)).0, -50),
        check("money display", format!("{} {}", Money(1234), Money(-50)), "$12.34 -$0.50".to_string()),
        check("fib", Fib::new().take(10).collect::<Vec<_>>(), vec![0, 1, 1, 2, 3, 5, 8, 13, 21, 34]),
        check("fib adaptors", Fib::new().filter(|n| n % 2 == 0).take(4).sum::<u64>(), 44),
        check("max_by_key", max_by_key_generic(&["aa", "b", "cccc", "dd"], |s| s.len()), Some(&"cccc")),
        check("max_by_key empty", max_by_key_generic(&[] as &[i32], |x| *x), None),
        check("parse point", "3,4".parse::<Point>(), Ok(Point { x: 3, y: 4 })),
        check("parse point bad", "3;4".parse::<Point>().is_err(), true),
        check("from tuple", Point::from((1, 2)), Point { x: 1, y: 2 }),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

</details>

Next: [10 — Files and I/O](10-files-io.md)
