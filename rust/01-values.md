# Rust 01 — Values, Variables and Printing

Rust is statically typed with strong inference. Variables are **immutable by
default**, integer overflow is never silent, and there are no implicit
numeric conversions.

Every example compiles with `rustc --edition 2021 -D warnings`, so even
warnings are treated as errors.

## Example

```rust file=example.rs
const MAX: u32 = 100; // constants need a type and are inlined

fn main() {
    // Immutable by default; opt in to mutation
    let x = 5;
    let mut y = 10;
    y += x;
    println!("{x} {y}");

    // Shadowing creates a NEW variable (and may change the type)
    let spaces = "   ";
    let spaces = spaces.len();
    println!("{spaces}");

    // Scalar types
    let a: i32 = -42;
    let b: u8 = 255;
    let c: f64 = 3.14;
    let d: bool = true;
    let e: char = 'é'; // a Unicode scalar value, 4 bytes
    println!("{a} {b} {c} {d} {e}");
    println!("{} {}", std::mem::size_of::<char>(), std::mem::size_of::<i64>());

    // Overflow is explicit: choose the behaviour you want
    println!(
        "{:?} {:?} {} {}",
        b.checked_add(1),
        200u8.checked_add(55),
        b.wrapping_add(1),
        b.saturating_add(1)
    );

    // Integer division truncates; rem_euclid is the mathematical modulo
    println!("{} {} {} {}", 7 / 2, -7 / 2, -7 % 3, (-7i32).rem_euclid(3));

    // `as` is an explicit, sometimes lossy, cast
    let f = 3.99_f64;
    println!("{} {} {}", f as i32, -1i32 as u32, 300i32 as u8);
    println!("{} {}", 1e20_f64 as i32, f64::NAN as i32); // saturates / zero

    // Tuples and arrays
    let t = (1, "two", 3.0);
    let (p, q, r) = t;
    println!("{p} {q} {r:.1} {}", t.1);
    let arr = [1, 2, 3];
    println!("{} {:?}", arr.len(), arr);
    println!("{MAX}");

    // Formatting
    println!("{:>5}|{:<5}|{:^5}|{:05}|{:+}", 42, 42, 42, 42, 42);
    println!("{:.3}|{:8.2}|{:e}|{:x}|{:#b}", 3.14159, 3.14159, 1234.5, 255, 5);
    println!("{:?} {:?}", "hi\n", 'x');

    // The unit type is the empty tuple
    let unit = ();
    println!("{unit:?}");

    // Floats are IEEE 754 binary
    println!("{}", 0.1 + 0.2);

    // Parsing returns Result: failure is a value
    let n: i32 = "42".parse().unwrap();
    let bad = "x".parse::<i32>();
    println!("{n} {}", bad.is_err());
}
```

```text output
5 15
3
-42 255 3.14 true é
4 8
None Some(255) 0 255
3 -3 -1 2
3 4294967295 44
2147483647 0
1 two 3.0 two
3 [1, 2, 3]
100
   42|42   | 42  |00042|+42
3.142|    3.14|1.2345e3|ff|0b101
"hi\n" 'x'
()
0.30000000000000004
42 true
```

## Details that bite

- In debug builds an overflowing `+` **panics**; in release builds it wraps.
  Use `checked_*`, `wrapping_*`, `saturating_*` or `overflowing_*` when
  the intent matters.
- `as` never fails but can silently truncate or saturate; prefer
  `i32::try_from(x)` when the value might not fit.
- `char` is 4 bytes and is not a `u8`. A `&str` is UTF-8 bytes (lesson 05).
- `-7 % 3` is `-1` (remainder), not `2`. Use `rem_euclid` for modulo.
- `{:?}` is the debug format (derivable); `{}` is the user-facing
  `Display`, which you must implement yourself.
- Floats do not implement `Eq` or `Ord`, only `PartialEq`/`PartialOrd`,
  because of `NaN`. Use `total_cmp` to sort them.
- Integer literals default to `i32`, floats to `f64`; add a suffix
  (`10u64`, `2.5f32`) or an annotation to choose.
- `let x;` without a value is allowed, but must be assigned exactly once
  before use.

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
