# Python 14 — Capstone: an LRU Cache

A least-recently-used cache keeps the N most recently touched entries and
evicts the stalest. Lookup and "move to newest" both have to be O(1). A
hash map plus a doubly linked list is the classic pair. `OrderedDict` is
that pair already.

## `OrderedDict` moves a key and drops the oldest

`move_to_end` is the "just used" operation. `popitem(last=False)` evicts
the other end. Both are O(1).

```python file=n01.py
from collections import OrderedDict

data = OrderedDict()
data["a"] = 1
data["b"] = 2
data.move_to_end("a")
print(list(data))
print(data.popitem(last=False))
print(list(data))
```

```text output
['b', 'a']
('b', 2)
['a']
```

## `get` makes the key newest

A hit moves the key to the end. A miss returns the default and does not
insert anything. The key list below is newest first.

```python file=n02.py
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self._data = OrderedDict()

    def get(self, key, default=None):
        if key not in self._data:
            return default

        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key, value):
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value

    def keys(self):
        return list(reversed(self._data))


c = LRUCache(2)
c.put("a", 1)
c.put("b", 2)
print(c.keys(), c.get("missing"))
print(c.get("a"))
print(c.keys())
```

```text output
['b', 'a'] None
1
['a', 'b']
```

## A full `put` evicts the least recently used

After `get("a")`, `b` is the oldest. The next new key drops `b`. Putting
a key that is already present refreshes it instead of growing the cache.

```python file=n03.py
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self._data = OrderedDict()

    def get(self, key, default=None):
        if key not in self._data:
            return default
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key, value):
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)

    def keys(self):
        return list(reversed(self._data))


c = LRUCache(2)
c.put("a", 1)
c.put("b", 2)
c.get("a")
c.put("c", 3)
print(c.get("b"), c.keys())
c.put("a", 10)
print(c.get("a"), c.keys())
```

```text output
None ['c', 'a']
10 ['a', 'c']
```

## `in` does not count as a use

Membership answers "is it stored?" and leaves the order alone. A `peek`
should do the same. Most caches treat only `get` and `put` as a use.

```python file=n04.py
from collections import OrderedDict


class LRUCache:
    def __init__(self):
        self._data = OrderedDict()

    def put(self, key, value):
        self._data[key] = value

    def keys(self):
        return list(reversed(self._data))

    def __contains__(self, key):
        return key in self._data


c = LRUCache()
c.put("a", 1)
c.put("b", 2)
print("a" in c, c.keys())
```

```text output
True ['b', 'a']
```

## Capacity has to be positive

Zero would evict every insert, and a negative size is meaningless. Raise
`ValueError` before building the map.

```python file=n05.py
def check(capacity):
    if capacity <= 0:
        raise ValueError("capacity must be positive")


try:
    check(0)
except ValueError as e:
    print("error:", e)
```

```text output
error: capacity must be positive
```

## The key has to be hashable

The map is a dict. A list or a dict as a key raises `TypeError`. The
caller converts those to tuples.

```python file=n06.py
from collections import OrderedDict

data = OrderedDict()
try:
    data[["a"]] = 1
except TypeError as e:
    print(type(e).__name__)
data[("a",)] = 1
print(data[("a",)])
```

```text output
TypeError
1
```

## The cache keeps the value alive

A stored value stays reachable until it is evicted or replaced. That is
what you want for a normal cache, and it is a leak when the value is
huge. `weakref.WeakValueDictionary` is the version that does not keep it.

```python file=n07.py
import weakref


class Box:
    pass


box = Box()
held = box
probe = weakref.ref(box)
del box
print(probe() is held)
del held
print(probe() is None)
```

```text output
True
True
```

## `lru_cache` is the same policy for functions

`maxsize` is the capacity. `cache_info` reports hits, misses, and how
many entries are stored. This decorator is safe to call from several
threads. A hand-rolled `OrderedDict` cache is not: `get` is several
steps, so share it only under a lock.

```python file=n08.py
import functools


@functools.lru_cache(maxsize=2)
def square(n):
    return n * n


square(1)
square(2)
square(1)
square(3)
print(square.cache_info())
```

```text output
CacheInfo(hits=1, misses=3, maxsize=2, currsize=2)
```

## The pieces are one cache

`get` refreshes, `put` evicts the oldest when the dict grows past
capacity, and `in` still does not refresh. The repr shows oldest first,
because that is `OrderedDict`'s order.

