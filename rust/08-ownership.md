# Rust 08 — Ownership, Borrowing and Lifetimes

This is Rust's defining idea. Every value has exactly one owner; when the
owner goes out of scope the value is dropped. References borrow without
owning, and the compiler proves at compile time that no reference outlives
its data or aliases a mutation.

## Example

```rust file=example.rs
use std::cell::RefCell;
use std::rc::Rc;

struct Noisy(&'static str);

impl Drop for Noisy {
    fn drop(&mut self) {
        println!("drop {}", self.0);
    }
}

fn takes(n: Noisy) {
    println!("took {}", n.0);
}

fn len(s: &String) -> usize {
    s.len()
}

fn append(s: &mut String) {
    s.push('!');
}

// The 'a says: the result lives no longer than BOTH inputs
fn longest<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() >= b.len() {
        a
    } else {
        b
    }
}

// A struct that borrows must say how long
struct Parser<'a> {
    input: &'a str,
}

impl<'a> Parser<'a> {
    fn first_word(&self) -> &'a str {
        self.input.split(' ').next().unwrap_or("")
    }
}

enum List {
    Cons(i32, Box<List>),
    Nil,
}

fn sum(list: &List) -> i32 {
    match list {
        List::Cons(v, rest) => v + sum(rest),
        List::Nil => 0,
    }
}

fn main() {
    // Move: s1 is no longer usable
    let s1 = String::from("hello");
    let s2 = s1;
    println!("{s2}");

    // Clone: an explicit deep copy
    let s3 = s2.clone();
    println!("{s2} {s3}");

    // Copy types (integers, bool, char, ...) are duplicated implicitly
    let x = 5;
    let y = x;
    println!("{x} {y}");

    // Borrowing
    let mut s = String::from("hi");
    println!("{}", len(&s));
    append(&mut s);
    println!("{s}");

    // Many shared borrows OR one mutable borrow, never both at once
    let r1 = &s;
    let r2 = &s;
    println!("{r1} {r2}");
    let r3 = &mut s; // fine: r1 and r2 are no longer used
    r3.push('?');
    println!("{r3}");

    // Drop order: reverse of declaration
    {
        let _a = Noisy("a");
        let _b = Noisy("b");
        println!("scope end");
    }
    takes(Noisy("moved"));
    let n = Noisy("kept");
    drop(n);
    println!("after drop");

    // Lifetimes
    println!("{}", longest("apple", "fig"));
    let p = Parser { input: "hello world" };
    let w = p.first_word();
    println!("{w}");

    // std::mem helpers swap values without clone
    let mut a = vec![1, 2];
    let mut b = vec![3];
    std::mem::swap(&mut a, &mut b);
    println!("{a:?} {b:?}");
    let taken = std::mem::take(&mut a);
    println!("{taken:?} {a:?}");

    // Heap allocation and shared ownership
    let boxed = Box::new(5);
    println!("{}", *boxed + 1);

    let shared = Rc::new(RefCell::new(vec![1]));
    let other = Rc::clone(&shared);
    other.borrow_mut().push(2);
    println!("{:?} {}", shared.borrow(), Rc::strong_count(&shared));

    let list = List::Cons(1, Box::new(List::Cons(2, Box::new(List::Nil))));
    println!("{}", sum(&list));
}
```

```text output
hello
hello hello
5 5
2
hi!
hi! hi!
hi!?
scope end
drop b
drop a
took moved
drop moved
drop kept
after drop
apple
hello
[3] [1, 2]
[3] []
6
[1, 2] 2
3
```

## Details that bite

- Passing a `String` (or any non-`Copy` value) to a function **moves** it;
  you cannot use it afterwards. Pass `&value` to lend it, or `.clone()` to
  duplicate it.
- The borrow checker reasons about *uses*, not scopes (non-lexical
  lifetimes): a borrow ends after its last use.
- You cannot return a reference to a local variable; return the owned
  value instead.
- `Rc<T>` is single-threaded shared ownership (use `Arc<T>` across
  threads), and `RefCell<T>` moves borrow checking to runtime: breaking the
  rules panics (`already borrowed`). Reach for them only when the static
  rules truly cannot express your design.
- `Rc` cycles leak; break them with `Weak`.
- `Drop` runs at scope end in reverse order, even on early `return` or
  panic unwinding. That is how locks, files and sockets clean up (RAII).
- Lifetime annotations do not change how long values live; they describe
  relationships so the compiler can verify them.
- "Fighting the borrow checker" usually means restructuring: split a
  struct, clone cheaply, store indexes instead of references, or use
  smaller scopes.

## Exercises

