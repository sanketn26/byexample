# Python 07 — Errors and Exceptions

Python signals failure with exceptions. The style is EAFP: easier to ask
forgiveness than permission. Try the operation and handle the failure.

## `else` runs only on success, `finally` always runs

`except` handles one type. `else` runs when the `try` raised nothing.
`finally` runs on the way out, including on `return`. A `return` inside
`finally` replaces the pending result and swallows an exception. Don't
write one.

```python file=n01.py
def parse(text):
    try:
        value = int(text)
    except ValueError as e:
        print("  bad input:", e)
        return None
    else:
        print("  parsed ok")
        return value
    finally:
        print("  done with", repr(text))


print(parse("42"))
print(parse("4x2"))


def report():
    try:
        return "value"
    finally:
        print("finally ran")


print(report())
```

```text output
  parsed ok
  done with '42'
42
  bad input: invalid literal for int() with base 10: '4x2'
  done with '4x2'
None
finally ran
value
```

## The first matching `except` wins

A tuple catches several types. Put the more specific type first: `KeyError`
is a `LookupError`, so a handler for the base class hides the subclass.

```python file=n02.py
def lookup(d, k):
    try:
        return d[k]
    except (KeyError, IndexError) as e:
        return f"missing {e!r}"


print(lookup({"a": 1}, "b"), lookup([1], 5))
try:
    raise KeyError("k")
except LookupError:
    print("lookup")
except KeyError:
    print("key")
```

```text output
missing KeyError('b') missing IndexError('list index out of range')
lookup
```

## Raise a type of your own

Subclass `Exception`, not `BaseException`. `super().__init__` sets the
message. Extra attributes travel on the instance.

```python file=n03.py
class ValidationError(Exception):
    def __init__(self, field, message):
        super().__init__(f"{field}: {message}")
        self.field = field


def validate_age(age):
    if not isinstance(age, int):
        raise ValidationError("age", "must be an int")
    if age < 0:
        raise ValidationError("age", "must be >= 0")
    return age


try:
    validate_age(-1)
except ValidationError as e:
    print(e, "| field =", e.field)
```

```text output
age: must be >= 0 | field = age
```

## `raise` can chain or re-raise

`raise RuntimeError(...) from e` stores `e` on `__cause__`. A bare `raise`
re-raises the active exception and keeps its traceback. `raise e` adds a
frame, so that traceback is longer.

```python file=n04.py
import traceback


def load_port(cfg):
    try:
        return int(cfg["port"])
    except (KeyError, ValueError) as e:
        raise RuntimeError("bad config") from e


def via_bare():
    try:
        raise ValueError("v")
    except ValueError:
        raise


def via_name():
    try:
        raise ValueError("v")
    except ValueError as e:
        raise e


def frames(fn):
    try:
        fn()
    except ValueError as err:
        return len(traceback.extract_tb(err.__traceback__))


try:
    load_port({"port": "http"})
except RuntimeError as e:
    print(e, "<-", repr(e.__cause__))
print(frames(via_bare) < frames(via_name))
```

```text output
bad config <- ValueError("invalid literal for int() with base 10: 'http'")
True
```

## `with` runs the cleanup

`__enter__` acquires and `__exit__` releases. Returning a false value from
`__exit__` does not swallow the exception, so the `KeyError` still propagates.

```python file=n05.py
class Resource:
    def __enter__(self):
        print("acquire")
        return self

    def __exit__(self, exc_type, exc, tb):
        print("release", exc_type.__name__ if exc_type else None)
        return False


try:
    with Resource():
        raise KeyError("boom")
except KeyError:
    print("caught after release")
```

```text output
acquire
release KeyError
caught after release
```

## `@contextmanager` is the short form

Code before `yield` is setup. The `finally` after `yield` is cleanup.
`suppress` ignores the named exceptions and nothing else.

```python file=n06.py
from contextlib import contextmanager, suppress


@contextmanager
def tag(name):
    print(f"<{name}>")
    try:
        yield
    finally:
        print(f"</{name}>")


with tag("b"):
    print("text")

with suppress(FileNotFoundError):
    open("/definitely/not/here")
print("suppressed")
```

```text output
<b>
text
</b>
suppressed
```

## Catch `Exception`, never a bare `except`

A bare `except:` also catches `KeyboardInterrupt` and `SystemExit`. Those
inherit from `BaseException`, not from `Exception`. `Exception` is the
widest handler you want.

```python file=n07.py
print(
    issubclass(KeyError, LookupError),
    issubclass(KeyboardInterrupt, Exception),
    issubclass(SystemExit, Exception),
)
```

```text output
True False False
```

## The `as` name ends with the block

At the end of `except ... as e`, Python deletes `e` so the traceback can
be freed. Using the name afterwards raises `NameError`.

```python file=n08.py
try:
    try:
        raise ValueError("z")
    except ValueError as e:
        print("caught", e)
    print(e)
except NameError as e:
    print(type(e).__name__)
```

```text output
caught z
NameError
```

## `assert` is for programmer errors

A failed assert raises `AssertionError`. Running with `-O` strips assert
statements, so they are not a runtime check of user input.

```python file=n09.py
try:
    assert 1 + 1 == 3, "math broke"
except AssertionError as e:
    print("assertion:", e)
```

