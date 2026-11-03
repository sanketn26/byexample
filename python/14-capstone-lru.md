# Python 14 — Capstone: an LRU Cache

A *least-recently-used* cache keeps the N most recently touched entries and
evicts the stalest. It exercises classes, dunder methods, error handling and
a data-structure choice: here `OrderedDict` gives O(1) reorder and evict.
(The same capstone appears in every language in this course; compare how the
data structure changes.)

## Example

```python file=example.py
import functools
from collections import OrderedDict


class LRUCache:
    """Maps keys to values, evicting the least recently used when full."""

    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._data = OrderedDict()          # oldest first, newest last

    def get(self, key, default=None):
        if key not in self._data:
            return default
        self._data.move_to_end(key)         # touching makes it newest
        return self._data[key]

    def put(self, key, value):
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)  # evict the oldest

    def keys(self):
        """Keys from most to least recently used."""
        return list(reversed(self._data))

    def __contains__(self, key):            # does NOT count as a use
        return key in self._data

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return f"LRUCache({dict(self._data)!r}, capacity={self.capacity})"


c = LRUCache(2)
c.put("a", 1)
c.put("b", 2)
print(c.get("a"))        # a becomes the newest
c.put("c", 3)            # evicts b, the least recently used
print(c.get("b"))
print(c.keys())
print("a" in c, len(c))
print(c)

try:
    LRUCache(0)
except ValueError as e:
    print("error:", e)

# The standard library already ships one for function results
@functools.lru_cache(maxsize=2)
def square(n):
    return n * n

square(1); square(2); square(1); square(3)   # 3 evicts 2
print(square.cache_info())
```

```text output
1
None
['c', 'a']
True 2
LRUCache({'a': 1, 'c': 3}, capacity=2)
error: capacity must be positive
CacheInfo(hits=1, misses=3, maxsize=2, currsize=2)
```

## Details that bite

- Two O(1) operations are needed: lookup by key and "move to newest".
  Hash map + doubly linked list is the classic answer; `OrderedDict`
  already is one.
- Decide whether `in` and `peek` count as a use. Most caches say no.
- Caches hold references: values stay alive until evicted. Use
  `weakref.WeakValueDictionary` if that is not what you want.
- A cache shared between threads needs a lock; `lru_cache` is
  thread-safe, `OrderedDict` operations are not atomic as a group.
- Unhashable keys (lists, dicts) raise `TypeError`; the caller must
  convert to tuples.

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
