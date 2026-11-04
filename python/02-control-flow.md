# Python 02 — Control Flow

Python uses indentation for blocks. `for` iterates over any iterable.
There is no C-style `for(;;)`.

## `if` picks one branch

`elif` adds another test. The conditional expression chooses a value:
`a if cond else b`.

```python file=n01.py
n = 15
if n % 15 == 0:
    kind = "fizzbuzz"
elif n % 3 == 0:
    kind = "fizz"
else:
    kind = "other"
print(kind, "even" if n % 2 == 0 else "odd")
```

```text output
fizzbuzz odd
```

## Comparisons can chain

`0 < x < 10` means `0 < x and x < 10`. Python evaluates `x` once.

```python file=n02.py
x = 5
print(0 < x < 10, 0 < x < 5)
```

```text output
True False
```

## `for` walks any iterable

`range(a, b)` stops before `b`. Pass a negative step to count down.
`enumerate` adds an index. `zip` stops at the shorter sequence.

```python file=n03.py
for i in range(3):
    print("i =", i)
for idx, ch in enumerate("abc", start=1):
    print(idx, ch)
for name, score in zip(["ann", "bob"], [90, 85]):
    print(name, score)
print(list(range(5, 0, -1)))
```

```text output
i = 0
i = 1
i = 2
1 a
2 b
3 c
ann 90
bob 85
[5, 4, 3, 2, 1]
```

## The loop variable survives the loop

After `for i in ...`, `i` still exists and holds the last value.

```python file=n04.py
for i in range(3):
    pass
print(i)
```

```text output
2
```

## `break` leaves, `continue` skips

`continue` jumps to the next iteration. `break` leaves the loop entirely.

```python file=n05.py
total, k = 0, 0
while True:
    k += 1
    if k % 2 == 0:
        continue
    if k > 9:
        break
    total += k
print("odd sum:", total)
```

```text output
odd sum: 25
```

## `for`/`else` runs when nothing breaks

The `else` belongs to the loop, not to an `if`. It runs only if the loop
never hit `break`. That is the idiomatic form of a search that found nothing.

```python file=n06.py
for d in range(2, 10):
    if 97 % d == 0:
        print("composite")
        break
else:
    print("97 is prime")
```

```text output
97 is prime
```

## `match` compares structure

A pattern can unpack a list or a dict, bind names, and combine alternatives
with `|`. A guard is an `if` on the pattern. `case _` is the default.

```python file=n07.py
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
```

```text output
going north
bye
5
negative
unknown
```

## A bare name in `match` captures

`case RED:` binds a new local. It does not compare against the variable
`RED`. To compare, use a literal or a dotted name such as `Color.RED`.

```python file=n08.py
RED = "red"


def captured(value):
    match value:
        case RED:
            return ("captured", RED)


class Color:
    RED = "red"


def by_value(value):
    match value:
        case Color.RED:
            return "red"
        case _:
            return "other"


print(captured("blue"), RED)
print(by_value("red"), by_value("blue"))
```

```text output
('captured', 'blue') red
red other
```

## A comprehension is a loop expression

The `if` filter sits after the `for`. A dict comprehension builds a mapping
the same way.

```python file=n09.py
squares = [i * i for i in range(6) if i % 2 == 0]
print(squares)
print({w: len(w) for w in ["a", "bb", "ccc"]})
```

```text output
[0, 4, 16]
{'a': 1, 'bb': 2, 'ccc': 3}
```

## Do not edit a list you are walking

Removing the current item shifts the rest left, so the loop skips one.
Iterate a copy (`items[:]`) or build a new list.

```python file=n10.py
items = [1, 2, 2, 3]
for x in items:
    if x == 2:
        items.remove(x)
print("skipped", items)

items = [1, 2, 2, 3]
for x in items[:]:
    if x == 2:
        items.remove(x)
print("copy", items)
```

```text output
skipped [1, 2, 3]
copy [1, 3]
```

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
