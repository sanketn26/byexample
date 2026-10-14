# Python 05 — Strings and Text

A `str` is an immutable sequence of Unicode code points. Raw bytes are a
separate type, `bytes`. Keeping those two apart is most of the battle.

## Example

```python file=example.py
s = "  Hello, World  "
print(repr(s.strip()), s.lower().strip(), s.count("l"))
print(s.strip().split(", "), "-".join(["a", "b", "c"]))
print(s.find("World"), s.find("nope"), s.strip().startswith("Hello"))
print(s.replace("l", "L", 2).strip())

# Indexing and slicing (immutable: s[0] = "x" raises TypeError)
w = "python"
print(w[0], w[-1], w[1:4], w[::-1], len(w))

# Unicode: code points vs bytes
t = "café"
print(len(t), len(t.encode("utf-8")), t.encode("utf-8"))
print(b"caf\xc3\xa9".decode("utf-8") == t)
print(ord("A"), chr(9731), "\u00e9" == "é")

# A combined character is TWO code points
import unicodedata
e1 = "\u00e9"        # é precomposed
e2 = "e\u0301"       # e + combining acute
print(e1 == e2, len(e1), len(e2))
print(unicodedata.normalize("NFC", e2) == e1)

# Formatting mini-language
print(f"{3.14159:.2f}|{42:>6}|{42:<6}|{42:^6}|{'x':*^5}")
print("{0} {1} {0}".format("a", "b"), "%s=%d" % ("n", 5))
width = 8
print(f"{'right':>{width}}")
print(f"{1234567.891:,.1f}", f"{0.256:.1%}", f"{10:b}")
x = 7
print(f"{x=}")                       # self-documenting (3.8+)

# Splitting and parsing
line = "name=Ada;age=36;city=London"
record = dict(pair.split("=") for pair in line.split(";"))
print(record, int(record["age"]) + 1)
print("a  b   c".split(), "a  b".split(" "))
print("line1\nline2\n".splitlines())

# Multi-line and raw strings
doc = """first
second"""
print(doc.upper().split("\n"))
print(r"C:\new\table", len(r"\n"))

# Building strings in a loop: use join, not +=
parts = [str(i) for i in range(5)]
print("".join(parts))

# Predicates
print("abc".isalpha(), "123".isdigit(), "a1".isalnum(), " ".isspace())

# Regular expressions
import re
m = re.search(r"(\d{4})-(\d{2})-(\d{2})", "due 2026-10-13!")
print(m.groups(), m.start())
print(re.findall(r"\b\w{5}\b", "hello there big world"))
print(re.sub(r"\s+", " ", "a   b \t c"))
```

```text output
'Hello, World' hello, world 3
['Hello', 'World'] a-b-c
9 -1 True
HeLLo, World
p n yth nohtyp 6
4 5 b'caf\xc3\xa9'
True
65 ☃ True
False 1 2
True
3.14|    42|42    |  42  |**x**
a b a n=5
   right
1,234,567.9 25.6% 1010
x=7
{'name': 'Ada', 'age': '36', 'city': 'London'} 37
['a', 'b', 'c'] ['a', '', 'b']
['line1', 'line2']
['FIRST', 'SECOND']
C:\new\table 2
01234
True True True True
('2026', '10', '13') 4
['hello', 'there', 'world']
a b c
```

## Details that bite

- `len("café")` counts code points, not bytes or "characters the user sees".
  Normalize (`NFC`) before comparing user text.
- `str.split()` with no argument collapses runs of whitespace; `split(" ")`
  does not.
- `s += x` in a loop is quadratic in the worst case; collect then `"".join`.
- Always pass `encoding="utf-8"` when opening text files; the default is
  platform-dependent.
- `str.strip("abc")` strips a *set of characters*, not a prefix. Use
  `removeprefix` / `removesuffix`.
- Compare with `==`; `is` on strings is an implementation detail.

## Exercises

```python file=exercise.py
def is_palindrome(s):
    """Ignore case and any non-alphanumeric characters."""
    raise NotImplementedError


def caesar(text, shift):
    """Shift ASCII letters by `shift` (may be negative), keeping case;
    leave other characters unchanged."""
    raise NotImplementedError


def title_case(s):
    """Capitalize the first letter of each space-separated word and lowercase
    the rest. Preserve single spaces; collapse nothing."""
    raise NotImplementedError


def parse_kv(line):
    """Parse 'a=1,b=two' into {'a': '1', 'b': 'two'}. Empty string -> {}."""
    raise NotImplementedError


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


results = [
    check("palindrome yes", is_palindrome("A man, a plan, a canal: Panama"), True),
    check("palindrome no", is_palindrome("hello"), False),
    check("caesar +3", caesar("Hello, World!", 3), "Khoor, Zruog!"),
    check("caesar -3", caesar("Khoor, Zruog!", -3), "Hello, World!"),
    check("title", title_case("hELLO wORLD  x"), "Hello World  X"),
    check("kv", parse_kv("a=1,b=two"), {"a": "1", "b": "two"}),
    check("kv empty", parse_kv(""), {}),
]
raise SystemExit(0 if all(results) else 1)
```

<details><summary>Solution</summary>

```python file=solution.py
def is_palindrome(s):
    cleaned = [c.lower() for c in s if c.isalnum()]
    return cleaned == cleaned[::-1]


def caesar(text, shift):
    out = []
    for ch in text:
        if "a" <= ch <= "z":
            out.append(chr((ord(ch) - 97 + shift) % 26 + 97))
        elif "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 + shift) % 26 + 65))
        else:
            out.append(ch)
    return "".join(out)


def title_case(s):
    return " ".join(w[:1].upper() + w[1:].lower() for w in s.split(" "))


def parse_kv(line):
    if not line:
        return {}
    return dict(pair.split("=", 1) for pair in line.split(","))


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


results = [
    check("palindrome yes", is_palindrome("A man, a plan, a canal: Panama"), True),
    check("palindrome no", is_palindrome("hello"), False),
    check("caesar +3", caesar("Hello, World!", 3), "Khoor, Zruog!"),
    check("caesar -3", caesar("Khoor, Zruog!", -3), "Hello, World!"),
    check("title", title_case("hELLO wORLD  x"), "Hello World  X"),
    check("kv", parse_kv("a=1,b=two"), {"a": "1", "b": "two"}),
    check("kv empty", parse_kv(""), {}),
]
raise SystemExit(0 if all(results) else 1)
```

</details>

Next: [06 — Classes](06-classes.md)
