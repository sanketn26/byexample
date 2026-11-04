# Rust 02 — Control Flow

Almost everything is an expression: `if`, `match`, and a block all produce a
value. `match` is exhaustive. The compiler refuses to build the program if
a case is missing.

## `if` produces a value

Each branch has the same type, and the condition must be a `bool`. `if n {}`
with an integer does not compile. There is no C-style `for (;;)` and no `++`.

```rust file=n01.rs
fn main() {
    let n = 15;
    let kind = if n % 15 == 0 {
        "fizzbuzz"
    } else if n % 3 == 0 {
        "fizz"
    } else {
        "other"
    };
    println!("{kind}");
}
```

```text output
fizzbuzz
```

## A semicolon throws the value away

`{ 5 }` is the value `5`. `{ 5; }` is the unit value `()`, because the
semicolon turns the expression into a statement.

```rust file=n02.rs
fn main() {
    let a = { 5 };
    let b = { 5; };
    println!("{a} {b:?}");
}
```

```text output
5 ()
```

## `loop` can break with a value

`loop` runs until `break`. `break` may carry the value the whole loop
evaluates to.

```rust file=n03.rs
fn main() {
    let mut counter = 0;
    let result = loop {
        counter += 1;
        if counter == 10 {
            break counter * 2;
        }
    };
    println!("{result}");
}
```

```text output
20
```

## `while` tests before each pass

The body runs while the condition is `true`. `print!` does not add a newline,
so the numbers stay on one line.

```rust file=n04.rs
fn main() {
    let mut k = 3;
    while k > 0 {
        print!("{k} ");
        k -= 1;
    }
    println!();
}
```

```text output
3 2 1 
```

## `for` walks a range or a borrow

`0..3` excludes 3. `0..=3` includes it. A range whose start is past its end
is empty, not an error. `for x in v` **moves** `v`. Write `for x in &v` or
`for x in &mut v` to borrow it and keep the collection.

```rust file=n05.rs
fn main() {
    for i in 0..3 {
        print!("{i} ");
    }
    println!();
    let v = vec![10, 20, 30];
    for x in &v {
        print!("{x} ");
    }
    println!("{}", v.len());
    println!("{} {}", (0..=3).contains(&3), (3..1).count());
}
```

```text output
0 1 2 
10 20 30 3
true 0
```

## `.rev()` needs an exact end

`.rev()` only works on a double-ended iterator whose size is known.
`(0..7).step_by(3).rev()` compiles. `(0..=6).step_by(3).rev()` does not.
Collect into a `Vec`, or rebuild the range.

```rust file=n06.rs
fn main() {
    for i in (0..7).step_by(3).rev() {
        print!("{i} ");
    }
    println!();
}
```

```text output
6 3 0 
```

## `enumerate` numbers the items

The index comes from the iterator, not from the characters themselves.

```rust file=n07.rs
fn main() {
    for (i, ch) in "abc".chars().enumerate() {
        print!("{i}{ch} ");
    }
    println!();
}
```

```text output
0a 1b 2c 
```

## A label names which loop breaks

`break` without a label leaves the innermost loop. `'outer: for ...` and
`break 'outer` leave the loop you named.

```rust file=n08.rs
fn main() {
    let mut found = None;
    'outer: for i in 1..5 {
        for j in 1..5 {
            if i * j == 6 {
                found = Some((i, j));
                break 'outer;
            }
        }
    }
    println!("{found:?}");
}
```

```text output
Some((2, 3))
```

## `match` arms cover every value

Ranges, `|` alternatives, and `if` guards are patterns. Every arm has the
same type, and something must match. `_` is the catch-all. Skip it on your
own enums so adding a variant breaks the build, which is what you want.

```rust file=n09.rs
fn classify(n: i32) -> &'static str {
    match n {
        i32::MIN..=-1 => "negative",
        0 => "zero",
        1 | 2 | 3 => "small",
        x if x % 2 == 0 => "big even",
        _ => "big odd",
    }
}

fn main() {
    for n in [-5, 0, 2, 10, 11] {
        print!("{} ", classify(n));
    }
    println!();
}
```

```text output
negative zero small big even big odd 
```

## A pattern can move the value out

Matching `(x, y)` on a pair of `String` would move `x`. Match `&pair` (or
write `ref`) when you only want to look and still use the original.

```rust file=n10.rs
fn main() {
    let pair = (String::from("hi"), 1);
    match &pair {
        (s, n) => println!("{s} {n}"),
    }
    println!("{}", pair.0);
}
```

```text output
hi 1
hi
```

## Patterns also test one shape

The pair below is two opposites, so the guard `x + y == 0` wins before the
odd-x arm.

```rust file=n11.rs
fn main() {
    let pair = (3, -3);
    match pair {
        (x, y) if x + y == 0 => println!("opposites"),
        (x, _) if x % 2 == 1 => println!("odd x"),
        _ => println!("other"),
    }
}
```

```text output
opposites
```

## `if let` and `while let` match one arm

`if let` runs the body only when the pattern fits. `let`/`else` leaves the
function when it does not. `while let` loops until the pattern fails.
`matches!` is the same test as a boolean.

