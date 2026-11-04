# Python 04 — Collections

Four built-ins cover almost everything. A `list` is ordered and mutable.
A `tuple` is ordered and immutable. A `dict` keeps insertion order and
unique keys. A `set` stores unique items and does not promise an order.

## A list grows, shrinks, and sorts

`append` adds at the end and `insert` adds at an index. A negative index
counts from the end. `list.sort` changes the list and returns `None`.
`sorted` returns a new list. Both sorts are stable: equal keys stay in
their original order.

```python file=n01.py
nums = [5, 3, 8, 1]
nums.append(9)
nums.insert(0, 7)
print(nums, len(nums), nums[-1], nums[1:3], nums[::-1])
print(nums.sort())
print(nums, sorted(nums, reverse=True))
print(sorted(["bb", "a", "ccc", "b"], key=len))
print(nums.pop(), nums.index(5), 8 in nums)
```

```text output
[7, 5, 3, 8, 1, 9] 6 9 [5, 3] [9, 1, 8, 3, 5, 7]
None
[1, 3, 5, 7, 8, 9] [9, 8, 7, 5, 3, 1]
['a', 'b', 'bb', 'ccc']
9 2 True
```

## A second name is not a copy

`b = a` is another name for the same list. `a[:]` is a shallow copy, so
appending to `a` shows up in `b` only.

```python file=n02.py
a = [1, 2, 3]
b = a
c = a[:]
a.append(4)
print(b, c)
```

```text output
[1, 2, 3, 4] [1, 2, 3]
```

## A comma makes the tuple

`(1)` is an int. `(1,)` is a one-item tuple. Tuples are immutable records.
A tuple of hashable items can be a dict key.

```python file=n03.py
point = (3, 4)
x, y = point
print(x, y, point + (5,))
single = (1,)
print(type((1)), type(single))
print({point: "p"}[point])
```

```text output
3 4 (3, 4, 5)
<class 'int'> <class 'tuple'>
p
```

## A missing dict key is a `KeyError`

`d[key]` raises. `d.get(key)` returns `None`, or the default you pass.
`in` tests keys. Iteration follows insertion order, guaranteed since 3.7.
`pop` accepts a default so a missing key does not raise.

```python file=n04.py
ages = {"ann": 31, "bob": 25}
ages["cy"] = 40
print(ages.get("dan"), ages.get("dan", 0), "ann" in ages)
for name, age in sorted(ages.items()):
    print(name, age)
print(list(ages), list(ages.values()))
del ages["bob"]
print(ages.pop("zed", "missing"))
try:
    ages["zed"]
except KeyError as e:
    print(type(e).__name__)
```

```text output
None 0 True
ann 31
bob 25
cy 40
['ann', 'bob', 'cy'] [31, 25, 40]
missing
KeyError
```

## `Counter` and `defaultdict` fill themselves in

`Counter` tallies hashable items and `most_common` ranks them.
`defaultdict(list)` creates the list the first time a key is used, so the
loop does not check `if key not in groups`.

```python file=n05.py
from collections import Counter, defaultdict

print(Counter("mississippi").most_common(2))
groups = defaultdict(list)
for word in ["apple", "avocado", "banana", "blueberry", "cherry"]:
    groups[word[0]].append(word)
print(dict(groups))
```

```text output
[('i', 4), ('s', 4)]
{'a': ['apple', 'avocado'], 'b': ['banana', 'blueberry'], 'c': ['cherry']}
```

## Set operators combine two sets

`|` is union, `&` intersection, `-` difference, and `^` symmetric
difference. The printed order is not a contract. `in` on a list scans
every item; `in` on a set does not.

```python file=n06.py
s = {1, 2, 3}
t = {3, 4}
print(s | t, s & t, s - t, s ^ t)
print(3 in [1, 2, 3], 3 in s)
```

```text output
{1, 2, 3, 4} {3} {1, 2} {1, 2, 4}
True True
```

## `dict.fromkeys` drops later duplicates

A dict keeps the first insertion of each key. `list` around that dict is
the items in first-seen order.

