# Python 09 — Protocols and Abstraction

Python favours *duck typing*: if it has the right methods, it works. Modern
Python adds static structure (`Protocol`, `ABC`) without forcing it at
runtime.

## Example

```python file=example.py
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable
import math


# 1. Duck typing: no declaration needed
class Duck:
    def speak(self):
        return "quack"

class Robot:
    def speak(self):
        return "beep"

for thing in (Duck(), Robot()):
    print(thing.speak())


# 2. ABC: enforce an interface at instantiation time
class Shape(ABC):
    @abstractmethod
    def area(self) -> float: ...

    def describe(self):                      # shared behaviour
        return f"{type(self).__name__} with area {self.area():.2f}"

class Circle(Shape):
    def __init__(self, r):
        self.r = r
    def area(self):
        return math.pi * self.r ** 2

class Square(Shape):
    def __init__(self, s):
        self.s = s
    def area(self):
        return self.s ** 2

print(Circle(1).describe(), "|", Square(2).describe())
try:
    Shape()
except TypeError as e:
    print("TypeError:", e)


# 3. Protocol: structural typing, checked by type checkers (mypy/pyright)
@runtime_checkable
class Closeable(Protocol):
    def close(self) -> None: ...

class File:
    def close(self):
        print("file closed")

def shutdown(items):
    for it in items:
        if isinstance(it, Closeable):        # runtime_checkable checks names only
            it.close()

shutdown([File(), 42])


# 4. Built-in protocols: implement dunders, get language features
class Countdown:
    def __init__(self, start):
        self.start = start
    def __iter__(self):
        n = self.start
        while n > 0:
            yield n
            n -= 1
    def __len__(self):
        return self.start
    def __contains__(self, x):
        return 0 < x <= self.start
    def __getitem__(self, i):
        return self.start - i

cd = Countdown(3)
print(list(cd), len(cd), 2 in cd, cd[0], sum(cd), max(cd))


# 5. Composition and delegation over deep inheritance
class Engine:
    def start(self):
        return "vroom"

class Car:
    def __init__(self, engine):
        self.engine = engine           # injected collaborator
    def drive(self):
        return self.engine.start() + "!"

class SilentEngine:
    def start(self):
        return "..."

print(Car(Engine()).drive(), Car(SilentEngine()).drive())


# 6. Callables as interfaces: functions are the lightest-weight strategy
def apply_all(value, *transforms):
    for t in transforms:
        value = t(value)
    return value

print(apply_all(3, lambda x: x + 1, str, lambda s: s * 2))


# 7. functools.singledispatch: polymorphism by argument type
from functools import singledispatch

@singledispatch
def show(x):
    return f"object {x!r}"

@show.register
def _(x: int):
    return f"int {x}"

@show.register
def _(x: list):
    return "list of " + ", ".join(show(i) for i in x)

print(show(1), "|", show("s"), "|", show([1, "a"]))
```

```text output
quack
beep
Circle with area 3.14 | Square with area 4.00
TypeError: Can't instantiate abstract class Shape without an implementation for abstract method 'area'
file closed
[3, 2, 1] 3 True 3 6 3
vroom! ...!
44
int 1 | object 's' | list of int 1, object 'a'
```

## Details that bite

- `isinstance(x, Protocol)` with `runtime_checkable` only checks that
  attribute *names* exist, not signatures.
- Type hints are not enforced at runtime. Run `mypy` or `pyright` to check
  them.
- Multiple inheritance follows the MRO (`Class.__mro__`); always call
  `super().__init__()` cooperatively.
- Prefer composition: inheritance couples a subclass to every detail of its
  parent.
- `__getitem__` alone makes an object iterable (legacy protocol); define
  `__iter__` explicitly.

## Exercises

