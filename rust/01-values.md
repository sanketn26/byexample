# Rust 01 — Values, Variables and Printing

Rust is statically typed, and inference fills in most annotations. Variables
are immutable unless you opt in. Overflow is never a silent wrap, and
numbers do not convert on their own. Every example compiles with
`rustc --edition 2021 -D warnings`.

## Variables are immutable unless you say `mut`

`let` binds a name you cannot assign again. `let mut` opts in. A `const`
needs a type and is inlined at each use. Integer literals default to `i32`
and floats to `f64`; a suffix (`10u64`, `2.5f32`) or an annotation picks
another type.

```rust file=n01.rs
const MAX: u32 = 100;

fn main() {
    let x = 5;
    let mut y = 10;
    y += x;
    println!("{x} {y}");
    println!("{MAX}");
}
```

```text output
5 15
100
```

## A bare `let` must be assigned once

`let x;` declares a name with no value yet. You must assign it exactly once
on every path before it is read.

```rust file=n02.rs
fn main() {
    let x;
    x = 7;
    println!("{x}");
}
```

```text output
7
```

## Shadowing creates a new variable

A second `let` of the same name hides the first. The new binding may have a
different type. The old one is gone.

```rust file=n03.rs
fn main() {
    let spaces = "   ";
    let spaces = spaces.len();
    println!("{spaces}");
}
```

```text output
3
```

## Scalars are the small built-in types

`i32` and `u8` are integers, `f64` is a float, `bool` is `true` or `false`.
A `char` is one Unicode scalar value, four bytes wide, and it is not a
`u8`. A `&str` is UTF-8 bytes, not a slice of `char`.

```rust file=n04.rs
fn main() {
    let a: i32 = -42;
    let b: u8 = 255;
    let c: f64 = 3.14;
    let d: bool = true;
    let e: char = 'é';
    println!("{a} {b} {c} {d} {e}");
    println!("{} {}", std::mem::size_of::<char>(), std::mem::size_of::<i64>());
}
```

```text output
-42 255 3.14 true é
4 8
```

## Overflow is a method you choose

In a debug build, `+` on integers panics when the result does not fit. In a
release build that same `+` wraps. Call `checked_*`, `wrapping_*`,
`saturating_*`, or `overflowing_*` when the behaviour is part of the
program, not an accident of the build mode.

```rust file=n05.rs
fn main() {
    let b: u8 = 255;
    println!(
        "{:?} {:?} {} {}",
        b.checked_add(1),
        200u8.checked_add(55),
        b.wrapping_add(1),
        b.saturating_add(1)
    );
}
```

```text output
None Some(255) 0 255
```

## Division truncates toward zero

`/` and `%` on integers throw away the fraction toward zero, so `-7 / 2` is
`-3` and `-7 % 3` is `-1`. That remainder is not the mathematical modulo.
`rem_euclid` is the non-negative one.

```rust file=n06.rs
fn main() {
    println!("{} {} {} {}", 7 / 2, -7 / 2, -7 % 3, (-7i32).rem_euclid(3));
}
```

```text output
3 -3 -1 2
```

## `as` casts and can lose the value

`as` always compiles and always produces a number. It truncates integers
and saturates floats. A value that does not fit becomes something else
with no error: `300i32 as u8` is `44`, a huge float becomes `i32::MAX`, and
`NaN` becomes `0`. Prefer `TryFrom` (`u8::try_from(n)`) when the value
might not fit.

```rust file=n07.rs
fn main() {
    let f = 3.99_f64;
    println!("{} {} {}", f as i32, -1i32 as u32, 300i32 as u8);
    println!("{} {}", 1e20_f64 as i32, f64::NAN as i32);
    println!("{:?} {:?}", u8::try_from(44i32).ok(), u8::try_from(300i32).ok());
}
```

```text output
3 4294967295 44
2147483647 0
Some(44) None
```

## Tuples and arrays group fixed values

A tuple can mix types. Destructuring pulls it apart, and `.1` is the second
field. An array has one type and a length that is part of the type.

```rust file=n08.rs
fn main() {
    let t = (1, "two", 3.0);
    let (p, q, r) = t;
    println!("{p} {q} {r:.1} {}", t.1);
    let arr = [1, 2, 3];
    println!("{} {:?}", arr.len(), arr);
}
```

```text output
1 two 3.0 two
3 [1, 2, 3]
```

## Format strings pad, round, and debug

The spec after `:` does the work of `printf`: alignment, padding, precision,
exponents, hex, and binary. `{}` calls `Display`, which you implement
yourself. `{:?}` calls `Debug`, which you can `#[derive]`.

