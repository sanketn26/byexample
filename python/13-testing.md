# Python 13 — Testing

`unittest` ships with Python; `pytest` is the popular layer on top. The
ideas — arrange/act/assert, isolation, fakes — are the same. Here we run the
tests from inside a script so the lesson is self-contained; normally you
run `python -m unittest` or `pytest`.

## Example

```python file=example.py
import doctest
import io
import re
import time
import unittest
from unittest import mock


def slugify(text):
    """Turn text into a URL slug.

    >>> slugify("Hello, World!")
    'hello-world'
    >>> slugify("  Many   spaces ")
    'many-spaces'
    """
    if not isinstance(text, str):
        raise TypeError("expected str")
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def stamp():
    return f"t={time.time()}"


def notify(channel, message):
    return channel.send(message.upper())


class TestSlugify(unittest.TestCase):
    def setUp(self):                      # runs before EVERY test
        self.cases = [("A B", "a-b"), ("--x--", "x"), ("", "")]

    def test_basic(self):
        self.assertEqual(slugify("Hello, World!"), "hello-world")

    def test_table(self):
        for raw, want in self.cases:
            with self.subTest(raw=raw):   # failures report which case
                self.assertEqual(slugify(raw), want)

    def test_raises(self):
        with self.assertRaises(TypeError):
            slugify(None)


class TestWithFakes(unittest.TestCase):
    def test_patch_a_dependency(self):
        with mock.patch("time.time", return_value=123.0):
            self.assertEqual(stamp(), "t=123.0")

    def test_mock_object(self):
        channel = mock.Mock()
        channel.send.return_value = True
        self.assertTrue(notify(channel, "hi"))
        channel.send.assert_called_once_with("HI")


class Broken(unittest.TestCase):
    def test_fails(self):
        self.assertEqual(1 + 1, 3)


def run(*classes):
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for cls in classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    return unittest.TextTestRunner(stream=io.StringIO()).run(suite)


good = run(TestSlugify, TestWithFakes)
print(good.testsRun, len(good.failures), len(good.errors), good.wasSuccessful())

bad = run(Broken)
print(bad.testsRun, len(bad.failures), bad.wasSuccessful())
print(bad.failures[0][1].strip().splitlines()[-1])

print(doctest.testmod())
```

```text output
5 0 0 True
1 1 False
AssertionError: 2 != 3
TestResults(failed=0, attempted=2)
```

## Details that bite

- Tests must be **independent and order-free**. Share nothing mutable;
  build fresh state in `setUp` (or fixtures in pytest).
- Test behaviour, not implementation. A test that breaks on every
  refactor is a tax, not a safety net.
- Patch where a name is *looked up*, not where it is defined:
  `mock.patch("mymodule.requests.get")`, not `"requests.get"`, when
  `mymodule` did `import requests`.
- Prefer injecting dependencies (a clock, a client) over patching; the
  code and its tests both get simpler (see the exercise).
- A passing test you have never seen fail proves little. Watch each new
  test fail first.
- Floating point: `assertAlmostEqual`, never `assertEqual`.
- `assert` statements are stripped under `python -O`; use `unittest`
  assertions or pytest's rewritten asserts.
- Coverage numbers measure what ran, not what was verified.

## Exercises

The tests are written for you. Implement `parse_duration` and
`RateLimiter` so they pass. Notice that `RateLimiter` receives a clock
instead of calling `time.time()` itself: that is what makes it testable.

