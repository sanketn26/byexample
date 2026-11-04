# Python 11 — The Pythonic Way

Pythonic code uses the language's own idioms instead of translating habits
from C or Java. It is shorter, clearer, and usually faster. From
`import this`: readability counts, flat is better than nested, explicit is
better than implicit, and there should be one obvious way to do it.
Pythonic is not "as short as possible".

## Iterate the items

`for x in xs` is the loop. `enumerate` adds the index when you need it.
`enumerate(xs, 1)` starts at one, so you do not keep a counter by hand.

```python file=n01.py
items = ["a", "b", "c"]
bad = []
for i in range(len(items)):
    bad.append(f"{i}:{items[i]}")
good = [f"{i}:{x}" for i, x in enumerate(items)]
print(bad == good, good)
print([f"{i}:{x}" for i, x in enumerate(items, 1)])
```

```text output
True ['0:a', '1:b', '2:c']
['1:a', '2:b', '3:c']
```

## `zip` walks sequences in parallel

It stops at the shorter one. `dict(zip(keys, vals))` builds the mapping.

```python file=n02.py
keys, vals = ["x", "y"], [1, 2]
print(dict(zip(keys, vals)))
```

```text output
{'x': 1, 'y': 2}
```

## A star grabs the middle

`first` and `last` take the ends. `*middle` collects whatever is left.

```python file=n03.py
first, *middle, last = range(5)
print(first, middle, last)
```

```text output
0 [1, 2, 3] 4
```

## Empty is falsy

`if not xs` is the emptiness test. `if len(xs) == 0` says the same thing
the long way. `if flag` is the test; `if flag == True` is not clearer.

```python file=n04.py
empty = []
flag = True
print("empty" if not empty else "has items")
print("yes" if flag else "no")
```

```text output
empty
yes
```

## `is None` is the null test

`==` calls `__eq__`, which a class can define to lie. `x is None` asks
whether the name points at the `None` object.

```python file=n05.py
class Weird:
    def __eq__(self, other):
        return True


print(Weird() == None, Weird() is None)
```

```text output
True False
```

## `any` and `all` stop early

They consume a generator expression, so they do not build a list of every
comparison first.

```python file=n06.py
nums = [1, 2, 3]
print(any(n > 2 for n in nums), all(n > 0 for n in nums))
```

```text output
True True
```

## Try the operation, or use `.get`

EAFP catches the failure. `dict.get` supplies a default without an
exception when the key is simply missing.

```python file=n07.py
config = {"port": "8080"}
try:
    port = int(config["port"])
except (KeyError, ValueError):
    port = 80
print(port, config.get("host", "localhost"))
```

```text output
8080 localhost
```

## `join` builds one string

`s += part` in a loop copies the growing string. `join` does the work
once.

```python file=n08.py
nums = [1, 2, 3]
print(", ".join(str(n) for n in nums))
```

```text output
1, 2, 3
```

## `defaultdict` and `Counter` keep the bookkeeping

The manual `if key not in d: d[key] = []` disappears. `Counter` tallies
in one pass.

```python file=n09.py
from collections import Counter, defaultdict

words = ["apple", "bob", "cat", "avocado", "bee"]
by_letter = defaultdict(list)
for w in words:
    by_letter[w[0]].append(w)
print(dict(by_letter), Counter(len(w) for w in words)[3])
```

```text output
{'a': ['apple', 'avocado'], 'b': ['bob', 'bee'], 'c': ['cat']} 3
```

## A comprehension replaces the append loop

A generator expression is lazy and single-use: the second `list` of it is
empty. Wrap it in `list` if you need to walk it twice. A triple-nested
comprehension is harder to read than a loop. Split that one up.

```python file=n10.py
nested = [[1, 2], [3], [4, 5]]
print([y for x in nested for y in x], sum(x * x for x in range(10)))
gen = (n * n for n in range(3))
print(list(gen), list(gen))
```

```text output
[1, 2, 3, 4, 5] 285
[0, 1, 4] []
```

## `:=` assigns inside the expression