```rust file=n09.rs
fn main() {
    println!("{:>5}|{:<5}|{:^5}|{:05}|{:+}", 42, 42, 42, 42, 42);
    println!("{:.3}|{:8.2}|{:e}|{:x}|{:#b}", 3.14159, 3.14159, 1234.5, 255, 5);
    println!("{:?} {:?}", "hi\n", 'x');
}
```

```text output
   42|42   | 42  |00042|+42
3.142|    3.14|1.2345e3|ff|0b101
"hi\n" 'x'
```

## `()` is a value

The unit type is the empty tuple. Functions that return nothing return
`()`.

```rust file=n10.rs
fn main() {
    let unit = ();
    println!("{unit:?}");
}
```

```text output
()
```

## Floats are binary, and `NaN` breaks equality

`0.1 + 0.2` is not `0.3`. Floats implement `PartialEq` and `PartialOrd`, not
`Eq` or `Ord`, because `NaN` is unordered: `partial_cmp` returns `None`.
Sort with `total_cmp`, which places `NaN` after every finite number.

```rust file=n11.rs
fn main() {
    println!("{}", 0.1 + 0.2);
    println!("{}", f64::NAN.partial_cmp(&1.0).is_none());
    let mut xs = [f64::NAN, 1.0, 0.0];
    xs.sort_by(f64::total_cmp);
    println!("{} {}", xs[0] == 0.0, xs[2].is_nan());
}
```

```text output
0.30000000000000004
true
true true
```

## Parsing returns a `Result`

`"42".parse()` succeeds only when you name the target type. A bad string is
`Err`, not a panic, unless you call `unwrap`.

```rust file=n12.rs
fn main() {
    let n: i32 = "42".parse().unwrap();
    let bad = "x".parse::<i32>();
    println!("{n} {}", bad.is_err());
}
```

```text output
42 true
```

## Exercises

Implement the five functions. The stubs call `todo!()`, which panics until
you replace it.

```rust file=exercise.rs
fn celsius_to_fahrenheit(_c: f64) -> f64 {
    todo!()
}

/// Floor quotient and non-negative remainder for b > 0:
/// div_mod_floor(-7, 2) == (-4, 1).
fn div_mod_floor(_a: i32, _b: i32) -> (i32, i32) {
    todo!()
}

/// The average of two u8 values rounded down, without overflowing.
fn average_u8(_a: u8, _b: u8) -> u8 {
    todo!()
}

/// "negative", "zero" or "positive".
fn describe(_n: i64) -> &'static str {
    todo!()
}

/// Parse `s` as an i32, or return `default` if it is not a valid number.
fn parse_or(_s: &str, _default: i32) -> i32 {
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
        check("c2f 100", celsius_to_fahrenheit(100.0), 212.0),
        check("c2f -40", celsius_to_fahrenheit(-40.0), -40.0),
        check("divmod -7/2", div_mod_floor(-7, 2), (-4, 1)),
        check("divmod 7/2", div_mod_floor(7, 2), (3, 1)),
        check("avg", average_u8(250, 200), 225),
        check("avg small", average_u8(1, 2), 1),
        check("describe", [describe(-3), describe(0), describe(9)], ["negative", "zero", "positive"]),
        check("parse ok", parse_or("42", 0), 42),
        check("parse bad", parse_or("4x2", -1), -1),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

<details><summary>Solution</summary>

```rust file=solution.rs
fn celsius_to_fahrenheit(c: f64) -> f64 {
    c * 9.0 / 5.0 + 32.0
}

fn div_mod_floor(a: i32, b: i32) -> (i32, i32) {
    (a.div_euclid(b), a.rem_euclid(b))
}

fn average_u8(a: u8, b: u8) -> u8 {
    ((a as u16 + b as u16) / 2) as u8
}

fn describe(n: i64) -> &'static str {
    match n {
        i64::MIN..=-1 => "negative",
        0 => "zero",
        _ => "positive",
    }
}

fn parse_or(s: &str, default: i32) -> i32 {
    s.parse().unwrap_or(default)
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
        check("c2f 100", celsius_to_fahrenheit(100.0), 212.0),
        check("c2f -40", celsius_to_fahrenheit(-40.0), -40.0),
        check("divmod -7/2", div_mod_floor(-7, 2), (-4, 1)),
        check("divmod 7/2", div_mod_floor(7, 2), (3, 1)),
        check("avg", average_u8(250, 200), 225),
        check("avg small", average_u8(1, 2), 1),
        check("describe", [describe(-3), describe(0), describe(9)], ["negative", "zero", "positive"]),
        check("parse ok", parse_or("42", 0), 42),
        check("parse bad", parse_or("4x2", -1), -1),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

</details>

Next: [02 — Control flow](02-control-flow.md)
