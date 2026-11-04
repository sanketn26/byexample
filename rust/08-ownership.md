# Rust 08 — Ownership, Borrowing and Lifetimes

Every value has one owner. When that owner goes out of scope, the value is
dropped. A reference borrows without owning. The compiler rejects a
reference that outlives its data, and it rejects a mutation that aliases a
shared borrow. You rearrange the code when the checker says no: smaller
scopes, an index instead of a pointer, a cheap clone, or a split struct.

## A move transfers the single owner

Passing a `String`, or any non-`Copy` value, moves it. The old name is
illegal after that. Lend with `&value`, or call `.clone()` when you really
need a second owner. You cannot return a reference to a local variable.
Return the owned value instead.

```rust file=n01.rs
fn main() {
    let s1 = String::from("hello");
    let s2 = s1;
    println!("{s2}");
}
```

```text output
hello
```

## `clone` is an explicit deep copy

`clone` on a `String` allocates another buffer. Both names remain valid.
That is the point of writing it out.

```rust file=n02.rs
fn main() {
    let s2 = String::from("hello");
    let s3 = s2.clone();
    println!("{s2} {s3}");
}
```

```text output
hello hello
```

## `Copy` types are duplicated by assignment

Integers, `bool`, `char`, and shared references are `Copy`. Assignment
copies the bits. The original name still works, and there is no `.clone()`
to write.

```rust file=n03.rs
fn main() {
    let x = 5;
    let y = x;
    println!("{x} {y}");
}
```

```text output
5 5
```

## A borrow lets a function use the value

`len` takes `&String` and returns the length. `append` takes `&mut String`
and changes the same buffer. After either call, the owner still owns it.

```rust file=n04.rs
fn len(s: &String) -> usize {
    s.len()
}

fn append(s: &mut String) {
    s.push('!');
}

fn main() {
    let mut s = String::from("hi");
    println!("{}", len(&s));
    append(&mut s);
    println!("{s}");
}
```

```text output
2
hi!
```

## Many readers, or one writer

You may hold several shared borrows, or one mutable borrow, not both at
once. The checker looks at uses, not at the braces (non-lexical lifetimes).
A borrow ends at its last use, so the mutable borrow below is legal.

```rust file=n05.rs
fn main() {
    let mut s = String::from("hi!");
    let r1 = &s;
    let r2 = &s;
    println!("{r1} {r2}");
    let r3 = &mut s;
    r3.push('?');
    println!("{r3}");
}
```

```text output
hi! hi!
hi!?
```

## `Drop` runs in reverse order of declaration

The value is dropped at the end of the scope, including on `return` and
while a panic unwinds. That is how locks, files, and sockets clean up.
`drop(n)` does it now. The parameter of `takes` owns the value, so the drop
happens when `takes` returns.

```rust file=n06.rs
struct Noisy(&'static str);

impl Drop for Noisy {
    fn drop(&mut self) {
        println!("drop {}", self.0);
    }
}

fn takes(n: Noisy) {
    println!("took {}", n.0);
}

fn main() {
    {
        let _a = Noisy("a");
        let _b = Noisy("b");
        println!("scope end");
    }
    takes(Noisy("moved"));
    let n = Noisy("kept");
    drop(n);
    println!("after drop");
}
```

```text output
scope end
drop b
drop a
took moved
drop moved
drop kept
after drop
```

## A lifetime says how two borrows relate

`'a` on `longest` means the returned reference lives no longer than both
inputs. The annotation does not extend anyone's life. It tells the compiler
the relationship it has to check. A struct that stores a reference names
the same relationship.

```rust file=n07.rs
fn longest<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() >= b.len() {
        a
    } else {
        b
    }
}

struct Parser<'a> {
    input: &'a str,
}

impl<'a> Parser<'a> {
    fn first_word(&self) -> &'a str {
        self.input.split(' ').next().unwrap_or("")
    }
}

fn main() {
    println!("{}", longest("apple", "fig"));
    let p = Parser { input: "hello world" };
    println!("{}", p.first_word());
}
```

```text output
apple
hello
```

## `swap` and `take` move through a mutable borrow

`mem::swap` exchanges two values. `mem::take` moves a value out and leaves
`Default::default()` behind, which for a `Vec` is empty. Neither one clones.

```rust file=n08.rs
fn main() {
    let mut a = vec![1, 2];
    let mut b = vec![3];
    std::mem::swap(&mut a, &mut b);
    println!("{a:?} {b:?}");
    let taken = std::mem::take(&mut a);
    println!("{taken:?} {a:?}");
}
```

```text output
[3] [1, 2]
[3] []
```

## `Box` puts one value on the heap

A recursive enum would otherwise contain itself. The `Box` makes the size
finite. Dereference with `*`.

```rust file=n09.rs
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
    let boxed = Box::new(5);
    println!("{}", *boxed + 1);
    let list = List::Cons(1, Box::new(List::Cons(2, Box::new(List::Nil))));
    println!("{}", sum(&list));
}
```

```text output
6
3
```

## `Rc` shares ownership on one thread

`Rc::clone` increments a count. It does not clone the vector. `RefCell`
moves the borrow check to runtime: two mutable borrows panic with "already
borrowed". Use these only when the static rules cannot express the design.
Across threads the pair is `Arc` and `Mutex` (lesson 11), because `Rc` and
`RefCell` are not `Send` or `Sync`.

```rust file=n10.rs
use std::cell::RefCell;
use std::rc::Rc;

fn main() {
    let shared = Rc::new(RefCell::new(vec![1]));
    let other = Rc::clone(&shared);
    other.borrow_mut().push(2);
    println!("{:?} {}", shared.borrow(), Rc::strong_count(&shared));

    std::panic::set_hook(Box::new(|_| {}));
    let cell = RefCell::new(1);
    let _guard = cell.borrow();
    let panicked = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let _ = cell.borrow_mut();
    }));
    println!("{}", panicked.is_err());
}
```

```text output
[1, 2] 2
true
```

## `Weak` does not keep the value alive

An `Rc` cycle never reaches zero, so it leaks. Store a `Weak` for the back
edge. `upgrade` returns `None` once the last strong pointer is gone.

```rust file=n11.rs
use std::rc::{Rc, Weak};

fn main() {
    let a = Rc::new(1);
    let w: Weak<i32> = Rc::downgrade(&a);
    println!("{}", w.upgrade().is_some());
    drop(a);
    println!("{}", w.upgrade().is_none());
}
```

```text output
true
true
```

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
