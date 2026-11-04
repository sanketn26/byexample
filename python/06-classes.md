# Python 06 — Classes and Data Modelling

Use `dataclass` for plain data, a regular class when there is behaviour and
invariants to protect, and dunder methods to plug into the language.

## A class holds data and behaviour

`interest_rate` is a class attribute, shared by every instance. `owner`
and `_balance` are instance attributes. A leading underscore is private
only by convention. `@property` reads like an attribute, `@classmethod`
receives the class, and `@staticmethod` receives neither.

```python file=n01.py
class Account:
    interest_rate = 0.02

    def __init__(self, owner, balance=0):
        self.owner = owner
        self._balance = balance

    @property
    def balance(self):
        return self._balance

    def deposit(self, amount):
        if amount <= 0:
            raise ValueError("amount must be positive")
        self._balance += amount
        return self

    @classmethod
    def empty(cls, owner):
        return cls(owner)

    @staticmethod
    def is_valid_amount(x):
        return x > 0

    def __repr__(self):
        return f"Account({self.owner!r}, {self._balance})"


acct = Account.empty("ada").deposit(50).deposit(25)
print(acct, acct.balance, Account.is_valid_amount(-1))
print(Account.interest_rate)
try:
    acct.deposit(0)
except ValueError as e:
    print(e)
```

```text output
Account('ada', 75) 75 False
0.02
amount must be positive
```

## `__new__` creates the object, `__init__` fills it in

`__init__` is not a constructor. `__new__` allocates the instance, then
`__init__` initialises it. Most classes only write `__init__`.

```python file=n02.py
class Box:
    def __new__(cls, value):
        obj = super().__new__(cls)
        print("new")
        return obj

    def __init__(self, value):
        print("init")
        self.value = value


print(Box(1).value)
```

```text output
new
init
1
```

## Double underscores are rewritten

`self.__x` is stored as `_Account__x` (the class name is inserted). That
avoids a clash with a subclass attribute of the same spelling. It is not
access control.

```python file=n03.py
class Account:
    def __init__(self):
        self.__x = 1


acct = Account()
print(hasattr(acct, "__x"), acct._Account__x)
```

```text output
False 1
```

## A dataclass writes `__init__`, `__repr__`, and `__eq__`

`order=True` adds the comparison methods. `frozen=True` blocks assignment
and, together with `eq=True`, makes the instances hashable. A mutable
default needs `field(default_factory=...)`. Never write `= []`.

```python file=n04.py
from dataclasses import dataclass, field


@dataclass(order=True, frozen=True)
class Version:
    major: int
    minor: int = 0
    tags: tuple = ()


print(Version(1, 2), Version(1, 2) == Version(1, 2), Version(1, 0) < Version(1, 5))
print(hash(Version(1, 2)) == hash(Version(1, 2)))
try:
    Version(1).major = 9
except AttributeError as e:
    print(type(e).__name__)


@dataclass
class Team:
    name: str
    members: list = field(default_factory=list)


t = Team("core")
t.members.append("ann")
print(t, Team("x").members)
```

```text output
Version(major=1, minor=2, tags=()) True True
True
FrozenInstanceError
Team(name='core', members=['ann']) []
```

## Dunder methods plug into operators

`__add__` and `__mul__` implement `+` and `*`. `__iter__` makes unpacking
work. `__bool__` is the truth value. `__slots__` drops the per-instance
`__dict__`. `__eq__` plus `__hash__` lets the value live in a set.

```python file=n05.py
class Vec:
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x, self.y = x, y

    def __add__(self, other):
        return Vec(self.x + other.x, self.y + other.y)

    def __mul__(self, k):
        return Vec(self.x * k, self.y * k)

    def __eq__(self, other):
        return isinstance(other, Vec) and (self.x, self.y) == (other.x, other.y)

    def __hash__(self):
        return hash((self.x, self.y))

    def __iter__(self):
        yield self.x
        yield self.y

    def __bool__(self):
        return bool(self.x or self.y)

    def __repr__(self):
        return f"Vec({self.x}, {self.y})"


v = Vec(1, 2) + Vec(3, 4) * 2
x, y = v
print(v, x, y, bool(Vec(0, 0)), len({Vec(1, 1), Vec(1, 1)}))
print(hasattr(v, "__dict__"))
```

```text output
Vec(7, 10) 7 10 False 1
False
```

## `__eq__` without `__hash__` is unhashable

Defining `__eq__` and not `__hash__` makes instances unhashable. Python
sets `__hash__` to `None` so a mutable equality cannot corrupt a set.

```python file=n06.py
class NoHash:
    def __eq__(self, other):
        return isinstance(other, NoHash)


try:
    hash(NoHash())
except TypeError as e:
    print(e)
```

```text output
unhashable type: 'NoHash'
```

## `super` follows the method resolution order

`Dog.__mro__` is the order `super` searches. `isinstance` walks that same
chain. In a multiple-inheritance tree, call `super().__init__()` so each
parent runs once instead of you naming them by hand.

```python file=n07.py
class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        return f"{self.name} makes a sound"


class Dog(Animal):
    def speak(self):
        return super().speak() + " (woof)"


print(Dog("Rex").speak(), isinstance(Dog("a"), Animal), Dog.__mro__[1].__name__)
print([cls.__name__ for cls in Dog.__mro__])
```

