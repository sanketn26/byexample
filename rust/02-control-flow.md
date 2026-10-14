# Rust 02 — Control Flow

Almost everything is an **expression**: `if`, `match` and blocks produce
values. `match` is exhaustive — the compiler refuses to build if you miss a
case.

## Example

```rust file=example.rs
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
    // `if` is an expression
    let n = 15;
    let kind = if n % 15 == 0 {
        "fizzbuzz"
    } else if n % 3 == 0 {
        "fizz"
    } else {
        "other"
    };
    println!("{kind}");

    // `loop` can break with a value
    let mut counter = 0;
    let result = loop {
        counter += 1;
        if counter == 10 {
            break counter * 2;
        }
    };
    println!("{result}");

    // while
    let mut k = 3;
    while k > 0 {
        print!("{k} ");
        k -= 1;
    }
    println!();

    // for over ranges and iterators
    for i in 0..3 {
        print!("{i} ");
    }
    println!();
    for i in (0..7).step_by(3).rev() {
        print!("{i} ");
    }
    println!();
    for (i, ch) in "abc".chars().enumerate() {
        print!("{i}{ch} ");
    }
    println!();

    // Labelled breaks
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

    // match with ranges, alternatives and guards
    for n in [-5, 0, 2, 10, 11] {
        print!("{} ", classify(n));
    }
    println!();

    // Destructuring in patterns
    let pair = (3, -3);
    match pair {
        (x, y) if x + y == 0 => println!("opposites"),
        (x, _) if x % 2 == 1 => println!("odd x"),
        _ => println!("other"),
    }

    // if let, let-else, while let, matches!
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
fizzbuzz
20
3 2 1 
0 1 2 
6 3 0 
0a 1b 2c 
Some((2, 3))
negative zero small big even big odd 
opposites
got 5
10
3 2 1 
true
```

## Details that bite

- Conditions must be `bool`: `if n {}` with an integer does not compile.
- `match` arms must all have the same type, and the match must be
  exhaustive. `_` is the catch-all; avoid it when matching your own enums
  so that adding a variant breaks the build (which is what you want).
- Ranges: `0..3` excludes 3, `0..=3` includes it. `a..b` with `a > b` is
  just empty.
- A trailing semicolon turns an expression into a statement:
  `{ 5 }` is `5`, `{ 5; }` is `()`.
- `for x in v` **moves** `v`; use `for x in &v` or `for x in &mut v` to
  borrow.
- There is no C-style `for (;;)` and no `++`.
- `.rev()` needs a double-ended, exact-size iterator: `(0..7).step_by(3).rev()`
  works but `(0..=6).step_by(3).rev()` does not compile. Collect or restructure.
- Binding patterns in `match` can move values out; use `ref` or match on
  `&value` when you only want to look.

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