The walrus operator binds a name and yields the value, so the `if` can
test the length it just computed.

```python file=n11.py
words = ["apple", "bob", "cat", "avocado", "bee"]
if (n := len(words)) > 3:
    print(f"{n} words")
```

```text output
5 words
```

## Pass `key=`, not a comparison function

The key function is called once per item. `itemgetter` builds one.
`max` takes `default` so an empty iterable does not raise.

```python file=n12.py
from operator import itemgetter

people = [
    {"name": "Al", "age": 30},
    {"name": "Bo", "age": 25},
    {"name": "Cy", "age": 30},
]
ordered = sorted(people, key=lambda p: (-p["age"], p["name"]))
print([p["name"] for p in ordered], max(people, key=itemgetter("age"))["name"])
print(max([], default=None))
```

```text output
['Al', 'Cy', 'Bo'] Al
None
```

## Name the fields of a small record

A `namedtuple` or a frozen dataclass is a tuple or a value object with
names. A bare tuple forces every reader to remember which index is which.

```python file=n13.py
from collections import namedtuple
from dataclasses import dataclass

Point = namedtuple("Point", "x y")


@dataclass(frozen=True)
class Pt:
    x: int
    y: int = 0


print(Point(1, 2), Pt(1))
```

```text output
Point(x=1, y=2) Pt(x=1, y=0)
```

## `cache` remembers a pure function

`functools.cache` stores results by the arguments. Use it only when the
same arguments always mean the same result.

```python file=n14.py
import functools


@functools.cache
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)


print(fib(50))
```

```text output
12586269025
```

## `itertools` holds the small iteration tools

`pairwise` yields neighbors. `batched` yields fixed-size groups, and the
last group can be short.

```python file=n15.py
import itertools

print(list(itertools.pairwise([1, 2, 4, 7])))
print(list(itertools.batched("abcdefg", 3)))
```

```text output
[(1, 2), (2, 4), (4, 7)]
[('a', 'b', 'c'), ('d', 'e', 'f'), ('g',)]
```

## `|` merges dicts

The right-hand mapping wins when a key is in both. `{**a, **b}` does the
same unpacking and can add a key at the same time.

```python file=n16.py
a, b = {"x": 1, "y": 2}, {"y": 3}
print(a | b, {**a, **b, "z": 4})
```

```text output
{'x': 1, 'y': 3} {'x': 1, 'y': 3, 'z': 4}
```

## `in` tests membership

Use it for a tuple of choices, for a substring, and for a dict key.
`d.has_key` is gone, and `if k in d.keys()` builds a view you do not need.

```python file=n17.py
ext = ".py"
d = {"py": True}
print(ext in (".py", ".pyi"), "ell" in "hello", "py" in d)
```

```text output
True True True
```

## Guard script code with `__name__`

`__name__` is `"__main__"` only when the file is the program. Code that
should not run on import goes under that test.

```python file=n18.py
print(__name__)
if __name__ == "__main__":
    print("ran as a program")
```

```text output
__main__
ran as a program
```

## A slice can reverse

`reversed` returns an iterator. `[::-1]` returns a new string. Neither
needs an index loop.

```python file=n19.py
print(list(reversed("abc")), "abc"[::-1])
```

```text output
['c', 'b', 'a'] cba
```

## Hints document the contract

Annotations are not checked when the function runs. `mypy` or `pyright`
reads them. `int | None` is the optional form.

```python file=n20.py
def first_or(xs: list[int], default: int | None = None) -> int | None:
    return xs[0] if xs else default


print(first_or([]), first_or([5]))
```

```text output
None 5
```

## `with` closes the file

An `open` followed by a later `close` skips the close when the body
raises. `with` runs it anyway.

```python file=n21.py
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as d:
    path = Path(d) / "note.txt"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("hi\n")
    print(path.read_text(encoding="utf-8").rstrip())
```

```text output
hi
```

## Join paths with `Path`

`Path(a) / b` inserts the separator. Concatenating with `"/"` breaks on
a root that already has one, and on Windows.