```text output
Rex makes a sound (woof) True Animal
['Dog', 'Animal', 'object']
```

## A mutable class attribute is shared

Appending to `C.items` changes every instance that has not shadowed the
name. Assigning `a.items = ...` creates an instance attribute and hides
the class one.

```python file=n08.py
class C:
    items = []


a, b = C(), C()
a.items.append(1)
print(b.items)
a.items = ["mine"]
print(a.items, b.items)
```

```text output
[1]
['mine'] [1]
```

## Exercises

```python file=exercise.py
class Stack:
    """LIFO stack. Provide push, pop (raise IndexError when empty), peek,
    __len__, __bool__ (True when non-empty) and __repr__ like Stack([1, 2])."""

    def __init__(self):
        raise NotImplementedError


class Money:
    """Immutable amount in integer cents, with currency code.
    Support +, - (same currency only, else ValueError), == , hash,
    and str() like '12.34 USD'. Money.of('12.34', 'USD') parses a decimal."""

    def __init__(self, cents, currency):
        raise NotImplementedError

    @classmethod
    def of(cls, text, currency):
        raise NotImplementedError


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


def raises(label, fn, exc):
    try:
        fn()
    except exc:
        print("PASS " + label)
        return True
    except Exception as e:
        print(f"FAIL {label}: raised {e!r}")
        return False
    print(f"FAIL {label}: nothing raised")
    return False


def run():
    s = Stack()
    out = [check("empty falsy", bool(s), False)]
    s.push(1); s.push(2)
    out += [
        check("len", len(s), 2),
        check("peek", s.peek(), 2),
        check("pop", s.pop(), 2),
        check("repr", repr(s), "Stack([1])"),
        raises("pop empty", lambda: (s.pop(), s.pop()), IndexError),
    ]
    a, b = Money.of("12.34", "USD"), Money(66, "USD")
    out += [
        check("add", str(a + b), "13.00 USD"),
        check("sub", str(a - Money(34, "USD")), "12.00 USD"),
        check("eq", Money(100, "USD") == Money.of("1", "USD"), True),
        check("hash", len({Money(5, "EUR"), Money(5, "EUR")}), 1),
        raises("currency mismatch", lambda: a + Money(1, "EUR"), ValueError),
    ]
    return out


raise SystemExit(0 if all(run()) else 1)
```

<details><summary>Solution</summary>

```python file=solution.py
class Stack:
    def __init__(self):
        self._items = []

    def push(self, x):
        self._items.append(x)

    def pop(self):
        if not self._items:
            raise IndexError("pop from empty stack")
        return self._items.pop()

    def peek(self):
        if not self._items:
            raise IndexError("peek at empty stack")
        return self._items[-1]

    def __len__(self):
        return len(self._items)

    def __bool__(self):
        return bool(self._items)

    def __repr__(self):
        return f"Stack({self._items!r})"


class Money:
    __slots__ = ("cents", "currency")

    def __init__(self, cents, currency):
        object.__setattr__(self, "cents", cents)
        object.__setattr__(self, "currency", currency)

    def __setattr__(self, name, value):
        raise AttributeError("Money is immutable")

    @classmethod
    def of(cls, text, currency):
        whole, _, frac = text.partition(".")
        frac = (frac + "00")[:2]
        return cls(int(whole) * 100 + int(frac), currency)

    def _check(self, other):
        if self.currency != other.currency:
            raise ValueError("currency mismatch")

    def __add__(self, other):
        self._check(other)
        return Money(self.cents + other.cents, self.currency)

    def __sub__(self, other):
        self._check(other)
        return Money(self.cents - other.cents, self.currency)

    def __eq__(self, other):
        return (isinstance(other, Money)
                and (self.cents, self.currency) == (other.cents, other.currency))

    def __hash__(self):
        return hash((self.cents, self.currency))

    def __str__(self):
        return f"{self.cents // 100}.{self.cents % 100:02d} {self.currency}"


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


def raises(label, fn, exc):
    try:
        fn()
    except exc:
        print("PASS " + label)
        return True
    except Exception as e:
        print(f"FAIL {label}: raised {e!r}")
        return False
    print(f"FAIL {label}: nothing raised")
    return False


def run():
    s = Stack()
    out = [check("empty falsy", bool(s), False)]
    s.push(1); s.push(2)
    out += [
        check("len", len(s), 2),
        check("peek", s.peek(), 2),
        check("pop", s.pop(), 2),
        check("repr", repr(s), "Stack([1])"),
        raises("pop empty", lambda: (s.pop(), s.pop()), IndexError),
    ]
    a, b = Money.of("12.34", "USD"), Money(66, "USD")
    out += [
        check("add", str(a + b), "13.00 USD"),
        check("sub", str(a - Money(34, "USD")), "12.00 USD"),
        check("eq", Money(100, "USD") == Money.of("1", "USD"), True),
        check("hash", len({Money(5, "EUR"), Money(5, "EUR")}), 1),
        raises("currency mismatch", lambda: a + Money(1, "EUR"), ValueError),
    ]
    return out


raise SystemExit(0 if all(run()) else 1)
```

</details>

Next: [07 — Errors](07-errors.md)
