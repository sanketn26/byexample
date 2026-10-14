# Rust 04 — Collections

Arrays are fixed-size, `Vec<T>` is the growable array, slices (`&[T]`) are
borrowed views, and the standard library provides `HashMap`, `HashSet`,
`BTreeMap`, `VecDeque` and more. The compiler guarantees you never
invalidate an iterator.

## Example

```rust file=example.rs
use std::collections::{BTreeMap, HashMap, HashSet, VecDeque};

fn main() {
    // Vec
    let mut v = vec![5, 2, 8, 1];
    v.push(9);
    v.insert(0, 7);
    println!("{v:?} {} {:?} {:?}", v.len(), v.first(), v.get(99));
    v.sort();
    println!("{v:?} {:?}", v.binary_search(&5));
    v.retain(|&x| x % 2 == 1);
    println!("{v:?}");
    println!("{:?} {:?}", &v[1..3], v.iter().rev().collect::<Vec<_>>());
    println!("{:?}", v.pop());

    // Slices: windows, chunks
    let data = [1, 2, 3, 4, 5];
    println!("{:?}", data.windows(2).map(|w| w[1] - w[0]).collect::<Vec<_>>());
    println!("{:?}", data.chunks(2).collect::<Vec<_>>());

    // Arrays are Copy when their elements are
    let a = [0u8; 4];
    let b = a;
    println!("{a:?} {}", b.len());

    // Sorting with a comparator, dedup, 2-D
    let mut people = vec![("Al", 30), ("Bo", 25), ("Cy", 30)];
    people.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(b.0)));
    println!("{people:?}");
    let mut d = vec![1, 1, 2, 2, 3, 1];
    d.dedup();
    println!("{d:?}");
    let mut grid = vec![vec![0; 3]; 2];
    grid[1][2] = 5;
    println!("{grid:?}");

    // HashMap and the entry API
    let mut ages = HashMap::new();
    ages.insert("ann", 31);
    ages.insert("bob", 25);
    println!("{:?} {:?} {}", ages.get("ann"), ages.get("zed"), ages.contains_key("bob"));
    *ages.entry("ann").or_insert(0) += 1;
    ages.entry("cy").or_insert(40);
    let mut keys: Vec<_> = ages.keys().copied().collect();
    keys.sort();
    println!("{keys:?} {}", ages["ann"]);

    // BTreeMap iterates in key order
    let mut counts: BTreeMap<char, usize> = BTreeMap::new();
    for c in "banana".chars() {
        *counts.entry(c).or_default() += 1;
    }
    println!("{counts:?}");

    // Sets
    let s1: HashSet<i32> = [1, 2, 3].into_iter().collect();
    let s2: HashSet<i32> = [3, 4].into_iter().collect();
    let mut inter: Vec<_> = s1.intersection(&s2).collect();
    inter.sort();
    let mut uni: Vec<_> = s1.union(&s2).copied().collect();
    uni.sort();
    println!("{inter:?} {uni:?}");

    // VecDeque: O(1) at both ends
    let mut dq = VecDeque::new();
    dq.push_back(1);
    dq.push_back(2);
    dq.push_front(0);
    println!("{dq:?}");
    println!("{:?}", dq.pop_front());
}
```

```text output
[7, 5, 2, 8, 1, 9] 6 Some(7) None
[1, 2, 5, 7, 8, 9] Ok(2)
[1, 5, 7, 9]
[5, 7] [9, 7, 5, 1]
Some(9)
[1, 1, 1, 1]
[[1, 2], [3, 4], [5]]
[0, 0, 0, 0] 4
[("Al", 30), ("Cy", 30), ("Bo", 25)]
[1, 2, 3, 1]
[[0, 0, 0], [0, 0, 5]]
Some(31) None true
["ann", "bob", "cy"] 32
{'a': 3, 'b': 1, 'n': 2}
[3] [1, 2, 3, 4]
[0, 1, 2]
Some(0)
```

## Details that bite

- Indexing (`v[i]`) panics when out of bounds; use `get(i)` for a
  `Option`.
- `HashMap` iteration order is random (and differs per run); use
  `BTreeMap` or sort the keys when you need determinism.
- You cannot hold a reference into a `Vec` while pushing to it — the
  borrow checker rejects it, because `push` may reallocate. Store indexes
  or restructure.
- `v.iter()` yields `&T`; `v.into_iter()` yields `T` and consumes `v`;
  `v.iter_mut()` yields `&mut T`.
- `HashMap` keys need `Eq + Hash`; `f64` is neither, so wrap it or use
  integers.
- `vec![x; n]` clones `x` n times: `vec![vec![0; 3]; 2]` is safe, unlike
  the Python/C equivalents, because each row is its own `Vec`.
- Prefer `Vec::with_capacity(n)` when the final size is known.
- `Vec::remove(i)` is O(n); use `swap_remove` when order is irrelevant.

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