```python file=exercise.py
from abc import ABC, abstractmethod


class Discount(ABC):
    """Abstract: apply(price) -> new price. Subclasses below."""

    @abstractmethod
    def apply(self, price):
        ...


class Percent(Discount):
    """Percent(10).apply(200) == 180.0"""


class Flat(Discount):
    """Flat(5).apply(3) == 0 (never negative)."""


class Chain(Discount):
    """Chain(d1, d2, ...) applies discounts in order."""


class Registry:
    """Maps names to handler callables.
    register(name) is a decorator; dispatch(name, *args) calls the handler;
    unknown names raise KeyError."""


class Range:
    """Iterable numeric range supporting len(), `in`, reversed(), and
    indexing: Range(2, 5) -> 2,3,4 ; Range(2,5)[1] == 3 ; IndexError beyond."""


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


def run():
    out = []
    out.append(check("percent", Percent(10).apply(200), 180.0))
    out.append(check("flat floor", Flat(5).apply(3), 0))
    out.append(check("chain", Chain(Percent(50), Flat(10)).apply(100), 40.0))
    try:
        Discount()
        out.append(check("abstract", "instantiated", "TypeError"))
    except TypeError:
        out.append(check("abstract", "TypeError", "TypeError"))
    reg = Registry()

    @reg.register("add")
    def add(a, b):
        return a + b

    out.append(check("dispatch", reg.dispatch("add", 2, 3), 5))
    try:
        reg.dispatch("nope")
        out.append(check("unknown", "no error", "KeyError"))
    except KeyError:
        out.append(check("unknown", "KeyError", "KeyError"))
    r = Range(2, 5)
    out.append(check("range", (list(r), len(r), 4 in r, 5 in r, r[1], list(reversed(r))),
                     ([2, 3, 4], 3, True, False, 3, [4, 3, 2])))
    try:
        r[3]
        out.append(check("index", "no error", "IndexError"))
    except IndexError:
        out.append(check("index", "IndexError", "IndexError"))
    return out


raise SystemExit(0 if all(run()) else 1)
```

<details><summary>Solution</summary>

```python file=solution.py
from abc import ABC, abstractmethod


class Discount(ABC):
    @abstractmethod
    def apply(self, price):
        ...


class Percent(Discount):
    def __init__(self, pct):
        self.pct = pct

    def apply(self, price):
        return price * (100 - self.pct) / 100


class Flat(Discount):
    def __init__(self, amount):
        self.amount = amount

    def apply(self, price):
        return max(0, price - self.amount)


class Chain(Discount):
    def __init__(self, *discounts):
        self.discounts = discounts

    def apply(self, price):
        for d in self.discounts:
            price = d.apply(price)
        return price


class Registry:
    def __init__(self):
        self._handlers = {}

    def register(self, name):
        def deco(fn):
            self._handlers[name] = fn
            return fn
        return deco

    def dispatch(self, name, *args):
        return self._handlers[name](*args)


class Range:
    def __init__(self, start, stop):
        self.start, self.stop = start, stop

    def __len__(self):
        return max(0, self.stop - self.start)

    def __iter__(self):
        return iter(range(self.start, self.stop))

    def __contains__(self, x):
        return self.start <= x < self.stop

    def __getitem__(self, i):
        if not 0 <= i < len(self):
            raise IndexError(i)
        return self.start + i

    def __reversed__(self):
        return iter(range(self.stop - 1, self.start - 1, -1))


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


def run():
    out = []
    out.append(check("percent", Percent(10).apply(200), 180.0))
    out.append(check("flat floor", Flat(5).apply(3), 0))
    out.append(check("chain", Chain(Percent(50), Flat(10)).apply(100), 40.0))
    try:
        Discount()
        out.append(check("abstract", "instantiated", "TypeError"))
    except TypeError:
        out.append(check("abstract", "TypeError", "TypeError"))
    reg = Registry()

    @reg.register("add")
    def add(a, b):
        return a + b

    out.append(check("dispatch", reg.dispatch("add", 2, 3), 5))
    try:
        reg.dispatch("nope")
        out.append(check("unknown", "no error", "KeyError"))
    except KeyError:
        out.append(check("unknown", "KeyError", "KeyError"))
    r = Range(2, 5)
    out.append(check("range", (list(r), len(r), 4 in r, 5 in r, r[1], list(reversed(r))),
                     ([2, 3, 4], 3, True, False, 3, [4, 3, 2])))
    try:
        r[3]
        out.append(check("index", "no error", "IndexError"))
    except IndexError:
        out.append(check("index", "IndexError", "IndexError"))
    return out


raise SystemExit(0 if all(run()) else 1)
```

</details>

Next: [10 — Files and I/O](10-files-io.md)
