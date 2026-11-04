# Rust 04 — Collections

An array is fixed-size. `Vec<T>` grows. A slice (`&[T]`) borrows either of
them. `HashMap`, `HashSet`, `BTreeMap`, and `VecDeque` cover the other
shapes you reach for. The compiler will not let an iterator see a
collection change under it.

## `Vec` grows at the end and in the middle

`push` adds at the end. `insert` shifts elements right. Indexing with `v[i]`
panics when `i` is out of range. `get` returns `None` instead. You cannot
hold a reference into a `Vec` across a `push`: the push may reallocate, and
the borrow checker rejects the pair.

```rust file=n01.rs
fn main() {
    let mut v = vec![5, 2, 8, 1];
    v.push(9);
    v.insert(0, 7);
    println!("{v:?} {} {:?} {:?}", v.len(), v.first(), v.get(99));
}
```

```text output
[7, 5, 2, 8, 1, 9] 6 Some(7) None
```

## Sort, search, then keep what you want

`sort` is ascending. `binary_search` needs that order and returns the index
as `Ok`. `retain` drops elements in place. `pop` takes the last one.

```rust file=n02.rs
fn main() {
    let mut v = vec![7, 5, 2, 8, 1, 9];
    v.sort();
    println!("{v:?} {:?}", v.binary_search(&5));
    v.retain(|&x| x % 2 == 1);
    println!("{v:?}");
    println!("{:?}", v.pop());
}
```

```text output
[1, 2, 5, 7, 8, 9] Ok(2)
[1, 5, 7, 9]
Some(9)
```

## A slice is a borrowed window

`&v[1..3]` does not copy the elements out. `iter` yields `&T`. Reverse the
iterator when you want the other direction without rearranging the `Vec`.

```rust file=n03.rs
fn main() {
    let v = vec![1, 5, 7, 9];
    println!("{:?} {:?}", &v[1..3], v.iter().rev().collect::<Vec<_>>());
}
```

```text output
[5, 7] [9, 7, 5, 1]
```

## `windows` and `chunks` group a slice

`windows(2)` slides one element at a time and overlaps. `chunks(2)` cuts
the slice into pieces that do not overlap. The last chunk is shorter when
the length does not divide evenly.

```rust file=n04.rs
fn main() {
    let data = [1, 2, 3, 4, 5];
    println!("{:?}", data.windows(2).map(|w| w[1] - w[0]).collect::<Vec<_>>());
    println!("{:?}", data.chunks(2).collect::<Vec<_>>());
}
```

```text output
[1, 1, 1, 1]
[[1, 2], [3, 4], [5]]
```

## Three iterators, three kinds of access

`iter` yields `&T` and leaves the vector in place. `iter_mut` yields
`&mut T`. `into_iter` yields `T` and consumes the vector.

```rust file=n05.rs
fn main() {
    let mut v = vec![1, 2];
    let refs: Vec<_> = v.iter().copied().collect();
    for x in &mut v {
        *x += 1;
    }
    let owned: Vec<_> = v.into_iter().collect();
    println!("{refs:?} {owned:?}");
}
```

```text output
[1, 2] [2, 3]
```

## An array of `Copy` elements is `Copy`

Assigning the array copies every byte. `[0u8; 4]` is four zeros, and both
names stay usable. Call `Vec::with_capacity` when you know how many
elements a vector will hold, so it does not grow one push at a time.

```rust file=n06.rs
fn main() {
    let a = [0u8; 4];
    let b = a;
    let v = Vec::<i32>::with_capacity(4);
    println!("{a:?} {} {}", b.len(), v.capacity() >= 4);
}
```

```text output
[0, 0, 0, 0] 4 true
```

## `sort_by` takes a comparator

`cmp` then `then` builds a key out of two orderings: age descending, then
name ascending.

```rust file=n07.rs
fn main() {
    let mut people = vec![("Al", 30), ("Bo", 25), ("Cy", 30)];
    people.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(b.0)));
    println!("{people:?}");
}
```

```text output
[("Al", 30), ("Cy", 30), ("Bo", 25)]
```

## `dedup` only collapses neighbours

Equal elements that are not next to each other stay. Sort first if you want
every duplicate gone. `remove(i)` shifts the tail and is O(n). `swap_remove`
is O(1) and does not keep the order.

