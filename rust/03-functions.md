# Rust 03 — Functions and Closures

Functions are declared with `fn`, parameter and return types are always
written out, and the last expression (without a semicolon) is the return
value. Closures capture their environment and come in three flavours:
`Fn`, `FnMut` and `FnOnce`.

## Example

```rust file=example.rs
fn add(a: i32, b: i32) -> i32 {
    a + b // no semicolon: this is the return value
}

fn divmod(a: i32, b: i32) -> (i32, i32) {
    (a / b, a % b)
}

// Borrow a slice instead of taking ownership of a Vec
fn sum(xs: &[i32]) -> i32 {
    xs.iter().sum()
}

// Returning a closure that owns mutable state
fn make_counter() -> impl FnMut() -> u32 {
    let mut c = 0;
    move || {
        c += 1;
        c
    }
}

// Different closure types behind one type: a trait object
fn make_adder(n: i32) -> Box<dyn Fn(i32) -> i32> {
    Box::new(move |x| x + n)
}

fn apply<F: Fn(i32) -> i32>(f: F, x: i32) -> i32 {
    f(x)
}

// Generics with a trait bound
fn largest<T: PartialOrd + Copy>(xs: &[T]) -> T {
    let mut m = xs[0];
    for &x in xs {
        if x > m {
            m = x;
        }
    }
    m
}

// Evaluated at compile time
const fn square(n: u32) -> u32 {
    n * n
}
const SQ: u32 = square(12);

fn fib(n: u32) -> u64 {
    match n {
        0 => 0,
        1 => 1,
        _ => fib(n - 1) + fib(n - 2),
    }
}

fn main() {
    println!("{}", add(2, 3));
    let (q, r) = divmod(17, 5);
    println!("{q} {r}");
    println!("{}", sum(&[1, 2, 3, 4]));

    let mut c = make_counter();
    let (c1, c2, c3) = (c(), c(), c());
    println!("{c1} {c2} {c3}");

    let add5 = make_adder(5);
    println!("{}", apply(&add5, 10));
    println!("{}", apply(|x| x * x, 7));

    println!("{} {:.1} {}", largest(&[3, 9, 2]), largest(&[1.5, 0.2]), largest(&['a', 'z', 'm']));
    println!("{SQ} {}", fib(20));

    // FnMut: mutates captured state
    let mut log = Vec::new();
    let mut record = |s: &str| log.push(s.to_uppercase());
    record("a");
    record("b");
    println!("{log:?}");

    // FnOnce: consumes a captured value
    let name = String::from("ferris");
    let consume = move || name;
    println!("{}", consume());

    // Plain function pointers: fn(i32, i32) -> i32
    let ops: [(&str, fn(i32, i32) -> i32); 2] = [("add", add), ("mul", |a, b| a * b)];
    for (n, f) in ops {
        print!("{n}={} ", f(3, 4));
    }
    println!();

    // Iterator chains replace most loops
    let evens_sq: Vec<i32> = (1..=6).filter(|n| n % 2 == 0).map(|n| n * n).collect();
    println!("{evens_sq:?}");
}
```

```text output
5
3 2
10
1 2 3
15
49
9 1.5 z
144 6765
["A", "B"]
ferris
add=7 mul=12 
[4, 16, 36]
```

## Details that bite

- A stray semicolon on the last line turns the return value into `()` and
  produces a type error — read the message, it points to the `;`.
- Closures capture by the *least* needed mode (shared borrow, mutable
  borrow, or move). `move` forces ownership transfer; you need it when the
  closure outlives the current scope (threads, returned closures).
- `impl Trait` in return position names *one* concrete hidden type. To
  return different closures from different branches, use
  `Box<dyn Fn…>`.
- A `FnMut` closure must be declared `let mut` to be called.
- Recursion has no tail-call guarantee; deep recursion overflows the stack.
  Prefer iteration for unbounded depth.
- There are no default arguments or overloading. Use `Option<T>` params,
  builder structs, or distinct names.
- Prefer `&[T]` over `&Vec<T>` and `&str` over `&String` for parameters:
  they accept more, and cost nothing.

