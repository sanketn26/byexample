# Python 01 — Values, Variables and Printing

Everything in Python is an object, and a variable is a name bound to an
object. You never declare a type; the object carries it. There are no
constants: `MAX = 10` is a convention, and a later assignment replaces it.

## Integers do not overflow

`int` grows until memory runs out. `**` is exponentiation.

```python file=n01.py
count = 42
power = 2 ** 100
print(count)
print(power)
```

```text output
42
1267650600228229401496703205376
```

## Division has two operators

`/` always returns a float. `//` and `%` floor toward negative infinity, so
`-7 // 2` is `-4` and `-7 % 3` is `2`.

```python file=n02.py
print(3 / 2)
print(7 // 2, 7 % 3)
print(-7 // 2, -7 % 3)
```

```text output
1.5
3 1
-4 2
```

## Decimal fractions are approximate

`0.1 + 0.2` is not `0.3`, because floats are binary. Use `math.isclose` or
the `decimal` module when the exact decimal matters.

```python file=n03.py
print(0.1 + 0.2)
print(0.1 + 0.2 == 0.3)
```

```text output
0.30000000000000004
False
```

## Most values are truthy

Only `0`, `0.0`, `""`, `[]`, `{}`, `set()`, `()`, `None`, and `False` are
falsy. The string `"0"` is truthy. `None` means "no value".

```python file=n04.py
flag = True
nothing = None
print(flag and not nothing)
print(bool(0), bool(""), bool([]), bool("0"), bool([0]))
```

```text output
True
False False False True True
```

## The object carries the type

`type` reports the class. `bool` is a subclass of `int`, so `True + True`
is `2`. `isinstance` follows that relationship; `type(True) is int` does not.

```python file=n05.py
count = 42
price = 9.99
flag = True
nothing = None
print(type(count), type(price), type(flag), type(nothing))
print(isinstance(True, int))
print(True + True)
```

```text output
<class 'int'> <class 'float'> <class 'bool'> <class 'NoneType'>
True
2
```

## `is` tests identity, `==` tests equality

Two equal lists are not the same object. Use `is` for `None` (`x is None`)
and for nothing else you care about comparing by value.

```python file=n06.py
print(None is None)
print([] == [])
print([] is [])
```

```text output
True
True
False
```

## One assignment can bind several names

The right-hand side is evaluated first, which is why a swap needs no
temporary. A starred name collects whatever is left.

```python file=n07.py
a, b = 1, 2
a, b = b, a
first, *rest = [10, 20, 30]
print(a, b, first, rest)
```

```text output
2 1 10 [20, 30]
```

## f-strings format in place

The format spec after `:` does the work of `printf`. `!r` calls `repr`.
Underscores in a numeric literal are ignored.

```python file=n08.py
name = "Ada"
count = 42
price = 9.99
power = 2 ** 100
print(f"{name} has {count} items costing {price:.1f} each")
print(f"{count:05d} | {price:>8.2f} | {power:.3e} | {255:#x}")
print(f"{name!r} {1_000_000:,}")
```

```text output
Ada has 42 items costing 10.0 each
00042 |     9.99 | 1.268e+30 | 0xff
'Ada' 1,000,000
```

## `print` joins its arguments

`sep` goes between arguments. `end` replaces the trailing newline.

```python file=n09.py
print("a", "b", "c", sep="-", end="!\n")
```

```text output
a-b-c!
```

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
