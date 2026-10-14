# Python 07 — Errors and Exceptions

Python signals failure with exceptions. The style is EAFP: *easier to ask
forgiveness than permission* — try the operation and handle the failure.

## Example

```python file=example.py
# Basic try / except / else / finally
def parse(text):
    try:
        value = int(text)
    except ValueError as e:
        print("  bad input:", e)
        return None
    else:
        print("  parsed ok")        # runs only if no exception
        return value
    finally:
        print("  done with", repr(text))   # always runs

print(parse("42"))
print(parse("4x2"))

# Catch several types; order matters (most specific first)
def lookup(d, k):
    try:
        return d[k]
    except (KeyError, IndexError) as e:
        return f"missing {e!r}"

print(lookup({"a": 1}, "b"), lookup([1], 5))

# Raising, and custom exception types
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

# Exception chaining: preserve the original cause
def load_port(cfg):
    try:
        return int(cfg["port"])
    except (KeyError, ValueError) as e:
        raise RuntimeError("bad config") from e

try:
    load_port({"port": "http"})
except RuntimeError as e:
    print(e, "<-", repr(e.__cause__))

# Context managers guarantee cleanup
class Resource:
    def __enter__(self):
        print("acquire")
        return self
    def __exit__(self, exc_type, exc, tb):
        print("release", exc_type.__name__ if exc_type else None)
        return False                 # False: do not swallow the exception

try:
    with Resource():
        raise KeyError("boom")
except KeyError:
    print("caught after release")

# contextlib makes this shorter
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

# The hierarchy: catch Exception, never a bare `except:`
print(issubclass(KeyError, LookupError), issubclass(KeyboardInterrupt, Exception))

# assert is for programmer errors; it can be disabled with -O
try:
    assert 1 + 1 == 3, "math broke"
except AssertionError as e:
    print("assertion:", e)

# ExceptionGroup / except* (3.11+) for concurrent failures
try:
    raise ExceptionGroup("batch", [ValueError("a"), TypeError("b")])
except* ValueError as eg:
    print("value errors:", [str(e) for e in eg.exceptions])
except* TypeError as eg:
    print("type errors:", [str(e) for e in eg.exceptions])
```

```text output
  parsed ok
  done with '42'
42
  bad input: invalid literal for int() with base 10: '4x2'
  done with '4x2'
None
missing KeyError('b') missing IndexError('list index out of range')
age: must be >= 0 | field = age
bad config <- ValueError("invalid literal for int() with base 10: 'http'")
acquire
release KeyError
caught after release
<b>
text
</b>
suppressed
True False
assertion: math broke
value errors: ['a']
type errors: ['b']
```

## Details that bite

- A bare `except:` also catches `KeyboardInterrupt` and `SystemExit`. Catch
  `Exception` at the broadest.
- `finally` runs even on `return`; a `return` inside `finally` swallows
  exceptions — don't.
- `raise` with no argument re-raises the active exception, preserving its
  traceback. `raise e` adds a frame; `raise X from e` sets `__cause__`.
- The `as e` name is deleted at the end of the `except` block.
- Don't use exceptions for ordinary control flow *inside hot loops*;
  `try` is cheap when nothing is raised, `raise` is not.
- LBYL (`if key in d`) can race with other threads or processes; EAFP
  doesn't.

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
