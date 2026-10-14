# Python 01 — Values, Variables and Printing

Everything in Python is an object, and a variable is just a *name* bound to an
object. You never declare a type; the object carries it.

## Example

```python file=example.py
# Numbers
count = 42            # int: unlimited precision
price = 9.99          # float: 64-bit IEEE 754
ratio = 3 / 2         # true division always gives a float
floor = 7 // 2        # floor division
rem = 7 % 3           # remainder
power = 2 ** 100      # ints never overflow

print(count, price, ratio, floor, rem)
print(power)

# Floats are binary, so decimal fractions are approximate
print(0.1 + 0.2)
print(0.1 + 0.2 == 0.3)

# Booleans, None, and truthiness
flag = True
nothing = None
print(flag and not nothing)
print(bool(0), bool(""), bool([]), bool("0"), bool([0]))

# Inspecting types
print(type(count), type(price), type(flag), type(nothing))
print(isinstance(True, int))      # bool is a subclass of int

# Multiple assignment, swapping, and unpacking
a, b = 1, 2
a, b = b, a
first, *rest = [10, 20, 30]
print(a, b, first, rest)

# Formatting: f-strings are the default tool
name = "Ada"
print(f"{name} has {count} items costing {price:.1f} each")
print(f"{count:05d} | {price:>8.2f} | {power:.3e} | {255:#x}")
print(f"{name!r} {1_000_000:,}")

# print() options
print("a", "b", "c", sep="-", end="!\n")
```

```text output
42 9.99 1.5 3 1
1267650600228229401496703205376
0.30000000000000004
False
True
False False False True True
<class 'int'> <class 'float'> <class 'bool'> <class 'NoneType'>
True
2 1 10 [20, 30]
Ada has 42 items costing 10.0 each
00042 |     9.99 | 1.268e+30 | 0xff
'Ada' 1,000,000
a-b-c!
```

## Details that bite

- `/` is always float division; use `//` for integers. `-7 // 2` is `-4`
  (floors toward negative infinity), and `%` follows the same rule, so
  `-7 % 3 == 2`.
- `0.1 + 0.2 != 0.3`. Use `math.isclose(a, b)` or the `decimal` module for
  money.
- Only `0`, `0.0`, `""`, `[]`, `{}`, `set()`, `()`, `None` and `False` are
  falsy. The string `"0"` is **truthy**.
- `is` tests identity, `==` tests equality. Use `is` only for `None`
  (`x is None`).
- `bool` is a subclass of `int`: `True + True == 2`.
- Python has no constants. `MAX = 10` is a convention, not enforcement.

## Exercises

Implement the three functions. Run the file; every line should say `PASS`.

```python file=exercise.py
def celsius_to_fahrenheit(c):
    """Return the Fahrenheit value for c degrees Celsius (float)."""
    raise NotImplementedError


def divmod_floor(a, b):
    """Return (quotient, remainder) using floor division, without divmod()."""
    raise NotImplementedError


def describe(value):
    """Return 'none', 'falsy' or 'truthy' for value.
    None -> 'none'; other falsy values -> 'falsy'; everything else -> 'truthy'.
    """
    raise NotImplementedError


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


results = [
    check("c2f(100)", celsius_to_fahrenheit(100), 212.0),
    check("c2f(-40)", celsius_to_fahrenheit(-40), -40.0),
    check("divmod(7,2)", divmod_floor(7, 2), (3, 1)),
    check("divmod(-7,2)", divmod_floor(-7, 2), (-4, 1)),
    check("describe(None)", describe(None), "none"),
    check("describe('')", describe(""), "falsy"),
    check("describe('0')", describe("0"), "truthy"),
]
raise SystemExit(0 if all(results) else 1)
```

<details><summary>Solution</summary>

```python file=solution.py
def celsius_to_fahrenheit(c):
    return c * 9 / 5 + 32


def divmod_floor(a, b):
    q = a // b
    return q, a - q * b


def describe(value):
    if value is None:
        return "none"
    return "truthy" if value else "falsy"


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


results = [
    check("c2f(100)", celsius_to_fahrenheit(100), 212.0),
    check("c2f(-40)", celsius_to_fahrenheit(-40), -40.0),
    check("divmod(7,2)", divmod_floor(7, 2), (3, 1)),
    check("divmod(-7,2)", divmod_floor(-7, 2), (-4, 1)),
    check("describe(None)", describe(None), "none"),
    check("describe('')", describe(""), "falsy"),
    check("describe('0')", describe("0"), "truthy"),
]
raise SystemExit(0 if all(results) else 1)
```

</details>

Next: [02 — Control flow](02-control-flow.md)