```python file=n22.py
from pathlib import Path

print(Path("dir") / "sub" / "file.txt")
```

```text output
dir/sub/file.txt
```

## An f-string replaces `%` and `str.format`

The expression sits inside the braces. The older forms still run, and
they are the ones to stop writing.

```python file=n23.py
name = "Ada"
print(f"{name}={3}", "%s=%d" % (name, 3), "{}={}".format(name, 3))
```

```text output
Ada=3 Ada=3 Ada=3
```

## `isinstance` follows subclasses

`type(x) == list` misses a subclass. Use `isinstance` at the boundary
where you have to reject a type. Duck typing stays the default everywhere
else.

```python file=n24.py
class MyList(list):
    pass


xs = MyList([1])
print(type(xs) == list, isinstance(xs, list))
```

```text output
False True
```

## Start with a plain attribute

Read and write the attribute. Add `@property` only when getting or
setting has a rule to enforce. A getter and setter pair with no rule is
noise.

```python file=n25.py
class Account:
    def __init__(self, balance):
        self._balance = balance

    @property
    def balance(self):
        return self._balance


acct = Account(5)
print(acct.balance)
```

```text output
5
```

## A function beats a static-only class

If the class holds no data, the methods are module-level functions. The
class adds an indentation level and nothing else.

```python file=n26.py
def double(n):
    return n * 2


print(double(21))
```

```text output
42
```

## Name the exception you catch

`except ValueError` leaves `KeyboardInterrupt` and `SystemExit` alone.
A bare `except:` catches those too.

```python file=n27.py
try:
    int("x")
except ValueError as e:
    print(type(e).__name__)
```

```text output
ValueError
```

## Use `None` as the mutable default

The list in the signature is created once and shared. A `None` sentinel
means "make a new list for this call".

```python file=n28.py
def append_bad(x, bucket=[]):
    bucket.append(x)
    return bucket


def append_good(x, bucket=None):
    if bucket is None:
        bucket = []
    bucket.append(x)
    return bucket


print(append_bad(1), append_bad(2))
print(append_good(1), append_good(2))
```

```text output
[1, 2] [1, 2]
[1] [2]
```

## Give it a `def` if you name it

A lambda stored in a variable has `__name__` `'<lambda>'`. A `def` has
the name you will see in a traceback.

```python file=n29.py
def double(n):
    return n * 2


scale = lambda n: n * 2
print(double.__name__, scale.__name__)
```

```text output
double <lambda>
```

## Import the module, not `*`

`from math import *` dumps names into your namespace, so a reader cannot
see where `sqrt` came from. Import the module. A bare global has the same
problem: it looks local and is not.

```python file=n30.py
import math

print(math.sqrt(4))
```

```text output
2.0
```

## Names follow PEP 8

`snake_case` for functions and variables, `CapWords` for classes,
`UPPER_CASE` for constants. `black` or `ruff format` applies the spacing
around them.

```python file=n31.py
MAX_ITEMS = 3


class ItemCount:
    def current(self):
        return MAX_ITEMS


print(ItemCount().current())
```

```text output
3
```

## Chunk a sequence

People look this up constantly. Step by `n` and slice. The last chunk is
shorter when the length does not divide evenly.

```python file=n32.py
rows = [1, 2, 3, 4, 5]
n = 2
print([rows[i:i + n] for i in range(0, len(rows), n)])
```

```text output
[[1, 2], [3, 4], [5]]
```

## Sort names by a score

`sorted` with `key=` does not need a comparison function. Equal scores
keep their original order.

```python file=n33.py
scores = {"bob": 2, "ada": 3, "cam": 2}
print(sorted(scores, key=scores.get))
```

```text output
['bob', 'cam', 'ada']
```

## Invert a dict

Swap keys and values in one comprehension. The values have to be
hashable, and a repeated value keeps only the last key.

```python file=n34.py
print({v: k for k, v in {"a": 1, "b": 2}.items()})
```

```text output
{1: 'a', 2: 'b'}
```