```rust file=n08.rs
fn main() {
    let mut d = vec![1, 1, 2, 2, 3, 1];
    d.dedup();
    println!("{d:?}");
    let mut v = vec![1, 2, 3, 4];
    v.swap_remove(1);
    println!("{v:?}");
}
```

```text output
[1, 2, 3, 1]
[1, 4, 3]
```

## `vec![row; n]` clones each row

Each inner `Vec` is its own allocation. Filling a grid this way does not
alias the rows the way a copied pointer would in Python or C.

```rust file=n09.rs
fn main() {
    let mut grid = vec![vec![0; 3]; 2];
    grid[1][2] = 5;
    println!("{grid:?}");
}
```

```text output
[[0, 0, 0], [0, 0, 5]]
```

## `HashMap` does not promise an order

`entry` inserts a key only when it is missing, then gives you a mutable
reference. Iteration order is arbitrary and can change between runs. Sort
the keys, or use `BTreeMap`, when the output must be stable. Keys need
`Eq + Hash`. `f64` is neither.

```rust file=n10.rs
use std::collections::HashMap;

fn main() {
    let mut ages = HashMap::new();
    ages.insert("ann", 31);
    ages.insert("bob", 25);
    println!(
        "{:?} {:?} {}",
        ages.get("ann"),
        ages.get("zed"),
        ages.contains_key("bob")
    );
    *ages.entry("ann").or_insert(0) += 1;
    ages.entry("cy").or_insert(40);
    let mut keys: Vec<_> = ages.keys().copied().collect();
    keys.sort();
    println!("{keys:?} {}", ages["ann"]);
}
```

```text output
Some(31) None true
["ann", "bob", "cy"] 32
```

## `BTreeMap` walks keys in order

`or_default` inserts the zero value (`0` for `usize`) when the key is new.
The `Debug` output is sorted because the tree is.

```rust file=n11.rs
use std::collections::BTreeMap;

fn main() {
    let mut counts: BTreeMap<char, usize> = BTreeMap::new();
    for c in "banana".chars() {
        *counts.entry(c).or_default() += 1;
    }
    println!("{counts:?}");
}
```

```text output
{'a': 3, 'b': 1, 'n': 2}
```

## Sets know union and intersection

`HashSet` is a `HashMap` whose values you never see. Collect the results
and sort them: the set itself has no order.

```rust file=n12.rs
use std::collections::HashSet;

fn main() {
    let s1: HashSet<i32> = [1, 2, 3].into_iter().collect();
    let s2: HashSet<i32> = [3, 4].into_iter().collect();
    let mut inter: Vec<_> = s1.intersection(&s2).collect();
    inter.sort();
    let mut uni: Vec<_> = s1.union(&s2).copied().collect();
    uni.sort();
    println!("{inter:?} {uni:?}");
}
```

```text output
[3] [1, 2, 3, 4]
```

## `VecDeque` is cheap at both ends

`push_front` and `pop_front` are O(1). Use it for a queue. A `Vec` would
shift every element to do the same thing.

```rust file=n13.rs
use std::collections::VecDeque;

fn main() {
    let mut dq = VecDeque::new();
    dq.push_back(1);
    dq.push_back(2);
    dq.push_front(0);
    println!("{dq:?}");
    println!("{:?}", dq.pop_front());
}
```

```text output
[0, 1, 2]
Some(0)
```

## Exercises

