# Python 08 — References, Mutability and Memory

Names point to objects. Identity, mutability, and reference counting explain
most of the spooky bugs.

## `is` tests identity, `==` tests equality

Two equal lists are not the same object. `id` is that identity as an
integer. Use `is` for `None`, not for values.

```python file=n01.py
a = [1, 2, 3]
b = a
c = [1, 2, 3]
print(a is b, a is c, a == c, id(a) == id(b))
```

```text output
True False True True
```

## Mutation shows through every alias

`append` changes the object both names point at. Rebinding `b` points that
name at a new object and leaves `a` alone.

```python file=n02.py
a = [1, 2, 3]
b = a
b.append(4)
print(a)
b = [0]
print(a, b)
```

```text output
[1, 2, 3, 4]
[1, 2, 3, 4] [0]
```

## An immutable update builds a new object

`s += "c"` does not edit the old string. It rebinds `s`, so the id changes.

```python file=n03.py
s = "ab"
before = id(s)
s += "c"
print(id(s) == before)
```

```text output
False
```

## `+=` mutates a list and rebinds a tuple

On a list, `+=` updates the object in place, so aliases see it. On a tuple
or a string it rebinds the name, and the old object stays as it was.

```python file=n04.py
a = [1]
b = a
a += [2]
print(a, b, a is b)
t = (1,)
u = t
t += (2,)
print(u, t, t is u)
```

```text output
[1, 2] [1, 2] True
(1,) (1, 2) False
```

## A function receives the object, not a copy

Appending inside the function changes the caller's list. Assigning to the
parameter rebinds the local name only.

```python file=n05.py
def mutate(xs):
    xs.append("m")


def rebind(xs):
    xs = ["new"]
    return xs


data = []
mutate(data)
rebind(data)
print(data)
```

```text output
['m']
```

## Reference counting frees an object at zero

`sys.getrefcount` includes the temporary reference from the call, so
subtract one. Binding another name increases the count. `del` drops a name.

```python file=n06.py
import sys

x = object()
print(sys.getrefcount(x) - 1)
y = x
print(sys.getrefcount(x) - 1)
del y
print(sys.getrefcount(x) - 1)
```

```text output
1
2
1
```

## A cycle waits for the garbage collector

Two objects pointing at each other never hit a zero count, so the cycle
collector has to find them. A `weakref` watches that without keeping the
object alive.

```python file=n07.py
import gc
import weakref


class Node:
    def __init__(self):
        self.other = None


n1, n2 = Node(), Node()
n1.other, n2.other = n2, n1
probe = weakref.ref(n1)
del n1, n2
print(probe() is not None)
gc.collect()
print(probe() is None)
```

```text output
True
True
```

## A weak reference does not keep the object alive

After the last strong name is gone, calling the weakref returns `None`.

```python file=n08.py
import weakref


class Big:
    pass


obj = Big()
w = weakref.ref(obj)
print(w() is obj)
del obj
print(w())
```

```text output
True
None
```

## Interning is an optimisation, not a contract

CPython may make `is` true for small integers and for some strings. Only
use `is` with `None`, `True`, `False`, and sentinels you created.

```python file=n09.py
p, q = 256, 256
print(p == q, p is q)
a = int("1000")
b = int("1000")
print(a == b, a is b)
left = "hello"
right = "".join(["he", "llo"])
print(left == right, left is right)
```

```text output
True True
True False
True False
```

## Two slots can share one inner list

`grid = [row, row]` is two names for one row. Writing through either
index changes both.

```python file=n10.py
row = [0, 0]
grid = [row, row]
grid[0][0] = 9
print(grid)
```

```text output
[[9, 0], [9, 0]]
```

## Hashability follows from immutability

A list cannot be a dict key. The error says the type is unhashable.

```python file=n11.py
try:
    {[1, 2]: "no"}
except TypeError as e:
    print(e)
```

```text output
cannot use 'list' as a dict key (unhashable type: 'list')
```

## `getsizeof` does not include the contents

The number is the container itself. A longer list is bigger than an empty
one, but neither figure counts the objects stored inside. The exact empty
size depends on the version and the platform.

```python file=n12.py
import sys

print(sys.getsizeof([]), sys.getsizeof([1, 2, 3]) > sys.getsizeof([]))
```

```text output
56 True
```

## `__slots__` omits `__dict__`

Instances then have only the names you listed. A normal instance carries
a `__dict__` that accepts any attribute.

```python file=n13.py
class P2:
    pass


class P3:
    __slots__ = ("x",)


print(hasattr(P2(), "__dict__"), hasattr(P3(), "__dict__"))
```

```text output
True False
```

## `del` drops a name, not every alias

The object stays alive while any name still points at it. `del` on the
last name, or leaving the scope, releases it.

```python file=n14.py
temp = [1, 2, 3]
alias = temp
del temp
print(alias)
try:
    print(temp)
except NameError as e:
    print(type(e).__name__)
```

```text output
[1, 2, 3]
NameError
```

## `__del__` is not a destructor

It may run late, or never, when a cycle keeps the object. A context
manager releases the resource at a known line.

```python file=n15.py
class Box:
    def __init__(self):
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.closed = True
        return False


with Box() as box:
    print("open", box.closed)
print("closed", box.closed)
```

```text output
open False
closed True
```

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
