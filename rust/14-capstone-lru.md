# Rust 14 — Capstone: an LRU Cache

A least-recently-used cache keeps the N most recently touched entries and
evicts the stalest. A pointer-linked list fights the borrow checker, so the
cache is an index-linked list inside a `Vec` (a tiny arena) plus a `HashMap`
from key to index. Indexes stay inside the cache. Handing one out would let
it go stale. `get` takes `&mut self` because a read changes recency. Behind
a `Mutex`, even a lookup needs the lock. For production, use the `lru`
crate. This is the mechanism.

## The node and the map are the cache

`head` is the newest index. `tail` is the oldest. `put` of a new key pushes
it at the head. `K: Clone` is required because the key lives in the map and
in the node. Store `Rc<K>` if cloning is expensive. Capacity has to be
positive.

```rust file=n01.rs
use std::collections::HashMap;
use std::hash::Hash;

struct Node<K, V> {
    key: K,
    val: V,
    prev: Option<usize>,
    next: Option<usize>,
}

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
        Lru {
            cap,
            map: HashMap::new(),
            nodes: Vec::with_capacity(cap),
            head: None,
            tail: None,
        }
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
}

fn main() {
    let mut c = Lru::new(2);
    c.put("a", 1);
    c.put("b", 2);
    println!("{:?} {}", c.keys(), c.nodes.len());
}
```

```text output
["b", "a"] 2
```

## `get` moves the hit to the front

Reading changes order. The returned `&V` borrows the cache for as long as
the reference lives, so this print finishes before the next mutation.

```rust file=n02.rs
use std::collections::HashMap;
use std::hash::Hash;

struct Node<K, V> {
    key: K,
    val: V,
    prev: Option<usize>,
    next: Option<usize>,
}

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
        Lru {
            cap,
            map: HashMap::new(),
            nodes: Vec::with_capacity(cap),
            head: None,
            tail: None,
        }
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
}

fn main() {
    let mut c = Lru::new(2);
    c.put("a", 1);
    c.put("b", 2);
    println!("{:?}", c.get(&"a"));
    println!("{:?}", c.keys());
}
```

```text output
Some(1)
["a", "b"]
```

## A full cache recycles the tail's slot

The third `put` evicts `b`, the least recently used key, and reuses that
node. `nodes.len()` stays at the capacity. No second allocation.

```rust file=n03.rs
use std::collections::HashMap;
use std::hash::Hash;

struct Node<K, V> {
    key: K,
    val: V,
    prev: Option<usize>,
    next: Option<usize>,
}

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
        Lru {
            cap,
            map: HashMap::new(),
            nodes: Vec::with_capacity(cap),
            head: None,
            tail: None,
        }
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
}

fn main() {
    let mut c = Lru::new(2);
    c.put("a", 1);
    c.put("b", 2);
    assert!(c.get(&"a").is_some());
    c.put("c", 3);
    println!("{:?}", c.get(&"b"));
    println!("{:?} {}", c.keys(), c.nodes.len());
}
```

```text output
None
["c", "a"] 2
```

## Copy the value out before you touch the cache again

`put` of a key that is already present replaces the value and moves that
node to the front. The `&V` from `get` holds a mutable borrow. `.copied()`
ends it, which is what lets `keys` run on the next line.

```rust file=n04.rs
use std::collections::HashMap;
use std::hash::Hash;

struct Node<K, V> {
    key: K,
    val: V,
    prev: Option<usize>,
    next: Option<usize>,
}

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
        Lru {
            cap,
            map: HashMap::new(),
            nodes: Vec::with_capacity(cap),
            head: None,
            tail: None,
        }
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
}

fn main() {
    let mut c = Lru::new(2);
    c.put("a", 1);
    c.put("b", 2);
    c.get(&"a");
    c.put("c", 3);
    c.put("a", 10);
    let v = c.get(&"a").copied();
    println!("{v:?} {:?}", c.keys());
}
```

```text output
Some(10) ["a", "c"]
```

## Zero capacity is a bug

The constructor panics. That is a programmer error, not a cache miss. The
hook keeps the panic text off the terminal. The `bool` is the result.

```rust file=n05.rs
use std::marker::PhantomData;

struct Lru<K, V> {
    cap: usize,
    _kind: PhantomData<(K, V)>,
}

impl<K, V> Lru<K, V> {
    fn new(cap: usize) -> Self {
        assert!(cap > 0, "capacity must be positive");
        Lru { cap, _kind: PhantomData }
    }
}

fn main() {
    std::panic::set_hook(Box::new(|_| {}));
    let r = std::panic::catch_unwind(|| Lru::<i32, i32>::new(0));
    let ok = Lru::<i32, i32>::new(2);
    println!("{} {}", r.is_err(), ok.cap);
}
```

```text output
true 2
```

## The same steps, one after another

Touch `a`, insert `c` (which evicts `b`), replace `a`, and copy the value
out before listing the keys.

```rust file=n06.rs
use std::collections::HashMap;
use std::hash::Hash;

struct Node<K, V> {
    key: K,
    val: V,
    prev: Option<usize>,
    next: Option<usize>,
}

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
        Lru {
            cap,
            map: HashMap::new(),
            nodes: Vec::with_capacity(cap),
            head: None,
            tail: None,
        }
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
}

fn main() {
    let mut c = Lru::new(2);
    c.put("a", 1);
    c.put("b", 2);
    println!("{:?}", c.get(&"a"));
    c.put("c", 3);
    println!("{:?}", c.get(&"b"));
    println!("{:?} {}", c.keys(), c.nodes.len());
    c.put("a", 10);
    let v = c.get(&"a").copied();
    println!("{v:?} {:?}", c.keys());
    std::panic::set_hook(Box::new(|_| {}));
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

Next: [15 — Streaming](15-streaming.md)
