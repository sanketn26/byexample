# Python 02 — Control Flow

Python uses indentation for blocks, `for` iterates over *any iterable*, and
there is no C-style `for(;;)`.

## Example

```python file=example.py
# if / elif / else, plus the conditional expression
n = 15
if n % 15 == 0:
    kind = "fizzbuzz"
elif n % 3 == 0:
    kind = "fizz"
else:
    kind = "other"
print(kind, "even" if n % 2 == 0 else "odd")

# Chained comparisons
x = 5
print(0 < x < 10, 0 < x < 5)

# for over a range, with enumerate and zip
for i in range(3):
    print("i =", i)
for idx, ch in enumerate("abc", start=1):
    print(idx, ch)
for name, score in zip(["ann", "bob"], [90, 85]):
    print(name, score)

# while, break and continue
total, k = 0, 0
while True:
    k += 1
    if k % 2 == 0:
        continue
    if k > 9:
        break
    total += k
print("odd sum:", total)

# for/else: else runs only if the loop did NOT break
for d in range(2, 10):
    if 97 % d == 0:
        print("composite")
        break
else:
    print("97 is prime")

# match (structural pattern matching, Python 3.10+)
def classify(cmd):
    match cmd:
        case ["go", direction]:
            return f"going {direction}"
        case ["quit"] | ["exit"]:
            return "bye"
        case {"op": "add", "args": [a, b]}:
            return a + b
        case int() as num if num < 0:
            return "negative"
        case _:
            return "unknown"

for c in (["go", "north"], ["exit"], {"op": "add", "args": [2, 3]}, -4, "x"):
    print(classify(c))

# Comprehensions are loops as expressions
squares = [i * i for i in range(6) if i % 2 == 0]
print(squares)
print({w: len(w) for w in ["a", "bb", "ccc"]})
```

```text output
fizzbuzz odd
True False
i = 0
i = 1
i = 2
1 a
2 b
3 c
ann 90
bob 85
odd sum: 25
97 is prime
going north
bye
5
negative
unknown
[0, 4, 16]
{'a': 1, 'bb': 2, 'ccc': 3}
```

## Details that bite

- `range(a, b)` excludes `b`. `range(5, 0, -1)` counts down.
- Loop variables leak: after `for i in ...`, `i` still exists.
- `match` binds names in patterns: `case x:` is a *capture*, not a comparison.
  To compare against a constant, use a dotted name (`Color.RED`) or a literal.
- Never modify a list while iterating over it; iterate over a copy
  (`for x in items[:]`) or build a new list.
- `for/else` is rarely used but is the idiomatic "search with no hit" form.

## Exercises

```python file=exercise.py
def fizzbuzz(n):
    """Return a list of strings for 1..n: 'Fizz' for multiples of 3,
    'Buzz' for 5, 'FizzBuzz' for both, otherwise the number as a string."""
    raise NotImplementedError


def collatz_steps(n):
    """Number of steps to reach 1 using: even -> n/2, odd -> 3n+1.
    collatz_steps(1) == 0. Raise ValueError if n < 1."""
    raise NotImplementedError


def first_repeat(items):
    """Return the first item that appears a second time, or None."""
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
    check("fizzbuzz(15)[-5:]", fizzbuzz(15)[-5:], ["11", "Fizz", "13", "14", "FizzBuzz"]),
    check("collatz(1)", collatz_steps(1), 0),
    check("collatz(27)", collatz_steps(27), 111),
    raises("collatz(0)", lambda: collatz_steps(0), ValueError),
    check("first_repeat", first_repeat([3, 1, 4, 1, 5, 3]), 1),
    check("first_repeat none", first_repeat([1, 2, 3]), None),
]
raise SystemExit(0 if all(results) else 1)
```

<details><summary>Solution</summary>

```python file=solution.py
def fizzbuzz(n):
    out = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            out.append("FizzBuzz")
        elif i % 3 == 0:
            out.append("Fizz")
        elif i % 5 == 0:
            out.append("Buzz")
        else:
            out.append(str(i))
    return out


def collatz_steps(n):
    if n < 1:
        raise ValueError("n must be >= 1")
    steps = 0
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        steps += 1
    return steps


def first_repeat(items):
    seen = set()
    for item in items:
        if item in seen:
            return item
        seen.add(item)
    return None


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
    check("fizzbuzz(15)[-5:]", fizzbuzz(15)[-5:], ["11", "Fizz", "13", "14", "FizzBuzz"]),
    check("collatz(1)", collatz_steps(1), 0),
    check("collatz(27)", collatz_steps(27), 111),
    raises("collatz(0)", lambda: collatz_steps(0), ValueError),
    check("first_repeat", first_repeat([3, 1, 4, 1, 5, 3]), 1),
    check("first_repeat none", first_repeat([1, 2, 3]), None),
]
raise SystemExit(0 if all(results) else 1)
```

</details>

Next: [03 — Functions](03-functions.md)