## An environment variable has a default

`os.environ.get` returns the default when the name is unset. It does
not invent the variable.

```python file=n35.py
import os

os.environ["APP_PORT"] = "8080"
print(os.environ.get("APP_PORT", "80"), os.environ.get("APP_MISSING", "80"))
```

```text output
8080 80
```

## Parse an ISO timestamp

`fromisoformat` reads `2024-03-15T13:45:00`. Take `.date()` when the
clock time is not part of the question.

```python file=n36.py
from datetime import datetime

print(datetime.fromisoformat("2024-03-15T13:45:00").date())
```

```text output
2024-03-15
```

## Exercises

Write each function in idiomatic style: no `range(len(...))`, no index
bookkeeping, no manual `+=` string building.

```python file=exercise.py
def flatten(nested):
    """Flatten one level: [[1, 2], [3]] -> [1, 2, 3]."""
    raise NotImplementedError


def invert_unique(d):
    """Swap keys and values. Raise ValueError if values are not unique."""
    raise NotImplementedError


def moving_average(xs, k):
    """Averages of every window of k consecutive items, as floats.
    Fewer than k items -> []."""
    raise NotImplementedError


def group_anagrams(words):
    """Groups of words that are anagrams. Each group sorted; groups sorted
    by their first word."""
    raise NotImplementedError


def run_length_encode(s):
    """'aaabcc' -> [('a', 3), ('b', 1), ('c', 2)]."""
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


results = [
    check("flatten", flatten([[1, 2], [3], []]), [1, 2, 3]),
    check("invert", invert_unique({"a": 1, "b": 2}), {1: "a", 2: "b"}),
    raises("invert dup", lambda: invert_unique({"a": 1, "b": 1}), ValueError),
    check("moving_average", moving_average([1, 2, 3, 4, 5], 3), [2.0, 3.0, 4.0]),
    check("moving_average short", moving_average([1], 3), []),
    check("anagrams", group_anagrams(["eat", "tea", "tan", "ate", "nat", "bat"]),
          [["ate", "eat", "tea"], ["bat"], ["nat", "tan"]]),
    check("rle", run_length_encode("aaabcc"), [("a", 3), ("b", 1), ("c", 2)]),
    check("rle empty", run_length_encode(""), []),
]
raise SystemExit(0 if all(results) else 1)
```

<details><summary>Solution</summary>

```python file=solution.py
from collections import defaultdict
from itertools import chain, groupby


def flatten(nested):
    return list(chain.from_iterable(nested))


def invert_unique(d):
    inverted = {v: k for k, v in d.items()}
    if len(inverted) != len(d):
        raise ValueError("values are not unique")
    return inverted


def moving_average(xs, k):
    return [sum(xs[i:i + k]) / k for i in range(len(xs) - k + 1)]


def group_anagrams(words):
    groups = defaultdict(list)
    for w in words:
        groups["".join(sorted(w))].append(w)
    return sorted(sorted(g) for g in groups.values())


def run_length_encode(s):
    return [(ch, sum(1 for _ in grp)) for ch, grp in groupby(s)]


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


results = [
    check("flatten", flatten([[1, 2], [3], []]), [1, 2, 3]),
    check("invert", invert_unique({"a": 1, "b": 2}), {1: "a", 2: "b"}),
    raises("invert dup", lambda: invert_unique({"a": 1, "b": 1}), ValueError),
    check("moving_average", moving_average([1, 2, 3, 4, 5], 3), [2.0, 3.0, 4.0]),
    check("moving_average short", moving_average([1], 3), []),
    check("anagrams", group_anagrams(["eat", "tea", "tan", "ate", "nat", "bat"]),
          [["ate", "eat", "tea"], ["bat"], ["nat", "tan"]]),
    check("rle", run_length_encode("aaabcc"), [("a", 3), ("b", 1), ("c", 2)]),
    check("rle empty", run_length_encode(""), []),
]
raise SystemExit(0 if all(results) else 1)
```

</details>

Next: [12 — asyncio](12-asyncio.md)