```rust file=exercise.rs
use std::collections::{BTreeMap, HashMap};

/// Reverse in place without allocating.
fn reverse_in_place(_xs: &mut [i32]) {
    todo!()
}

/// Remove duplicates, keeping the first occurrence order.
fn unique(_xs: &[i32]) -> Vec<i32> {
    todo!()
}

/// Lowercase word frequencies, splitting on whitespace.
fn word_count(_text: &str) -> HashMap<String, usize> {
    todo!()
}

/// A new Vec rotated left by k (k may exceed the length).
fn rotate_left(_xs: &[i32], _k: usize) -> Vec<i32> {
    todo!()
}

/// Group words by length, keeping input order inside each group.
fn group_by_len(_words: &[&str]) -> BTreeMap<usize, Vec<String>> {
    todo!()
}

/// The n most frequent words: count descending, then word ascending.
fn top_n(_counts: &HashMap<String, usize>, _n: usize) -> Vec<String> {
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
    let mut r = [1, 2, 3, 4];
    reverse_in_place(&mut r);
    let wc = word_count("The cat the  hat THE end");
    let mut want = HashMap::new();
    for (w, n) in [("the", 3), ("cat", 1), ("hat", 1), ("end", 1)] {
        want.insert(w.to_string(), n);
    }
    let mut groups = BTreeMap::new();
    groups.insert(1, vec!["a".to_string(), "c".to_string()]);
    groups.insert(2, vec!["bb".to_string(), "dd".to_string()]);
    groups.insert(3, vec!["eee".to_string()]);
    let results = [
        check("reverse", r, [4, 3, 2, 1]),
        check("unique", unique(&[3, 1, 3, 2, 1]), vec![3, 1, 2]),
        check("word_count", wc.clone(), want),
        check("rotate", rotate_left(&[1, 2, 3, 4, 5], 7), vec![3, 4, 5, 1, 2]),
        check("rotate empty", rotate_left(&[], 3), vec![]),
        check("group_by_len", group_by_len(&["a", "bb", "c", "dd", "eee"]), groups),
        check("top_n", top_n(&wc, 2), vec!["the".to_string(), "cat".to_string()]),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

<details><summary>Solution</summary>

```rust file=solution.rs
use std::collections::{BTreeMap, HashMap, HashSet};

fn reverse_in_place(xs: &mut [i32]) {
    let n = xs.len();
    for i in 0..n / 2 {
        xs.swap(i, n - 1 - i);
    }
}

fn unique(xs: &[i32]) -> Vec<i32> {
    let mut seen = HashSet::new();
    xs.iter().copied().filter(|x| seen.insert(*x)).collect()
}

fn word_count(text: &str) -> HashMap<String, usize> {
    let mut counts = HashMap::new();
    for w in text.split_whitespace() {
        *counts.entry(w.to_lowercase()).or_insert(0) += 1;
    }
    counts
}

fn rotate_left(xs: &[i32], k: usize) -> Vec<i32> {
    if xs.is_empty() {
        return Vec::new();
    }
    let k = k % xs.len();
    let mut out = xs.to_vec();
    out.rotate_left(k);
    out
}

fn group_by_len(words: &[&str]) -> BTreeMap<usize, Vec<String>> {
    let mut groups: BTreeMap<usize, Vec<String>> = BTreeMap::new();
    for w in words {
        groups.entry(w.len()).or_default().push(w.to_string());
    }
    groups
}

fn top_n(counts: &HashMap<String, usize>, n: usize) -> Vec<String> {
    let mut entries: Vec<_> = counts.iter().collect();
    entries.sort_by(|a, b| b.1.cmp(a.1).then(a.0.cmp(b.0)));
    entries.into_iter().take(n).map(|(w, _)| w.clone()).collect()
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
    let mut r = [1, 2, 3, 4];
    reverse_in_place(&mut r);
    let wc = word_count("The cat the  hat THE end");
    let mut want = HashMap::new();
    for (w, n) in [("the", 3), ("cat", 1), ("hat", 1), ("end", 1)] {
        want.insert(w.to_string(), n);
    }
    let mut groups = BTreeMap::new();
    groups.insert(1, vec!["a".to_string(), "c".to_string()]);
    groups.insert(2, vec!["bb".to_string(), "dd".to_string()]);
    groups.insert(3, vec!["eee".to_string()]);
    let results = [
        check("reverse", r, [4, 3, 2, 1]),
        check("unique", unique(&[3, 1, 3, 2, 1]), vec![3, 1, 2]),
        check("word_count", wc.clone(), want),
        check("rotate", rotate_left(&[1, 2, 3, 4, 5], 7), vec![3, 4, 5, 1, 2]),
        check("rotate empty", rotate_left(&[], 3), vec![]),
        check("group_by_len", group_by_len(&["a", "bb", "c", "dd", "eee"]), groups),
        check("top_n", top_n(&wc, 2), vec!["the".to_string(), "cat".to_string()]),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

</details>

Next: [05 — Strings](05-strings.md)