```python file=exercise.py
import io
import unittest


def parse_duration(text):
    """'1h30m' -> 5400, '45s' -> 45, '2h' -> 7200, '1m1s' -> 61 (seconds).
    Raise ValueError for '', 'abc', '10', '5x'."""
    raise NotImplementedError


class RateLimiter:
    """Allow at most `limit` calls per `window` seconds (sliding window).
    `clock` is a zero-argument callable returning the current time."""

    def __init__(self, limit, window, clock):
        raise NotImplementedError

    def allow(self):
        raise NotImplementedError


class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now


class TestParseDuration(unittest.TestCase):
    def test_values(self):
        for text, want in [("1h30m", 5400), ("45s", 45), ("2h", 7200), ("1m1s", 61)]:
            with self.subTest(text=text):
                self.assertEqual(parse_duration(text), want)

    def test_invalid(self):
        for text in ["", "abc", "10", "5x"]:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_duration(text)


class TestRateLimiter(unittest.TestCase):
    def test_limit_and_window(self):
        clock = FakeClock()
        rl = RateLimiter(limit=2, window=10, clock=clock)
        self.assertTrue(rl.allow())
        self.assertTrue(rl.allow())
        self.assertFalse(rl.allow())     # third call inside the window
        clock.now = 9.9
        self.assertFalse(rl.allow())
        clock.now = 10.0                 # the first calls have expired
        self.assertTrue(rl.allow())

    def test_denied_calls_do_not_count(self):
        clock = FakeClock()
        rl = RateLimiter(1, 5, clock)
        self.assertTrue(rl.allow())
        for _ in range(10):
            self.assertFalse(rl.allow())
        clock.now = 5.0
        self.assertTrue(rl.allow())


suite = unittest.TestSuite()
loader = unittest.defaultTestLoader
suite.addTests(loader.loadTestsFromTestCase(TestParseDuration))
suite.addTests(loader.loadTestsFromTestCase(TestRateLimiter))
result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
print(f"{result.testsRun - len(result.failures) - len(result.errors)}/{result.testsRun} passed")
for case, trace in result.failures + result.errors:
    print("FAIL", case.id().split(".")[-1], "-", trace.strip().splitlines()[-1])
raise SystemExit(0 if result.wasSuccessful() else 1)
```

<details><summary>Solution</summary>

```python file=solution.py
import io
import re
import unittest
from collections import deque


def parse_duration(text):
    if not re.fullmatch(r"(\d+[hms])+", text):
        raise ValueError(f"bad duration {text!r}")
    units = {"h": 3600, "m": 60, "s": 1}
    return sum(int(n) * units[u] for n, u in re.findall(r"(\d+)([hms])", text))


class RateLimiter:
    def __init__(self, limit, window, clock):
        self.limit, self.window, self.clock = limit, window, clock
        self._calls = deque()

    def allow(self):
        now = self.clock()
        while self._calls and now - self._calls[0] >= self.window:
            self._calls.popleft()
        if len(self._calls) >= self.limit:
            return False
        self._calls.append(now)
        return True


class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now


class TestParseDuration(unittest.TestCase):
    def test_values(self):
        for text, want in [("1h30m", 5400), ("45s", 45), ("2h", 7200), ("1m1s", 61)]:
            with self.subTest(text=text):
                self.assertEqual(parse_duration(text), want)

    def test_invalid(self):
        for text in ["", "abc", "10", "5x"]:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_duration(text)


class TestRateLimiter(unittest.TestCase):
    def test_limit_and_window(self):
        clock = FakeClock()
        rl = RateLimiter(limit=2, window=10, clock=clock)
        self.assertTrue(rl.allow())
        self.assertTrue(rl.allow())
        self.assertFalse(rl.allow())     # third call inside the window
        clock.now = 9.9
        self.assertFalse(rl.allow())
        clock.now = 10.0                 # the first calls have expired
        self.assertTrue(rl.allow())

    def test_denied_calls_do_not_count(self):
        clock = FakeClock()
        rl = RateLimiter(1, 5, clock)
        self.assertTrue(rl.allow())
        for _ in range(10):
            self.assertFalse(rl.allow())
        clock.now = 5.0
        self.assertTrue(rl.allow())


suite = unittest.TestSuite()
loader = unittest.defaultTestLoader
suite.addTests(loader.loadTestsFromTestCase(TestParseDuration))
suite.addTests(loader.loadTestsFromTestCase(TestRateLimiter))
result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
print(f"{result.testsRun - len(result.failures) - len(result.errors)}/{result.testsRun} passed")
for case, trace in result.failures + result.errors:
    print("FAIL", case.id().split(".")[-1], "-", trace.strip().splitlines()[-1])
raise SystemExit(0 if result.wasSuccessful() else 1)
```

</details>

Next: [14 — Capstone: an LRU cache](14-capstone-lru.md)