```python file=n09.py
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._data = OrderedDict()

    def get(self, key, default=None):
        if key not in self._data:
            return default
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key, value):
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)

    def keys(self):
        return list(reversed(self._data))

    def __contains__(self, key):
        return key in self._data

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return f"LRUCache({dict(self._data)!r}, capacity={self.capacity})"


c = LRUCache(2)
c.put("a", 1)
c.put("b", 2)
print(c.get("a"))
c.put("c", 3)
print(c.get("b"))
print(c.keys())
print("a" in c, len(c))
print(c)
```

```text output
1
None
['c', 'a']
True 2
LRUCache({'a': 1, 'c': 3}, capacity=2)
```

## Exercises

Implement the same API **without** `OrderedDict`, using a plain list, and
add `peek`, `remove` and hit/miss statistics.

```python file=exercise.py
class SimpleLRU:
    """put/get like LRUCache, plus:
      peek(key, default=None)  -- value without changing recency or stats
      remove(key)              -- True if it was present
      stats()                  -- (hits, misses) counted by get() only
      keys()                   -- most recently used first
    """

    def __init__(self, capacity):
        raise NotImplementedError

    def get(self, key, default=None):
        raise NotImplementedError

    def put(self, key, value):
        raise NotImplementedError

    def peek(self, key, default=None):
        raise NotImplementedError

    def remove(self, key):
        raise NotImplementedError

    def stats(self):
        raise NotImplementedError

    def keys(self):
        raise NotImplementedError


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


def run():
    c = SimpleLRU(2)
    c.put("a", 1)
    c.put("b", 2)
    out = [check("get", c.get("a"), 1)]
    c.put("c", 3)
    out += [
        check("evicted", c.get("b", "gone"), "gone"),
        check("keys", c.keys(), ["c", "a"]),
        check("peek", c.peek("a"), 1),
        check("peek keeps order", c.keys(), ["c", "a"]),
        check("stats", c.stats(), (1, 1)),
    ]
    c.put("a", 10)                 # update refreshes recency
    out += [
        check("update", (c.get("a"), c.keys()), (10, ["a", "c"])),
        check("remove", (c.remove("c"), c.remove("zzz"), c.keys()), (True, False, ["a"])),
    ]
    try:
        SimpleLRU(0)
        out.append(check("capacity", "no error", "ValueError"))
    except ValueError:
        out.append(check("capacity", "ValueError", "ValueError"))
    return out


raise SystemExit(0 if all(run()) else 1)
```

<details><summary>Solution</summary>

```python file=solution.py
class SimpleLRU:
    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._items = []            # [(key, value)], newest first
        self._hits = self._misses = 0

    def _index(self, key):
        for i, (k, _) in enumerate(self._items):
            if k == key:
                return i
        return -1

    def get(self, key, default=None):
        i = self._index(key)
        if i < 0:
            self._misses += 1
            return default
        self._hits += 1
        self._items.insert(0, self._items.pop(i))
        return self._items[0][1]

    def put(self, key, value):
        i = self._index(key)
        if i >= 0:
            self._items.pop(i)
        self._items.insert(0, (key, value))
        del self._items[self.capacity:]

    def peek(self, key, default=None):
        i = self._index(key)
        return self._items[i][1] if i >= 0 else default

    def remove(self, key):
        i = self._index(key)
        if i < 0:
            return False
        del self._items[i]
        return True

    def stats(self):
        return self._hits, self._misses

    def keys(self):
        return [k for k, _ in self._items]


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


def run():
    c = SimpleLRU(2)
    c.put("a", 1)
    c.put("b", 2)
    out = [check("get", c.get("a"), 1)]
    c.put("c", 3)
    out += [
        check("evicted", c.get("b", "gone"), "gone"),
        check("keys", c.keys(), ["c", "a"]),
        check("peek", c.peek("a"), 1),
        check("peek keeps order", c.keys(), ["c", "a"]),
        check("stats", c.stats(), (1, 1)),
    ]
    c.put("a", 10)                 # update refreshes recency
    out += [
        check("update", (c.get("a"), c.keys()), (10, ["a", "c"])),
        check("remove", (c.remove("c"), c.remove("zzz"), c.keys()), (True, False, ["a"])),
    ]
    try:
        SimpleLRU(0)
        out.append(check("capacity", "no error", "ValueError"))
    except ValueError:
        out.append(check("capacity", "ValueError", "ValueError"))
    return out


raise SystemExit(0 if all(run()) else 1)
```

</details>

Next: [15 — Streaming](15-streaming.md)
