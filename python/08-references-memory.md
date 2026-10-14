# Python 08 — References, Mutability and Memory

Names point to objects. Understanding identity, mutability and reference
counting explains most "spooky" Python bugs.

## Example

```python file=example.py
import sys
import gc
import weakref

# Identity vs equality
a = [1, 2, 3]
b = a
c = [1, 2, 3]
print(a is b, a is c, a == c, id(a) == id(b))

# Mutating through an alias
b.append(4)
print(a)

# Rebinding does not affect the other name
b = [0]
print(a, b)

# Immutable objects: "modification" creates a new object
s = "ab"
before = id(s)
s += "c"
print(id(s) == before)

# Functions receive references
def mutate(xs):
    xs.append("m")          # visible to caller

def rebind(xs):
    xs = ["new"]            # local only
    return xs

data = []
mutate(data)
rebind(data)
print(data)

# Reference counting
x = object()
print(sys.getrefcount(x) - 1)   # minus the temporary argument reference
y = x
print(sys.getrefcount(x) - 1)
del y
print(sys.getrefcount(x) - 1)

# Cycles need the garbage collector
class Node:
    def __init__(self):
        self.other = None

n1, n2 = Node(), Node()
n1.other, n2.other = n2, n1
probe = weakref.ref(n1)
del n1, n2
print(probe() is not None)      # still alive: refcount never hit zero
gc.collect()
print(probe() is None)          # cycle collector reclaimed it

# Weak references do not keep objects alive
class Big:
    pass

obj = Big()
w = weakref.ref(obj)
print(w() is obj)
del obj
print(w())

# Small-int / interned-string caching is an optimisation, not a contract
p, q = 256, 256
print(p is q)                   # True in CPython, but never rely on this

# Hidden sharing between containers
row = [0, 0]
grid = [row, row]
grid[0][0] = 9
print(grid)

# Hashability follows mutability
try:
    {[1, 2]: "no"}
except TypeError as e:
    print(e)

# Sizes (CPython 3.12 on 64-bit; the exact numbers vary by version/platform)
print(sys.getsizeof([]), sys.getsizeof([1, 2, 3]) > sys.getsizeof([]))

# __slots__ trades flexibility for memory
class P2:
    pass
class P3:
    __slots__ = ("x",)
print(hasattr(P2(), "__dict__"), hasattr(P3(), "__dict__"))
```

```text output
True False True True
[1, 2, 3, 4]
[1, 2, 3, 4] [0]
False
['m']
1
2
1
True
True
True
None
True
[[9, 0], [9, 0]]
unhashable type: 'list'
56 True
True False
```

## Details that bite

- `sys.getsizeof` is shallow: a list's size excludes the objects inside.
- `is` on ints and strings may be `True` because of caching. Only use `is`
  with `None`, `True`/`False`, and sentinels you created.
- `a += b` on a list *mutates in place* (aliases see it); on a tuple or str
  it rebinds.
- `copy.copy` / `list(x)` / `x[:]` are shallow; nested objects stay shared.
- `__del__` is not a reliable destructor; use context managers.
- Large temporary structures stay alive as long as any name references them
  — `del name` or narrowing scope releases them.

## Exercises

```python file=exercise.py
def append_unique(items, value):
    """Append value to `items` IN PLACE if absent. Return True if appended."""
    raise NotImplementedError


def with_added(items, value):
    """Return a NEW list with value appended; do not modify `items`."""
    raise NotImplementedError


def deep_flatten(nested):
    """Flatten arbitrarily nested lists: [1,[2,[3]],4] -> [1,2,3,4]."""
    raise NotImplementedError


def clone_matrix(m):
    """Return a deep copy of a list of lists WITHOUT importing copy."""
    raise NotImplementedError


def share_count(a, b):
    """Return how many top-level elements of lists a and b are the SAME object
    (identity) at the same index."""
    raise NotImplementedError


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


def run():
    xs = [1, 2]
    r1 = append_unique(xs, 3)
    r2 = append_unique(xs, 3)
    orig = [1]
    new = with_added(orig, 2)
    m = [[1, 2], [3]]
    c = clone_matrix(m)
    c[0].append(99)
    inner = [0]
    return [
        check("append_unique", (xs, r1, r2), ([1, 2, 3], True, False)),
        check("with_added", (orig, new), ([1], [1, 2])),
        check("deep_flatten", deep_flatten([1, [2, [3, []]], 4]), [1, 2, 3, 4]),
        check("clone_matrix", (m, c), ([[1, 2], [3]], [[1, 2, 99], [3]])),
        check("share_count", share_count([inner, [1]], [inner, [1]]), 1),
    ]


raise SystemExit(0 if all(run()) else 1)
```

<details><summary>Solution</summary>

```python file=solution.py
def append_unique(items, value):
    if value in items:
        return False
    items.append(value)
    return True


def with_added(items, value):
    return [*items, value]


def deep_flatten(nested):
    out = []
    for item in nested:
        if isinstance(item, list):
            out.extend(deep_flatten(item))
        else:
            out.append(item)
    return out


def clone_matrix(m):
    return [list(row) for row in m]


def share_count(a, b):
    return sum(1 for x, y in zip(a, b) if x is y)


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


def run():
    xs = [1, 2]
    r1 = append_unique(xs, 3)
    r2 = append_unique(xs, 3)
    orig = [1]
    new = with_added(orig, 2)
    m = [[1, 2], [3]]
    c = clone_matrix(m)
    c[0].append(99)
    inner = [0]
    return [
        check("append_unique", (xs, r1, r2), ([1, 2, 3], True, False)),
        check("with_added", (orig, new), ([1], [1, 2])),
        check("deep_flatten", deep_flatten([1, [2, [3, []]], 4]), [1, 2, 3, 4]),
        check("clone_matrix", (m, c), ([[1, 2], [3]], [[1, 2, 99], [3]])),
        check("share_count", share_count([inner, [1]], [inner, [1]]), 1),
    ]


raise SystemExit(0 if all(run()) else 1)
```

</details>

Next: [09 — Protocols and abstraction](09-protocols.md)
