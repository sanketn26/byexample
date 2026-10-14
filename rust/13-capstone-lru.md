# Rust 13 — Capstone: an LRU Cache

A *least-recently-used* cache keeps the N most recently touched entries and
evicts the stalest. In safe Rust a pointer-linked list fights the borrow
checker, so the idiomatic answer is an **index-linked list inside a `Vec`**
(a tiny arena) plus a `HashMap` from key to index. (The same capstone is in
every language of this course; compare how the data structure changes.)

## Example

```rust file=example.rs
use std::collections::HashMap;
use std::hash::Hash;

struct Node<K, V> {
    key: K,
    val: V,
    prev: Option<usize>,
    next: Option<usize>,
}

/// Fixed-capacity cache. head = most recently used, tail = least.
struct Lru<K, V> {
    cap: usize,
    map: HashMap<K, usize>,
    nodes: Vec<Node<K, V>>,
    head: Option<usize>,
    tail: Option<usize>,
}

impl<K: Clone + Eq + Hash, V> Lru<K, V> {
    fn new(cap: usize) -> Self {
        assert!(cap > 0, "capacity must be positive");
        Lru { cap, map: HashMap::new(), nodes: Vec::with_capacity(cap), head: None, tail: None }
    }

    fn detach(&mut self, i: usize) {
        let (p, n) = (self.nodes[i].prev, self.nodes[i].next);
        match p {
            Some(p) => self.nodes[p].next = n,
            None => self.head = n,
        }
        match n {
            Some(n) => self.nodes[n].prev = p,
            None => self.tail = p,
        }
    }

    fn push_front(&mut self, i: usize) {
        self.nodes[i].prev = None;
        self.nodes[i].next = self.head;
        if let Some(h) = self.head {
            self.nodes[h].prev = Some(i);
        }
        self.head = Some(i);
        if self.tail.is_none() {
            self.tail = Some(i);
        }
    }

    fn get(&mut self, key: &K) -> Option<&V> {
        let i = *self.map.get(key)?;
        self.detach(i);
        self.push_front(i);
        Some(&self.nodes[i].val)
    }

    fn put(&mut self, key: K, val: V) {
        if let Some(&i) = self.map.get(&key) {
            self.nodes[i].val = val;
            self.detach(i);
            self.push_front(i);
        } else if self.nodes.len() < self.cap {
            let i = self.nodes.len();
            self.nodes.push(Node { key: key.clone(), val, prev: None, next: None });
            self.map.insert(key, i);
            self.push_front(i);
        } else {
            // Full: recycle the tail's slot instead of allocating
            let i = self.tail.expect("cap > 0 so a tail exists");
            self.detach(i);
            let old = std::mem::replace(&mut self.nodes[i].key, key.clone());
            self.map.remove(&old);
            self.nodes[i].val = val;
            self.map.insert(key, i);
            self.push_front(i);
        }
    }

    fn keys(&self) -> Vec<K> {
        let mut out = Vec::with_capacity(self.nodes.len());
        let mut cur = self.head;
        while let Some(i) = cur {
            out.push(self.nodes[i].key.clone());
            cur = self.nodes[i].next;
        }
        out
    }

    fn len(&self) -> usize {
        self.nodes.len()
    }
}

fn main() {
    let mut c = Lru::new(2);
    c.put("a", 1);
    c.put("b", 2);
    println!("{:?}", c.get(&"a")); // a becomes the newest
    c.put("c", 3); // evicts b
    println!("{:?}", c.get(&"b"));
    println!("{:?} {}", c.keys(), c.len());

    c.put("a", 10);
    let v = c.get(&"a").copied(); // copy out: the &V would keep `c` borrowed
    println!("{v:?} {:?}", c.keys());

    let r = std::panic::catch_unwind(|| Lru::<i32, i32>::new(0));
    println!("{}", r.is_err());
}
```

```text output
Some(1)
None
["c", "a"] 2
Some(10) ["a", "c"]
true
```

## Details that bite

- A `Vec` of nodes addressed by index gives O(1) operations and no
  `unsafe`, no `Rc<RefCell<…>>`. The price is that indexes are not
  checked against stale use: that is why `Lru` never hands them out.
- `get` takes `&mut self` because reading changes recency. If you wrap the
  cache in a `Mutex`, `lock()` is required even for lookups.
- Evicting by *recycling the tail's slot* avoids a second allocation and
  keeps `nodes.len() <= cap`.
- `K: Clone` is needed because the key lives in both the map and the node.
  Store `Rc<K>` (or an intern id) if cloning is expensive.
- The returned `&V` borrows the cache mutably for as long as it lives; copy
  or clone out the value if you need to touch the cache again.
- For production use, reach for the `lru` crate; this is for understanding
  the mechanics.

