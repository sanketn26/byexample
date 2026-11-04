# Rust 03 — Functions and Closures

A function is `fn`, and every parameter and return type is written out.
The last expression, with no semicolon, is the return value. A closure
captures the names around it. It is `Fn`, `FnMut`, or `FnOnce` depending
on how it uses those names.

## The last expression is the return value

There is no `return` required. A stray semicolon on that line turns the
value into `()`, and the compiler points at the `;`. There are no default
arguments and no overloading. Use an `Option` parameter, a builder, or a
second function name.

```rust file=n01.rs
fn add(a: i32, b: i32) -> i32 {
    a + b
}

fn main() {
    println!("{}", add(2, 3));
}
```

```text output
5
```

## A tuple returns more than one value

The caller destructures it. Division here is the truncating kind from
lesson 01.

```rust file=n02.rs
fn divmod(a: i32, b: i32) -> (i32, i32) {
    (a / b, a % b)
}

fn main() {
    let (q, r) = divmod(17, 5);
    println!("{q} {r}");
}
```

```text output
3 2
```

## Take a slice, not a `Vec`

`&[T]` accepts a vector, an array, or any other slice, and it does not take
ownership. Prefer `&[T]` over `&Vec<T>` and `&str` over `&String`.

```rust file=n03.rs
fn sum(xs: &[i32]) -> i32 {
    xs.iter().sum()
}

fn main() {
    println!("{}", sum(&[1, 2, 3, 4]));
}
```

```text output
10
```

## A bound names what the function uses

`T: PartialOrd + Copy` means the values can be ordered and copied out of
the slice. The function works for any type that can do both.

```rust file=n04.rs
fn largest<T: PartialOrd + Copy>(xs: &[T]) -> T {
    let mut m = xs[0];
    for &x in xs {
        if x > m {
            m = x;
        }
    }
    m
}

fn main() {
    println!(
        "{} {:.1} {}",
        largest(&[3, 9, 2]),
        largest(&[1.5, 0.2]),
        largest(&['a', 'z', 'm'])
    );
}
```

```text output
9 1.5 z
```

## `const fn` runs at compile time

A const function can initialize a `const`. The call happens while the
program is compiled, not when `main` runs.

```rust file=n05.rs
const fn square(n: u32) -> u32 {
    n * n
}
const SQ: u32 = square(12);

fn main() {
    println!("{SQ}");
}
```

```text output
144
```

## Recursion has no tail-call guarantee

This Fibonacci is clear and fine for a small `n`. Deep recursion overflows
the stack. Prefer a loop when the depth is unbounded.

```rust file=n06.rs
fn fib(n: u32) -> u64 {
    match n {
        0 => 0,
        1 => 1,
        _ => fib(n - 1) + fib(n - 2),
    }
}

fn main() {
    println!("{}", fib(20));
}
```

```text output
6765
```

## `impl FnMut` returns one hidden closure

The closure owns a counter because of `move`. `impl Trait` in return
position names exactly one concrete type, which the caller cannot write
down. A `FnMut` value must be `let mut` to be called.

```rust file=n07.rs
fn make_counter() -> impl FnMut() -> u32 {
    let mut c = 0;
    move || {
        c += 1;
        c
    }
}

fn main() {
    let mut c = make_counter();
    let (c1, c2, c3) = (c(), c(), c());
    println!("{c1} {c2} {c3}");
}
```

```text output
1 2 3
```

## `Box<dyn Fn>` erases different closures

Two branches cannot return two different closure types through `impl Fn`.
Box them as `dyn Fn` when the closure is chosen at run time. Closures
capture by the least mode that works: shared borrow, mutable borrow, or
move. `move` forces the ownership transfer, which you need when the
closure outlives the current scope.

```rust file=n08.rs
fn make_adder(n: i32) -> Box<dyn Fn(i32) -> i32> {
    Box::new(move |x| x + n)
}

fn pick(even: bool) -> Box<dyn Fn(i32) -> i32> {
    if even {
        Box::new(|x| x * 2)
    } else {
        Box::new(|x| x + 1)
    }
}

fn apply<F: Fn(i32) -> i32>(f: F, x: i32) -> i32 {
    f(x)
}

fn main() {
    let add5 = make_adder(5);
    println!("{}", apply(&add5, 10));
    println!("{}", apply(|x| x * x, 7));
    println!("{} {}", pick(true)(3), pick(false)(3));
}
```

```text output
15
49
6 4
```

## `FnMut` changes what it captured

The closure pushes into `log`, so calling it needs a mutable binding.
Shared `Fn` would not be allowed to do that.

```rust file=n09.rs
fn main() {
    let mut log = Vec::new();
    let mut record = |s: &str| log.push(s.to_uppercase());
    record("a");
    record("b");
    println!("{log:?}");
}
```

```text output
["A", "B"]
```

## `FnOnce` consumes a captured value

After the closure returns the `String`, that value is gone, so the closure
cannot run a second time.

```rust file=n10.rs
fn main() {
    let name = String::from("ferris");
    let consume = move || name;
    println!("{}", consume());
}
```

```text output
ferris
```

## A function pointer is a type you can name

`fn(i32, i32) -> i32` is a pointer to a function, not a trait. A closure
that captures nothing coerces to one. A closure that captures does not.

```rust file=n11.rs
fn add(a: i32, b: i32) -> i32 {
    a + b
}

fn main() {
    let ops: [(&str, fn(i32, i32) -> i32); 2] = [("add", add), ("mul", |a, b| a * b)];
    for (n, f) in ops {
        print!("{n}={} ", f(3, 4));
    }
    println!();
}
```

```text output
add=7 mul=12 
```

## Iterators replace most loops

`filter`, `map`, and `collect` build a new collection without an index.
The range `1..=6` includes 6.

```rust file=n12.rs
fn main() {
    let evens_sq: Vec<i32> = (1..=6).filter(|n| n % 2 == 0).map(|n| n * n).collect();
    println!("{evens_sq:?}");
}
```

```text output
[4, 16, 36]
```

## A missing argument is an `Option`

There is no default-argument syntax. `Option` is the parameter that
may be absent. `unwrap_or` supplies the fallback at the use site.

```rust file=n13.rs
fn greet(name: Option<&str>) -> String {
    format!("hello {}", name.unwrap_or("stranger"))
}

fn main() {
    println!("{}", greet(None));
    println!("{}", greet(Some("Ada")));
}
```

```text output
hello stranger
hello Ada
```

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