```rust file=exercise.rs
#![allow(dead_code)] // Tracker's fields are unused until you implement Drop
use std::cell::RefCell;
use std::rc::Rc;

/// The longest whitespace-separated word (the first one on ties).
/// The result borrows from `text`.
fn longest_word<'a>(_text: &'a str) -> &'a str {
    todo!()
}

/// Split "first rest of it" into ("first", "rest of it").
/// With a single word the second part is "".
fn split_first_word(_s: &str) -> (&str, &str) {
    todo!()
}

/// Merge two sorted vectors into one sorted vector, consuming both.
fn merge_sorted(_a: Vec<i32>, _b: Vec<i32>) -> Vec<i32> {
    todo!()
}

/// Remove the largest element from `v` and return it.
fn take_largest(_v: &mut Vec<i32>) -> Option<i32> {
    todo!()
}

/// Replace every string in `v` with an empty string and return the
/// original strings, without cloning.
fn drain_strings(_v: &mut [String]) -> Vec<String> {
    todo!()
}

/// Pushes "dropped <name>" into the shared log when it is dropped.
struct Tracker {
    name: String,
    log: Rc<RefCell<Vec<String>>>,
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
    let text = String::from("a quick brownish fox");
    let longest = longest_word(&text);

    let mut v = vec![3, 9, 2, 7];
    let max = take_largest(&mut v);

    let mut names = vec!["ann".to_string(), "bob".to_string()];
    let drained = drain_strings(&mut names);

    let log = Rc::new(RefCell::new(Vec::new()));
    {
        let _a = Tracker { name: "a".into(), log: Rc::clone(&log) };
        let _b = Tracker { name: "b".into(), log: Rc::clone(&log) };
    }

    let results = [
        check("longest_word", longest, "brownish"),
        check("split_first_word", split_first_word("first rest of it"), ("first", "rest of it")),
        check("split single", split_first_word("only"), ("only", "")),
        check("merge", merge_sorted(vec![1, 4, 7], vec![2, 3, 9]), vec![1, 2, 3, 4, 7, 9]),
        check("take_largest", (max, v), (Some(9), vec![3, 2, 7])),
        check("take_largest empty", take_largest(&mut Vec::new()), None),
        check("drain", (drained, names), (vec!["ann".to_string(), "bob".to_string()], vec![String::new(), String::new()])),
        check("drop order", log.borrow().clone(), vec!["dropped b".to_string(), "dropped a".to_string()]),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

<details><summary>Solution</summary>

```rust file=solution.rs
use std::cell::RefCell;
use std::rc::Rc;

fn longest_word<'a>(text: &'a str) -> &'a str {
    let mut best = "";
    for w in text.split_whitespace() {
        if w.len() > best.len() {
            best = w;
        }
    }
    best
}

fn split_first_word(s: &str) -> (&str, &str) {
    match s.split_once(' ') {
        Some((first, rest)) => (first, rest),
        None => (s, ""),
    }
}

fn merge_sorted(a: Vec<i32>, b: Vec<i32>) -> Vec<i32> {
    let mut out = Vec::with_capacity(a.len() + b.len());
    let mut a = a.into_iter().peekable();
    let mut b = b.into_iter().peekable();
    loop {
        match (a.peek(), b.peek()) {
            (Some(x), Some(y)) => {
                if x <= y {
                    out.push(a.next().unwrap());
                } else {
                    out.push(b.next().unwrap());
                }
            }
            (Some(_), None) => out.extend(a.by_ref()),
            (None, Some(_)) => out.extend(b.by_ref()),
            (None, None) => break,
        }
    }
    out
}

fn take_largest(v: &mut Vec<i32>) -> Option<i32> {
    let (idx, _) = v.iter().enumerate().max_by_key(|&(_, x)| *x)?;
    Some(v.remove(idx))
}

fn drain_strings(v: &mut [String]) -> Vec<String> {
    v.iter_mut().map(std::mem::take).collect()
}

struct Tracker {
    name: String,
    log: Rc<RefCell<Vec<String>>>,
}

impl Drop for Tracker {
    fn drop(&mut self) {
        self.log.borrow_mut().push(format!("dropped {}", self.name));
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
    let text = String::from("a quick brownish fox");
    let longest = longest_word(&text);

    let mut v = vec![3, 9, 2, 7];
    let max = take_largest(&mut v);

    let mut names = vec!["ann".to_string(), "bob".to_string()];
    let drained = drain_strings(&mut names);

    let log = Rc::new(RefCell::new(Vec::new()));
    {
        let _a = Tracker { name: "a".into(), log: Rc::clone(&log) };
        let _b = Tracker { name: "b".into(), log: Rc::clone(&log) };
    }

    let results = [
        check("longest_word", longest, "brownish"),
        check("split_first_word", split_first_word("first rest of it"), ("first", "rest of it")),
        check("split single", split_first_word("only"), ("only", "")),
        check("merge", merge_sorted(vec![1, 4, 7], vec![2, 3, 9]), vec![1, 2, 3, 4, 7, 9]),
        check("take_largest", (max, v), (Some(9), vec![3, 2, 7])),
        check("take_largest empty", take_largest(&mut Vec::new()), None),
        check("drain", (drained, names), (vec!["ann".to_string(), "bob".to_string()], vec![String::new(), String::new()])),
        check("drop order", log.borrow().clone(), vec!["dropped b".to_string(), "dropped a".to_string()]),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

</details>

Next: [09 — Traits and generics](09-traits.md)