## Exercises

Implement a **`Vec`-backed** version with `get`, `put`, `peek`, `remove`,
stats, and `keys`.

```rust file=exercise.rs
#![allow(dead_code)] // the stub's fields are unused until you implement it

/// Newest first. O(n) per operation is fine.
struct SimpleLru {
    cap: usize,
    items: Vec<(String, i32)>,
    hits: u32,
    misses: u32,
}

impl SimpleLru {
    fn new(_cap: usize) -> Self {
        todo!()
    }
    /// Value and marks it most recently used; counts a hit or a miss.
    fn get(&mut self, _key: &str) -> Option<i32> {
        todo!()
    }
    /// Insert or update, make newest, evict the oldest when over capacity.
    fn put(&mut self, _key: &str, _val: i32) {
        todo!()
    }
    /// Value without changing recency or stats.
    fn peek(&self, _key: &str) -> Option<i32> {
        todo!()
    }
    /// True if it was present.
    fn remove(&mut self, _key: &str) -> bool {
        todo!()
    }
    /// (hits, misses) counted by get().
    fn stats(&self) -> (u32, u32) {
        todo!()
    }
    /// Most recently used first.
    fn keys(&self) -> Vec<String> {
        todo!()
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
    let mut c = SimpleLru::new(2);
    c.put("a", 1);
    c.put("b", 2);
    let got = c.get("a");
    c.put("c", 3);
    let evicted = c.get("b");
    let k1 = c.keys();
    let peeked = c.peek("a");
    let k2 = c.keys();
    let st = c.stats();
    c.put("a", 10);
    let updated = (c.get("a"), c.keys());
    let removed = (c.remove("c"), c.remove("zzz"), c.keys());
    let results = [
        check("get", got, Some(1)),
        check("evicted", evicted, None),
        check("keys", k1, vec!["c".to_string(), "a".to_string()]),
        check("peek", peeked, Some(1)),
        check("peek keeps order", k2, vec!["c".to_string(), "a".to_string()]),
        check("stats", st, (1, 1)),
        check("update", updated, (Some(10), vec!["a".to_string(), "c".to_string()])),
        check("remove", removed, (true, false, vec!["a".to_string()])),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

<details><summary>Solution</summary>

```rust file=solution.rs
struct SimpleLru {
    cap: usize,
    items: Vec<(String, i32)>,
    hits: u32,
    misses: u32,
}

impl SimpleLru {
    fn new(cap: usize) -> Self {
        assert!(cap > 0, "capacity must be positive");
        SimpleLru { cap, items: Vec::new(), hits: 0, misses: 0 }
    }

    fn index(&self, key: &str) -> Option<usize> {
        self.items.iter().position(|(k, _)| k == key)
    }

    fn get(&mut self, key: &str) -> Option<i32> {
        match self.index(key) {
            Some(i) => {
                self.hits += 1;
                let item = self.items.remove(i);
                let val = item.1;
                self.items.insert(0, item);
                Some(val)
            }
            None => {
                self.misses += 1;
                None
            }
        }
    }

    fn put(&mut self, key: &str, val: i32) {
        if let Some(i) = self.index(key) {
            self.items.remove(i);
        }
        self.items.insert(0, (key.to_string(), val));
        self.items.truncate(self.cap);
    }

    fn peek(&self, key: &str) -> Option<i32> {
        self.index(key).map(|i| self.items[i].1)
    }

    fn remove(&mut self, key: &str) -> bool {
        match self.index(key) {
            Some(i) => {
                self.items.remove(i);
                true
            }
            None => false,
        }
    }

    fn stats(&self) -> (u32, u32) {
        (self.hits, self.misses)
    }

    fn keys(&self) -> Vec<String> {
        self.items.iter().map(|(k, _)| k.clone()).collect()
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
    let mut c = SimpleLru::new(2);
    c.put("a", 1);
    c.put("b", 2);
    let got = c.get("a");
    c.put("c", 3);
    let evicted = c.get("b");
    let k1 = c.keys();
    let peeked = c.peek("a");
    let k2 = c.keys();
    let st = c.stats();
    c.put("a", 10);
    let updated = (c.get("a"), c.keys());
    let removed = (c.remove("c"), c.remove("zzz"), c.keys());
    let results = [
        check("get", got, Some(1)),
        check("evicted", evicted, None),
        check("keys", k1, vec!["c".to_string(), "a".to_string()]),
        check("peek", peeked, Some(1)),
        check("peek keeps order", k2, vec!["c".to_string(), "a".to_string()]),
        check("stats", st, (1, 1)),
        check("update", updated, (Some(10), vec!["a".to_string(), "c".to_string()])),
        check("remove", removed, (true, false, vec!["a".to_string()])),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

</details>

Back to the [course index](README.md)
