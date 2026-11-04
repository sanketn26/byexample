# Python 05 — Strings and Text

A `str` is an immutable sequence of Unicode code points. Raw bytes are a
separate type, `bytes`. Keeping those two apart is most of the battle.

## `strip`, `split`, and `join` reshape text

`strip` drops whitespace from both ends. `split` breaks on a separator,
`join` puts one back, and `find` returns `-1` when the text is missing.
`replace` can stop after a count.

```python file=n01.py
s = "  Hello, World  "
print(repr(s.strip()), s.lower().strip(), s.count("l"))
print(s.strip().split(", "), "-".join(["a", "b", "c"]))
print(s.find("World"), s.find("nope"), s.strip().startswith("Hello"))
print(s.replace("l", "L", 2).strip())
```

```text output
'Hello, World' hello, world 3
['Hello', 'World'] a-b-c
9 -1 True
HeLLo, World
```

## `strip` removes a set of characters

`s.strip("abc")` strips each of `a`, `b`, and `c` from the ends. It does
not remove the prefix `"abc"`. Use `removeprefix` and `removesuffix` for
that.

```python file=n02.py
s = "abchelloabc"
print(repr(s.strip("abc")))
print(s.removeprefix("abc"), s.removesuffix("abc"))
```

```text output
'hello'
helloabc abchello
```

## Indexing returns one code point

`s[0]` is the first code point and `s[-1]` is the last. A slice such as
`[::-1]` is a new string. Assigning to an index raises `TypeError`,
because a string is immutable.

```python file=n03.py
w = "python"
print(w[0], w[-1], w[1:4], w[::-1], len(w))
try:
    w[0] = "x"
except TypeError as e:
    print(type(e).__name__)
```

```text output
p n yth nohtyp 6
TypeError
```

## `len` counts code points, not bytes

`"café"` is 4 code points and 5 UTF-8 bytes. `encode` and `decode` cross
that boundary. Pass `encoding="utf-8"` when you open a text file; the
default depends on the platform.

```python file=n04.py
t = "café"
print(len(t), len(t.encode("utf-8")), t.encode("utf-8"))
print(b"caf\xc3\xa9".decode("utf-8") == t)
print(ord("A"), chr(9731), "\u00e9" == "é")
```

```text output
4 5 b'caf\xc3\xa9'
True
65 ☃ True
```

## A visible character can be two code points

`\u00e9` is one precomposed `é`. `e` plus a combining acute is two code
points, and the two are not equal. Normalize to NFC before comparing
text a user typed.

```python file=n05.py
import unicodedata

e1 = "\u00e9"
e2 = "e\u0301"
print(e1 == e2, len(e1), len(e2))
print(unicodedata.normalize("NFC", e2) == e1)
```

```text output
False 1 2
True
```

## The format spec does the padding

The mini-language after `:` sets precision, width, and alignment.
`f"{x=}"` prints the source and the value. `.format` and `%` still work.
A width can be a name, not only a literal.

```python file=n06.py
print(f"{3.14159:.2f}|{42:>6}|{42:<6}|{42:^6}|{'x':*^5}")
print("{0} {1} {0}".format("a", "b"), "%s=%d" % ("n", 5))
width = 8
print(f"{'right':>{width}}")
print(f"{1234567.891:,.1f}", f"{0.256:.1%}", f"{10:b}")
x = 7
print(f"{x=}")
```

```text output
3.14|    42|42    |  42  |**x**
a b a n=5
   right
1,234,567.9 25.6% 1010
x=7
```

## `split()` and `split(" ")` disagree

With no argument, `split` collapses runs of whitespace. `split(" ")`
keeps the empty pieces between repeated spaces. `splitlines` drops the
line endings.

```python file=n07.py
line = "name=Ada;age=36;city=London"
record = dict(pair.split("=") for pair in line.split(";"))
print(record, int(record["age"]) + 1)
print("a  b   c".split(), "a  b".split(" "))
print("line1\nline2\n".splitlines())
```

```text output
{'name': 'Ada', 'age': '36', 'city': 'London'} 37
['a', 'b', 'c'] ['a', '', 'b']
['line1', 'line2']
```

## Triple quotes keep newlines, raw strings keep backslashes

A triple-quoted string includes the line break. An `r"..."` string does
not treat `\n` as a newline, so its length counts the two characters.

```python file=n08.py
doc = """first
second"""
print(doc.upper().split("\n"))
print(r"C:\new\table", len(r"\n"))
```

```text output
['FIRST', 'SECOND']
C:\new\table 2
```

## Build a long string with `join`

`s += part` copies the whole string on every addition, which is quadratic.
Collect the parts and join them once.

```python file=n09.py
parts = [str(i) for i in range(5)]
print("".join(parts))
```

```text output
01234
```

## Predicates look at every character

`isalpha`, `isdigit`, `isalnum`, and `isspace` are true only when the
whole string matches.

```python file=n10.py
print("abc".isalpha(), "123".isdigit(), "a1".isalnum(), " ".isspace())
```

```text output
True True True True
```

## A pattern can search, find, and replace

`search` returns the first match. Parentheses become groups. `findall`
returns every non-overlapping match, and `sub` replaces what the pattern
matches.

```python file=n11.py
import re

m = re.search(r"(\d{4})-(\d{2})-(\d{2})", "due 2026-10-13!")
print(m.groups(), m.start())
print(re.findall(r"\b\w{5}\b", "hello there big world"))
print(re.sub(r"\s+", " ", "a   b \t c"))
```

```text output
('2026', '10', '13') 4
['hello', 'there', 'world']
a b c
```

## Compare strings with `==`

`is` can be true for two names bound to the same interned literal, and
false for an equal string you built. It is not a comparison.

```python file=n12.py
left = "hello"
right = "".join(["he", "llo"])
also = "hello"
print(left == right, left is right, left is also)
```

```text output
True False True
```

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