## Exercises

```rust file=exercise.rs
/// compose(f, g)(x) == g(f(x))
fn compose<A, B, C>(_f: impl Fn(A) -> B, _g: impl Fn(B) -> C) -> impl Fn(A) -> C {
    |_: A| todo!()
}

/// Returns a closure that adds its argument to a running total.
fn make_accumulator(_start: i32) -> impl FnMut(i32) -> i32 {
    |_: i32| todo!()
}

/// Apply f to x, n times.
fn apply_n(_f: impl Fn(i32) -> i32, _n: u32, _x: i32) -> i32 {
    todo!()
}

/// (min, max) of a slice, None when empty.
fn min_max(_xs: &[i32]) -> Option<(i32, i32)> {
    todo!()
}

/// How many elements satisfy pred.
fn count_where<T>(_xs: &[T], _pred: impl Fn(&T) -> bool) -> usize {
    todo!()
}

/// Iterative Fibonacci.
fn fib_iter(_n: u32) -> u64 {
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
    let inc_then_double = compose(|x: i32| x + 1, |x: i32| x * 2);
    let to_len = compose(|s: &str| s.trim().to_string(), |s: String| s.len());
    let mut acc = make_accumulator(10);
    acc(5);
    let results = [
        check("compose", inc_then_double(5), 12),
        check("compose types", to_len("  hey "), 3),
        check("accumulator", acc(5), 20),
        check("apply_n", apply_n(|x| x * 2, 4, 3), 48),
        check("apply_n 0", apply_n(|x| x * 2, 0, 3), 3),
        check("min_max", min_max(&[3, 9, -2, 5]), Some((-2, 9))),
        check("min_max empty", min_max(&[]), None),
        check("count_where", count_where(&["a", "bb", "cc", "d"], |s| s.len() == 2), 2),
        check("fib", [fib_iter(0), fib_iter(1), fib_iter(50)], [0, 1, 12586269025]),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

<details><summary>Solution</summary>

```rust file=solution.rs
fn compose<A, B, C>(f: impl Fn(A) -> B, g: impl Fn(B) -> C) -> impl Fn(A) -> C {
    move |x| g(f(x))
}

fn make_accumulator(start: i32) -> impl FnMut(i32) -> i32 {
    let mut total = start;
    move |n| {
        total += n;
        total
    }
}

fn apply_n(f: impl Fn(i32) -> i32, n: u32, x: i32) -> i32 {
    (0..n).fold(x, |acc, _| f(acc))
}

fn min_max(xs: &[i32]) -> Option<(i32, i32)> {
    let first = *xs.first()?;
    Some(xs.iter().fold((first, first), |(lo, hi), &x| (lo.min(x), hi.max(x))))
}

fn count_where<T>(xs: &[T], pred: impl Fn(&T) -> bool) -> usize {
    xs.iter().filter(|x| pred(x)).count()
}

fn fib_iter(n: u32) -> u64 {
    let (mut a, mut b) = (0u64, 1u64);
    for _ in 0..n {
        (a, b) = (b, a + b);
    }
    a
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
    let inc_then_double = compose(|x: i32| x + 1, |x: i32| x * 2);
    let to_len = compose(|s: &str| s.trim().to_string(), |s: String| s.len());
    let mut acc = make_accumulator(10);
    acc(5);
    let results = [
        check("compose", inc_then_double(5), 12),
        check("compose types", to_len("  hey "), 3),
        check("accumulator", acc(5), 20),
        check("apply_n", apply_n(|x| x * 2, 4, 3), 48),
        check("apply_n 0", apply_n(|x| x * 2, 0, 3), 3),
        check("min_max", min_max(&[3, 9, -2, 5]), Some((-2, 9))),
        check("min_max empty", min_max(&[]), None),
        check("count_where", count_where(&["a", "bb", "cc", "d"], |s| s.len() == 2), 2),
        check("fib", [fib_iter(0), fib_iter(1), fib_iter(50)], [0, 1, 12586269025]),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

</details>

Next: [04 — Collections](04-collections.md)
