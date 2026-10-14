# Python 11 — The Pythonic Way

"Pythonic" code uses the language's own idioms instead of translating habits
from C or Java. It is shorter, clearer, and usually faster. Each numbered
block below shows the clumsy way, the idiomatic way, and proves they agree.

Guiding principles from `import this`: *Readability counts. Flat is better
than nested. Explicit is better than implicit. There should be one obvious
way to do it.*

## Example

```python file=example.py
import functools
import itertools
from collections import Counter, defaultdict, namedtuple
from dataclasses import dataclass
from operator import itemgetter

# 1. Iterate directly; use enumerate when you need the index
items = ["a", "b", "c"]
bad = []
for i in range(len(items)):
    bad.append(f"{i}:{items[i]}")
good = [f"{i}:{x}" for i, x in enumerate(items)]
print(1, bad == good, good)

# 2. zip walks sequences in parallel
keys, vals = ["x", "y"], [1, 2]
print(2, dict(zip(keys, vals)))

# 3. Extended unpacking
first, *middle, last = range(5)
print(3, first, middle, last)

# 4. Truthiness, not len() == 0
empty = []
print(4, "empty" if not empty else "has items")

# 5. any / all with generator expressions
nums = [1, 2, 3]
print(5, any(n > 2 for n in nums), all(n > 0 for n in nums))

# 6. EAFP: try it, handle the failure; .get for defaults
config = {"port": "8080"}
try:
    port = int(config["port"])
except (KeyError, ValueError):
    port = 80
print(6, port, config.get("host", "localhost"))

# 7. join, never += in a loop
print(7, ", ".join(str(n) for n in nums))

# 8. defaultdict and Counter replace manual dict bookkeeping
words = ["apple", "bob", "cat", "avocado", "bee"]
by_letter = defaultdict(list)
for w in words:
    by_letter[w[0]].append(w)
print(8, dict(by_letter), Counter(len(w) for w in words)[3])

# 9. Comprehensions and generator expressions
nested = [[1, 2], [3], [4, 5]]
print(9, [y for x in nested for y in x], sum(x * x for x in range(10)))

# 10. Walrus operator: assign inside an expression
if (n := len(words)) > 3:
    print(10, f"{n} words")

# 11. key= functions instead of cmp functions or manual sorts
people = [{"name": "Al", "age": 30}, {"name": "Bo", "age": 25}, {"name": "Cy", "age": 30}]
ordered = sorted(people, key=lambda p: (-p["age"], p["name"]))
print(11, [p["name"] for p in ordered], max(people, key=itemgetter("age"))["name"],
      max([], default=None))

# 12. Small record types instead of bare tuples or dicts
Point = namedtuple("Point", "x y")

@dataclass(frozen=True)
class Pt:
    x: int
    y: int = 0

print(12, Point(1, 2), Pt(1))

# 13. functools.cache for pure recursive functions
@functools.cache
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)

print(13, fib(50))

# 14. itertools: the standard toolbox for iteration
print(14, list(itertools.pairwise([1, 2, 4, 7])), list(itertools.batched("abcdefg", 3)))

# 15. Merge dicts with |
a, b = {"x": 1, "y": 2}, {"y": 3}
print(15, a | b, {**a, **b, "z": 4})

# 16. in for membership; no chains of ==
ext = ".py"
print(16, ext in (".py", ".pyi"), "ell" in "hello")

# 17. The main guard: import-safe scripts
print(17, __name__)

# 18. Slicing and reversed
print(18, list(reversed("abc")), "abc"[::-1])

# 19. Type hints document intent (checked by mypy/pyright, not at runtime)
def first_or(xs: list[int], default: int | None = None) -> int | None:
    return xs[0] if xs else default

print(19, first_or([]), first_or([5]))
```

```text output
1 True ['0:a', '1:b', '2:c']
2 {'x': 1, 'y': 2}
3 0 [1, 2, 3] 4
4 empty
5 True True
6 8080 localhost
7 1, 2, 3
8 {'a': ['apple', 'avocado'], 'b': ['bob', 'bee'], 'c': ['cat']} 3
9 [1, 2, 3, 4, 5] 285
10 5 words
11 ['Al', 'Cy', 'Bo'] Al None
12 Point(x=1, y=2) Pt(x=1, y=0)
13 12586269025
14 [(1, 2), (2, 4), (4, 7)] [('a', 'b', 'c'), ('d', 'e', 'f'), ('g',)]
15 {'x': 1, 'y': 3} {'x': 1, 'y': 3, 'z': 4}
16 True True
17 __main__
18 ['c', 'b', 'a'] cba
19 None 5
```

## The checklist

| Instead of | Write |
|------------|-------|
| `for i in range(len(xs))` | `for x in xs` / `enumerate(xs)` |
| `if len(xs) == 0` | `if not xs` |
| `if x == None` | `if x is None` |
| `if flag == True` | `if flag` |
| `result = []; for …: result.append(…)` | a comprehension |
| `s = ""; s += part` | `"".join(parts)` |
| `open(f); …; close()` | `with open(f) as fh:` |
| `os.path.join(a, b)` | `Path(a) / b` |
| `"%s" % x`, `.format()` | f-strings |
| `type(x) == list` | `isinstance(x, list)` |
| `d.has_key(k)` / `if k in d.keys()` | `if k in d` |
| getters and setters | plain attributes, `@property` when needed |
| classes with only static methods | module-level functions |
| `except:` | `except SomeError:` |
| mutable default arguments | `None` sentinel |
| `lambda` stored in a variable | `def` |

## Details that bite

- Pythonic is not "as short as possible". A triple-nested comprehension is
  less readable than a loop; split it up.
- Generator expressions are lazy and single-use; wrap in `list()` if you
  need to iterate twice.
- `from module import *` and bare globals hide where names come from.
- Use `enumerate(xs, 1)`, not `i = 0 … i += 1` bookkeeping.
- Duck typing is the default; reach for `isinstance` at boundaries, not
  everywhere.
- Follow PEP 8 (`black`/`ruff format` do it for you): `snake_case` for
  functions and variables, `CapWords` for classes, `UPPER_CASE` for
  constants.

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