```text output
assertion: math broke
```

## `except*` splits an `ExceptionGroup`

One `raise` can carry several failures. Each `except*` handles one type
and leaves the rest for the next clause. This needs Python 3.11 or newer.

```python file=n10.py
try:
    raise ExceptionGroup("batch", [ValueError("a"), TypeError("b")])
except* ValueError as eg:
    print("value errors:", [str(e) for e in eg.exceptions])
except* TypeError as eg:
    print("type errors:", [str(e) for e in eg.exceptions])
```

```text output
value errors: ['a']
type errors: ['b']
```

## Don't use exceptions as the normal path of a hot loop

`try` is cheap when nothing is raised. Raising is not. `if key in d` can
race with another thread that changes the dict; the `try` form does not.

```python file=n11.py
d = {"a": 1}
if "a" in d:
    print(d["a"])
try:
    print(d["missing"])
except KeyError:
    print("missing")
```

```text output
1
missing
```

## Exercises

```python file=exercise.py
class InsufficientFunds(Exception):
    """Carry `needed` and `available` attributes."""


def withdraw(balance, amount):
    """Return new balance. Raise ValueError if amount <= 0,
    InsufficientFunds (with needed/available) if amount > balance."""
    raise NotImplementedError


def safe_int(text, default=None):
    """int(text), or `default` if it cannot be parsed (also for None)."""
    raise NotImplementedError


def read_config(d):
    """Return int(d['port']). On a missing key raise ConfigError('missing port');
    on a non-integer raise ConfigError('invalid port') — both chained
    (`__cause__` set to the original exception)."""
    raise NotImplementedError


class ConfigError(Exception):
    pass


class Timer:
    """Context manager recording `elapsed_calls`: increments class counter
    Timer.exits on every exit, even on error, and does NOT swallow errors."""
    exits = 0


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


def raised(fn):
    try:
        fn()
    except Exception as e:
        return e
    return None


def run():
    out = [check("withdraw", withdraw(100, 30), 70)]
    e = raised(lambda: withdraw(10, 50))
    out.append(check("insufficient", (type(e).__name__, getattr(e, "needed", None),
                                      getattr(e, "available", None)),
                     ("InsufficientFunds", 50, 10)))
    out.append(check("neg", type(raised(lambda: withdraw(10, -1))).__name__, "ValueError"))
    out += [check("safe_int", safe_int("12"), 12),
            check("safe_int bad", safe_int("x", -1), -1),
            check("safe_int None", safe_int(None, 0), 0)]
    e = raised(lambda: read_config({}))
    out.append(check("missing", (str(e), type(e.__cause__).__name__), ("missing port", "KeyError")))
    e = raised(lambda: read_config({"port": "x"}))
    out.append(check("invalid", (str(e), type(e.__cause__).__name__), ("invalid port", "ValueError")))
    try:
        with Timer():
            raise KeyError("x")
    except KeyError:
        pass
    with Timer():
        pass
    out.append(check("timer exits", Timer.exits, 2))
    return out


raise SystemExit(0 if all(run()) else 1)
```

<details><summary>Solution</summary>

```python file=solution.py
class InsufficientFunds(Exception):
    def __init__(self, needed, available):
        super().__init__(f"need {needed}, have {available}")
        self.needed = needed
        self.available = available


def withdraw(balance, amount):
    if amount <= 0:
        raise ValueError("amount must be positive")
    if amount > balance:
        raise InsufficientFunds(amount, balance)
    return balance - amount


def safe_int(text, default=None):
    try:
        return int(text)
    except (ValueError, TypeError):
        return default


class ConfigError(Exception):
    pass


def read_config(d):
    try:
        return int(d["port"])
    except KeyError as e:
        raise ConfigError("missing port") from e
    except ValueError as e:
        raise ConfigError("invalid port") from e


class Timer:
    exits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        Timer.exits += 1
        return False


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


def raised(fn):
    try:
        fn()
    except Exception as e:
        return e
    return None


def run():
    out = [check("withdraw", withdraw(100, 30), 70)]
    e = raised(lambda: withdraw(10, 50))
    out.append(check("insufficient", (type(e).__name__, getattr(e, "needed", None),
                                      getattr(e, "available", None)),
                     ("InsufficientFunds", 50, 10)))
    out.append(check("neg", type(raised(lambda: withdraw(10, -1))).__name__, "ValueError"))
    out += [check("safe_int", safe_int("12"), 12),
            check("safe_int bad", safe_int("x", -1), -1),
            check("safe_int None", safe_int(None, 0), 0)]
    e = raised(lambda: read_config({}))
    out.append(check("missing", (str(e), type(e.__cause__).__name__), ("missing port", "KeyError")))
    e = raised(lambda: read_config({"port": "x"}))
    out.append(check("invalid", (str(e), type(e.__cause__).__name__), ("invalid port", "ValueError")))
    try:
        with Timer():
            raise KeyError("x")
    except KeyError:
        pass
    with Timer():
        pass
    out.append(check("timer exits", Timer.exits, 2))
    return out


raise SystemExit(0 if all(run()) else 1)
```

</details>

Next: [08 — References and memory](08-references-memory.md)
