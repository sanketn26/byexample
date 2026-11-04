# Python 03 — Functions

Functions are first-class objects: you can pass them, return them, and store
them in data structures.

## Some parameters are optional or keyword-only

A default is fixed when the function is defined, not when it is called.
`*` makes every following parameter keyword-only. `/` makes the parameters
before it positional-only. `*args` collects extra positionals and `**kwargs`
collects extra keywords.

```python file=n01.py
def greet(name, greeting="Hello", *, punct="!"):
    return f"{greeting}, {name}{punct}"


def summarize(*nums, **opts):
    total = sum(nums)
    return total if not opts.get("double") else total * 2


def div(a, b, /):
    return a // b


print(greet("Ada"))
print(greet("Ada", "Hi", punct="?"))
print(summarize(1, 2, 3), summarize(1, 2, 3, double=True))
print(div(7, 2))
try:
    greet("Ada", "Hi", "?")
except TypeError as e:
    print("keyword-only", type(e).__name__)
try:
    div(a=7, b=2)
except TypeError as e:
    print("positional-only", type(e).__name__)
```

```text output
Hello, Ada!
Hi, Ada?
6 12
3
keyword-only TypeError
positional-only TypeError
```

## Several return values are one tuple

`return a, b` builds a tuple. The caller unpacks it into names.

```python file=n02.py
def min_max(xs):
    return min(xs), max(xs)


lo, hi = min_max([4, 9, 2])
print(lo, hi)
```

```text output
2 9
```

## A call can unpack a sequence or a mapping

`*seq` fills positional arguments. `**mapping` fills keyword arguments.

```python file=n03.py
def greet(name, greeting="Hello", *, punct="!"):
    return f"{greeting}, {name}{punct}"


def summarize(*nums, **opts):
    total = sum(nums)
    return total if not opts.get("double") else total * 2


args = [1, 2, 3]
print(summarize(*args), greet(**{"name": "Bob", "greeting": "Yo"}))
```

```text output
6 Yo, Bob!
```

## A closure sees the variable, not a copy

The inner function reads `count` from the enclosing scope. `nonlocal` lets
it assign to that name. An assignment without `nonlocal` would make a new
local instead.

```python file=n04.py
def counter():
    count = 0

    def inc():
        nonlocal count
        count += 1
        return count

    return inc


c = counter()
print(c(), c(), c())
```

```text output
1 2 3
```

## Assignment makes a name local

`global` rebinds a module-level name. Mutating an object needs neither
`global` nor `nonlocal`. Reading a name you also assign, with no declaration,
raises `UnboundLocalError`.

```python file=n05.py
count = 0
items = []


def bump():
    global count
    count += 1


def add(x):
    items.append(x)


def local_trap():
    count += 1


bump()
add(1)
print(count, items)
try:
    local_trap()
except UnboundLocalError as e:
    print(type(e).__name__)
```

```text output
1 [1]
UnboundLocalError
```

## Functions are values

Pass them to `sorted`, `map`, and `filter`. A `lambda` is a function
expression with no name of its own.

```python file=n06.py
words = ["pear", "fig", "banana", "kiwi"]
print(sorted(words, key=len))
print(list(map(str.upper, words[:2])))
print(list(filter(lambda w: len(w) == 4, words)))
```

```text output
['fig', 'pear', 'kiwi', 'banana']
['PEAR', 'FIG']
['pear', 'kiwi']
```

## A decorator wraps a function

The wrapper runs around the original call. `functools.wraps` copies the
original name onto the wrapper so traces still say `add`.

```python file=n07.py
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
print(add.__name__)
```

```text output
calling add(2, 3)
5
add
```

## A mutable default is created once

Every call that omits `bucket` shares that one list, so the values
accumulate. Use `None` as a sentinel and create the list inside the body.

```python file=n08.py
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
```

```text output
[1, 2] [1, 2]
[1] [2]
```

## Lambdas in a loop share one variable

Each lambda reads `i` when it is called, after the loop has finished.
Bind the current value with a default argument: `lambda i=i: i`.

```python file=n09.py
fns = [lambda: i for i in range(3)]
print([f() for f in fns])
fns = [lambda i=i: i for i in range(3)]
print([f() for f in fns])
```

```text output
[2, 2, 2]
[0, 1, 2]
```

## `yield` pauses a function

A generator produces values lazily. `islice` pulls a finite prefix from a
generator that would otherwise run forever.

```python file=n10.py
from itertools import islice


def fib():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b


print(list(islice(fib(), 8)))
```

```text output
[0, 1, 1, 2, 3, 5, 8, 13]
```

## The parameter is another name for the object

Arguments are passed by object reference. Appending changes the caller's
list. Assigning to the parameter rebinds only the local name.

```python file=n11.py
def mutate(xs):
    xs.append("m")


def rebind(xs):
    xs = ["new"]
    return xs


data = []
mutate(data)
print(rebind(data), data)
```

```text output
['new'] ['m']
```

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