```rust file=n12.rs
fn main() {
    let maybe = Some(5);
    if let Some(v) = maybe {
        println!("got {v}");
    }
    let Some(first) = [10, 20].first() else {
        return;
    };
    println!("{first}");
    let mut stack = vec![1, 2, 3];
    while let Some(top) = stack.pop() {
        print!("{top} ");
    }
    println!();
    println!("{}", matches!(maybe, Some(n) if n > 3));
}
```

```text output
got 5
10
3 2 1 
true
```

## Exercises

```rust file=exercise.rs
fn fizzbuzz(_n: u32) -> Vec<String> {
    todo!()
}

/// Steps for Collatz to reach 1; None for 0.
fn collatz_steps(_n: u64) -> Option<u32> {
    todo!()
}

/// First value that appears a second time.
fn first_repeat(_xs: &[i32]) -> Option<i32> {
    todo!()
}

/// All primes <= limit.
fn primes_up_to(_limit: u32) -> Vec<u32> {
    todo!()
}

/// "equilateral", "isosceles", "scalene" or "invalid"
/// (a side <= 0 or the triangle inequality fails).
fn triangle(_a: f64, _b: f64, _c: f64) -> &'static str {
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
        check("fizzbuzz", fizzbuzz(15)[10..].iter().map(|s| s.as_str()).collect::<Vec<_>>(), vec!["11", "Fizz", "13", "14", "FizzBuzz"]),
        check("collatz 1", collatz_steps(1), Some(0)),
        check("collatz 27", collatz_steps(27), Some(111)),
        check("collatz 0", collatz_steps(0), None),
        check("repeat", first_repeat(&[3, 1, 4, 1, 5, 3]), Some(1)),
        check("no repeat", first_repeat(&[1, 2, 3]), None),
        check("primes", primes_up_to(30), vec![2, 3, 5, 7, 11, 13, 17, 19, 23, 29]),
        check("primes small", primes_up_to(1), vec![]),
        check("equilateral", triangle(2.0, 2.0, 2.0), "equilateral"),
        check("isosceles", triangle(2.0, 2.0, 3.0), "isosceles"),
        check("scalene", triangle(3.0, 4.0, 5.0), "scalene"),
        check("invalid", triangle(1.0, 2.0, 5.0), "invalid"),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

<details><summary>Solution</summary>

```rust file=solution.rs
use std::collections::HashSet;

fn fizzbuzz(n: u32) -> Vec<String> {
    (1..=n)
        .map(|i| match (i % 3, i % 5) {
            (0, 0) => "FizzBuzz".to_string(),
            (0, _) => "Fizz".to_string(),
            (_, 0) => "Buzz".to_string(),
            _ => i.to_string(),
        })
        .collect()
}

fn collatz_steps(mut n: u64) -> Option<u32> {
    if n == 0 {
        return None;
    }
    let mut steps = 0;
    while n != 1 {
        n = if n % 2 == 0 { n / 2 } else { 3 * n + 1 };
        steps += 1;
    }
    Some(steps)
}

fn first_repeat(xs: &[i32]) -> Option<i32> {
    let mut seen = HashSet::new();
    xs.iter().copied().find(|&x| !seen.insert(x))
}

fn primes_up_to(limit: u32) -> Vec<u32> {
    let limit = limit as usize;
    if limit < 2 {
        return Vec::new();
    }
    let mut composite = vec![false; limit + 1];
    let mut out = Vec::new();
    for i in 2..=limit {
        if composite[i] {
            continue;
        }
        out.push(i as u32);
        let mut j = i * i;
        while j <= limit {
            composite[j] = true;
            j += i;
        }
    }
    out
}

fn triangle(a: f64, b: f64, c: f64) -> &'static str {
    if a <= 0.0 || b <= 0.0 || c <= 0.0 || a + b <= c || a + c <= b || b + c <= a {
        return "invalid";
    }
    if a == b && b == c {
        "equilateral"
    } else if a == b || b == c || a == c {
        "isosceles"
    } else {
        "scalene"
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
        check("fizzbuzz", fizzbuzz(15)[10..].iter().map(|s| s.as_str()).collect::<Vec<_>>(), vec!["11", "Fizz", "13", "14", "FizzBuzz"]),
        check("collatz 1", collatz_steps(1), Some(0)),
        check("collatz 27", collatz_steps(27), Some(111)),
        check("collatz 0", collatz_steps(0), None),
        check("repeat", first_repeat(&[3, 1, 4, 1, 5, 3]), Some(1)),
        check("no repeat", first_repeat(&[1, 2, 3]), None),
        check("primes", primes_up_to(30), vec![2, 3, 5, 7, 11, 13, 17, 19, 23, 29]),
        check("primes small", primes_up_to(1), vec![]),
        check("equilateral", triangle(2.0, 2.0, 2.0), "equilateral"),
        check("isosceles", triangle(2.0, 2.0, 3.0), "isosceles"),
        check("scalene", triangle(3.0, 4.0, 5.0), "scalene"),
        check("invalid", triangle(1.0, 2.0, 5.0), "invalid"),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

</details>

Next: [03 — Functions and closures](03-functions.md)
