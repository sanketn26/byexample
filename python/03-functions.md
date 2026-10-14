# Python 03 — Functions

Functions are first-class objects: you can pass them, return them, and store
them in data structures.

## Example

```python file=example.py
# Defaults, keyword arguments, *args and **kwargs
def greet(name, greeting="Hello", *, punct="!"):
    return f"{greeting}, {name}{punct}"

print(greet("Ada"))
print(greet("Ada", "Hi", punct="?"))

def summarize(*nums, **opts):
    total = sum(nums)
    return total if not opts.get("double") else total * 2

print(summarize(1, 2, 3), summarize(1, 2, 3, double=True))

# Multiple return values are just a tuple
def min_max(xs):
    return min(xs), max(xs)

lo, hi = min_max([4, 9, 2])
print(lo, hi)

# Unpacking into a call
args = [1, 2, 3]
print(summarize(*args), greet(**{"name": "Bob", "greeting": "Yo"}))

# Closures capture variables, not values
def counter():
    count = 0
    def inc():
        nonlocal count
        count += 1
        return count
    return inc

c = counter()
print(c(), c(), c())

# Higher-order functions and lambdas
words = ["pear", "fig", "banana", "kiwi"]
print(sorted(words, key=len))
print(list(map(str.upper, words[:2])))
print(list(filter(lambda w: len(w) == 4, words)))

# Decorators wrap functions
import functools

def logged(fn):
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        print(f"calling {fn.__name__}{a}")
        return fn(*a, **kw)
    return wrapper

@logged
def add(a, b):
    return a + b

print(add(2, 3))

# THE classic trap: mutable default arguments are created once
def append_bad(x, bucket=[]):
    bucket.append(x)
    return bucket

print(append_bad(1), append_bad(2))

def append_good(x, bucket=None):
    if bucket is None:
        bucket = []
    bucket.append(x)
    return bucket

print(append_good(1), append_good(2))

# Late binding in closures
fns = [lambda: i for i in range(3)]
print([f() for f in fns])
fns = [lambda i=i: i for i in range(3)]
print([f() for f in fns])

# Generators produce values lazily
def fib():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

from itertools import islice
print(list(islice(fib(), 8)))
```

```text output
Hello, Ada!
Hi, Ada?
6 12
2 9
6 Yo, Bob!
1 2 3
['fig', 'pear', 'kiwi', 'banana']
['PEAR', 'FIG']
['pear', 'kiwi']
calling add(2, 3)
5
[1, 2] [1, 2]
[1] [2]
[2, 2, 2]
[0, 1, 2]
[0, 1, 1, 2, 3, 5, 8, 13]
```

## Details that bite

- Default values are evaluated **once**, at definition time. Use `None` as a
  sentinel for mutable defaults.
- Closures see the *variable*, so lambdas created in a loop all share the
  final value; bind with a default argument (`lambda i=i: i`).
- Assigning to a name inside a function makes it local. Use `nonlocal` /
  `global` to rebind outer names. Mutating (`lst.append`) needs neither.
- Arguments are passed by *object reference*: rebinding a parameter does not
  affect the caller, but mutating the object does.
- `*` in a signature makes later parameters keyword-only; `/` makes earlier
  ones positional-only.

## Exercises

```python file=exercise.py
def compose(*fns):
    """compose(f, g, h)(x) == f(g(h(x))). compose() is the identity."""
    raise NotImplementedError


def make_accumulator(start=0):
    """Return a function; each call adds its argument and returns the total."""
    raise NotImplementedError


def chunks(seq, size):
    """Generator yielding successive lists of at most `size` items."""
    raise NotImplementedError


def memoize(fn):
    """Return a wrapper caching results by positional args (hashable)."""
    raise NotImplementedError


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


calls = []

@memoize
def slow_square(n):
    calls.append(n)
    return n * n


def run():
    inc = lambda x: x + 1
    dbl = lambda x: x * 2
    acc = make_accumulator(10)
    acc(5)
    out = [
        check("compose", compose(inc, dbl)(5), 11),
        check("compose()", compose()(7), 7),
        check("accumulator", acc(5), 20),
        check("chunks", list(chunks([1, 2, 3, 4, 5], 2)), [[1, 2], [3, 4], [5]]),
    ]
    slow_square(4); slow_square(4)
    out.append(check("memoize", (slow_square(4), calls), (16, [4])))
    return out


raise SystemExit(0 if all(run()) else 1)
```

<details><summary>Solution</summary>

```python file=solution.py
import functools


def compose(*fns):
    def composed(x):
        for fn in reversed(fns):
            x = fn(x)
        return x
    return composed


def make_accumulator(start=0):
    total = start
    def add(n):
        nonlocal total
        total += n
        return total
    return add


def chunks(seq, size):
    for i in range(0, len(seq), size):
        yield list(seq[i:i + size])


def memoize(fn):
    cache = {}
    @functools.wraps(fn)
    def wrapper(*args):
        if args not in cache:
            cache[args] = fn(*args)
        return cache[args]
    return wrapper


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


calls = []

@memoize
def slow_square(n):
    calls.append(n)
    return n * n


def run():
    inc = lambda x: x + 1
    dbl = lambda x: x * 2
    acc = make_accumulator(10)
    acc(5)
    out = [
        check("compose", compose(inc, dbl)(5), 11),
        check("compose()", compose()(7), 7),
        check("accumulator", acc(5), 20),
        check("chunks", list(chunks([1, 2, 3, 4, 5], 2)), [[1, 2], [3, 4], [5]]),
    ]
    slow_square(4); slow_square(4)
    out.append(check("memoize", (slow_square(4), calls), (16, [4])))
    return out


raise SystemExit(0 if all(run()) else 1)
```

</details>

Next: [04 — Collections](04-collections.md)
