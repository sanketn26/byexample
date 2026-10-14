# Python 04 — Collections

Four built-ins cover almost everything: `list`, `tuple`, `dict`, `set`.

| type    | ordered | mutable | duplicates | lookup        |
|---------|---------|---------|------------|---------------|
| `list`  | yes     | yes     | yes        | O(n) by value |
| `tuple` | yes     | no      | yes        | O(n) by value |
| `dict`  | insertion | yes   | unique keys | O(1) by key  |
| `set`   | no      | yes     | no         | O(1)          |

## Example

```python file=example.py
# Lists
nums = [5, 3, 8, 1]
nums.append(9)
nums.insert(0, 7)
print(nums, len(nums), nums[-1], nums[1:3], nums[::-1])
nums.sort()
print(nums, sorted(nums, reverse=True))
print(nums.pop(), nums.index(5), 8 in nums)

# Slicing copies; assignment aliases
a = [1, 2, 3]
b = a
c = a[:]
a.append(4)
print(b, c)

# Tuples: immutable, hashable, great for records and dict keys
point = (3, 4)
x, y = point
print(x, y, point + (5,))
single = (1,)          # the comma makes the tuple
print(type((1)), type(single))

# Dicts
ages = {"ann": 31, "bob": 25}
ages["cy"] = 40
print(ages.get("dan"), ages.get("dan", 0), "ann" in ages)
for name, age in sorted(ages.items()):
    print(name, age)
print(list(ages), list(ages.values()))
del ages["bob"]
print(ages.pop("zed", "missing"))

# Counting and grouping
from collections import Counter, defaultdict
print(Counter("mississippi").most_common(2))
groups = defaultdict(list)
for word in ["apple", "avocado", "banana", "blueberry", "cherry"]:
    groups[word[0]].append(word)
print(dict(groups))

# Sets
s = {1, 2, 3}
t = {3, 4}
print(s | t, s & t, s - t, s ^ t)
print(list(dict.fromkeys([3, 1, 3, 2, 1])))   # dedupe, keep order

# Comprehensions
matrix = [[1, 2, 3], [4, 5, 6]]
print([[row[i] for row in matrix] for i in range(3)])  # transpose
print({k: v for k, v in zip("abc", range(3))})

# Copies: shallow vs deep
import copy
nested = [[1], [2]]
shallow = nested.copy()
deep = copy.deepcopy(nested)
nested[0].append(99)
print(shallow, deep)

# The aliasing trap
grid_bad = [[0] * 2] * 2
grid_bad[0][0] = 1
print(grid_bad)
grid_ok = [[0] * 2 for _ in range(2)]
grid_ok[0][0] = 1
print(grid_ok)
```

```text output
[7, 5, 3, 8, 1, 9] 6 9 [5, 3] [9, 1, 8, 3, 5, 7]
[1, 3, 5, 7, 8, 9] [9, 8, 7, 5, 3, 1]
9 2 True
[1, 2, 3, 4] [1, 2, 3]
3 4 (3, 4, 5)
<class 'int'> <class 'tuple'>
None 0 True
ann 31
bob 25
cy 40
['ann', 'bob', 'cy'] [31, 25, 40]
missing
[('i', 4), ('s', 4)]
{'a': ['apple', 'avocado'], 'b': ['banana', 'blueberry'], 'c': ['cherry']}
{1, 2, 3, 4} {3} {1, 2} {1, 2, 4}
[3, 1, 2]
[[1, 4], [2, 5], [3, 6]]
{'a': 0, 'b': 1, 'c': 2}
[[1, 99], [2]] [[1], [2]]
[[1, 0], [1, 0]]
[[1, 0], [0, 0]]
```

## Details that bite

- `[x] * n` copies the *reference* n times. Use a comprehension for nested
  mutable items.
- Dict keys must be hashable: lists and dicts are not; tuples of hashables
  are.
- `d[key]` raises `KeyError`; `d.get(key)` returns `None`.
- `list.sort()` sorts in place and returns `None`; `sorted()` returns a new
  list. Both are stable.
- `x in some_list` is a linear scan. Use a `set` for repeated membership
  tests.
- Sets and dicts iterate in unspecified order for sets, insertion order for
  dicts (guaranteed since 3.7).

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