```python file=n07.py
print(list(dict.fromkeys([3, 1, 3, 2, 1])))
```

```text output
[3, 1, 2]
```

## A comprehension builds the collection

Read nested comprehensions left to right: the first `for` is the outer
loop. `zip` pairs two sequences for a dict comprehension.

```python file=n08.py
matrix = [[1, 2, 3], [4, 5, 6]]
print([[row[i] for row in matrix] for i in range(3)])
print({k: v for k, v in zip("abc", range(3))})
```

```text output
[[1, 4], [2, 5], [3, 6]]
{'a': 0, 'b': 1, 'c': 2}
```

## `copy` does not copy the inside

`list.copy`, `list(x)`, and `x[:]` are shallow: the inner lists stay
shared. `copy.deepcopy` copies those too.

```python file=n09.py
import copy

nested = [[1], [2]]
shallow = nested.copy()
deep = copy.deepcopy(nested)
also = list(nested)
nested[0].append(99)
print(shallow, deep, also)
```

```text output
[[1, 99], [2]] [[1], [2]] [[1, 99], [2]]
```

## `[x] * n` repeats one object

Every row is the same list, so writing one cell writes them all. Build
each row in a comprehension when the items are mutable.

```python file=n10.py
grid_bad = [[0] * 2] * 2
grid_bad[0][0] = 1
print(grid_bad)
grid_ok = [[0] * 2 for _ in range(2)]
grid_ok[0][0] = 1
print(grid_ok)
```

```text output
[[1, 0], [1, 0]]
[[1, 0], [0, 0]]
```

## A dict key has to be hashable

Lists and dicts are not. A tuple of hashable items is. The error names
the unhashable type.

```python file=n11.py
print({(1, 2): "ok"}[(1, 2)])
try:
    {[1, 2]: "no"}
except TypeError as e:
    print(e)
```

```text output
ok
cannot use 'list' as a dict key (unhashable type: 'list')
```

## Exercises

```python file=exercise.py
def word_freq(text):
    """Lowercase word counts as a dict. Split on whitespace, strip .,!?"""
    raise NotImplementedError


def invert(d):
    """Map value -> sorted list of keys that had that value."""
    raise NotImplementedError


def dedupe(items):
    """Remove duplicates, keeping first occurrence order."""
    raise NotImplementedError


def top_n(d, n):
    """Return the n keys with the largest values, ties broken by key ascending."""
    raise NotImplementedError


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


results = [
    check("word_freq", word_freq("The cat. The hat! the end"), {"the": 3, "cat": 1, "hat": 1, "end": 1}),
    check("invert", invert({"a": 1, "b": 2, "c": 1}), {1: ["a", "c"], 2: ["b"]}),
    check("dedupe", dedupe([3, 1, 3, 2, 1]), [3, 1, 2]),
    check("top_n", top_n({"x": 5, "y": 9, "z": 5, "w": 1}, 3), ["y", "x", "z"]),
]
raise SystemExit(0 if all(results) else 1)
```

<details><summary>Solution</summary>

```python file=solution.py
from collections import Counter


def word_freq(text):
    words = (w.strip(".,!?").lower() for w in text.split())
    return dict(Counter(w for w in words if w))


def invert(d):
    out = {}
    for k, v in d.items():
        out.setdefault(v, []).append(k)
    return {v: sorted(ks) for v, ks in out.items()}


def dedupe(items):
    return list(dict.fromkeys(items))


def top_n(d, n):
    return sorted(d, key=lambda k: (-d[k], k))[:n]


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


results = [
    check("word_freq", word_freq("The cat. The hat! the end"), {"the": 3, "cat": 1, "hat": 1, "end": 1}),
    check("invert", invert({"a": 1, "b": 2, "c": 1}), {1: ["a", "c"], 2: ["b"]}),
    check("dedupe", dedupe([3, 1, 3, 2, 1]), [3, 1, 2]),
    check("top_n", top_n({"x": 5, "y": 9, "z": 5, "w": 1}, 3), ["y", "x", "z"]),
]
raise SystemExit(0 if all(results) else 1)
```

</details>

Next: [05 — Strings](05-strings.md)
