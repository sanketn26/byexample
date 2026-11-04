# Python 10 — Files, I/O and the Standard Library

Read and write files with `pathlib` and context managers. Use the standard
library for JSON, CSV, and processes.

## Say the encoding when you touch text

`write_text` and `read_text` take `encoding`. `name`, `suffix`, and `stem`
are the pieces of the path. Join pieces with `/`, not with `+ "/" +`.

```python file=n01.py
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    p = root / "notes.txt"
    p.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    print(p.read_text(encoding="utf-8").splitlines())
    print(p.name, p.suffix, p.stem, p.parent == root, p.exists())
```

```text output
['alpha', 'beta', 'gamma']
notes.txt .txt notes True True
```

## Iterate a file instead of reading it all

`read` loads the whole file. A `for` loop over the file yields one line.
Mode `"a"` appends. `"w"` truncates immediately, so a crash mid-write
leaves an empty or partial file.

```python file=n02.py
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp) / "notes.txt"
    p.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    with open(p, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            print(lineno, line.rstrip("\n"))
    with open(p, "a", encoding="utf-8") as f:
        f.write("delta\n")
    print(len(p.read_text(encoding="utf-8").splitlines()))
```

```text output
1 alpha
2 beta
3 gamma
4
```

## Replace a finished temp file

Write the new bytes to a temp file in the same directory, then
`os.replace` it over the destination. A crash leaves the old file or the
new one, not a half-written destination.

```python file=n03.py
import os
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "notes.txt"
    path.write_text("old\n", encoding="utf-8")
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text("new\n", encoding="utf-8")
    os.replace(tmp_path, path)
    print(path.read_text(encoding="utf-8").rstrip(), tmp_path.exists())
```

```text output
new False
```

## Bytes skip decoding

`write_bytes` and `read_bytes` do not use an encoding. `stat().st_size`
is the length on disk.

```python file=n04.py
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    b = Path(tmp) / "data.bin"
    b.write_bytes(bytes([0, 1, 2, 255]))
    print(list(b.read_bytes()), b.stat().st_size)
```

```text output
[0, 1, 2, 255] 4
```

## JSON is a text format with a small set of types

`dumps` and `loads` round-trip lists, dicts, strings, numbers, booleans,
and `None`. Dict keys become strings. `set`, `datetime`, and `bytes` need
a conversion or a `default=` hook. `sort_keys` makes the text stable.

```python file=n05.py
import json
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    cfg = {"name": "app", "ports": [80, 443], "debug": False, "extra": None}
    j = Path(tmp) / "cfg.json"
    j.write_text(json.dumps(cfg, indent=2, sort_keys=True), encoding="utf-8")
    print(json.loads(j.read_text(encoding="utf-8")) == cfg)
print(json.dumps({"b": 1, "a": [1, 2]}, sort_keys=True, separators=(",", ":")))
print(json.loads(json.dumps({1: "a"})))
try:
    json.dumps({1, 2})
except TypeError as e:
    print(type(e).__name__)
```

```text output
True
{"a":[1,2],"b":1}
{'1': 'a'}
TypeError
```

## Open CSV with `newline=""`

`DictWriter` quotes a field that contains a comma. `newline=""` stops
Windows from inserting a blank row between records. `DictReader` uses
the header row as the keys.

```python file=n06.py
import csv
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / "people.csv"
    with open(c, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "age"])
        w.writeheader()
        w.writerow({"name": "Ada", "age": 36})
        w.writerow({"name": "Linus, T.", "age": 55})
    print(c.read_text(encoding="utf-8").splitlines()[2])
    with open(c, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(rows[1]["name"], sum(int(r["age"]) for r in rows))
```

```text output
"Linus, T.",55
Linus, T. 91
```

## `rglob` walks, `glob` does not

`rglob("*")` visits the whole tree. `glob("*.json")` stays in that
directory. `relative_to` drops the temporary prefix.

```python file=n07.py
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "notes.txt").write_text("n", encoding="utf-8")
    (root / "cfg.json").write_text("{}", encoding="utf-8")
    (root / "sub").mkdir()
    (root / "sub" / "x.py").write_text("print('x')", encoding="utf-8")
    (root / "data.bin").write_bytes(b"\x00")
    (root / "people.csv").write_text("h\n", encoding="utf-8")
    print(sorted(str(q.relative_to(root)) for q in root.rglob("*") if q.is_file()))
    print(sorted(q.name for q in root.glob("*.json")))
```

```text output
['cfg.json', 'data.bin', 'notes.txt', 'people.csv', 'sub/x.py']
['cfg.json']
```

## An in-memory file is still a file

`io.StringIO` accepts `print(..., file=buf)`. The same code can target a
real file or a buffer.

```python file=n08.py
import io

buf = io.StringIO()
print("hello", file=buf)
print(repr(buf.getvalue()))
```

```text output
'hello\n'
```

## A missing path raises `FileNotFoundError`

`read_text` on a path that is not there fails with that type. There is
nothing to open.

```python file=n09.py
from pathlib import Path

try:
    Path("/no/such/file").read_text()
except FileNotFoundError as e:
    print(type(e).__name__)
```

```text output
FileNotFoundError
```

## Pass `subprocess` a list of arguments

`shell=True` with text from a user is a command-injection hole. A list
does not go through the shell. `check=True` raises when the exit code is
not zero.

```python file=n10.py
import subprocess
import sys

r = subprocess.run(
    [sys.executable, "-c", "print(6 * 7)"],
    capture_output=True,
    text=True,
    check=True,
)
print(r.stdout.strip(), r.returncode)
```

```text output
42 0
```

## A missing environment variable can have a default

`os.environ.get` returns the second argument when the name is unset.

```python file=n11.py
import os

print(os.environ.get("DEFINITELY_NOT_SET", "default"))
```

```text output
default
```

## stdout and stderr are different streams

`print` writes to stdout. `file=sys.stderr` does not show up there. This
program captures each stream so both lines are visible.

```python file=n12.py
import io
import sys

out, err = io.StringIO(), io.StringIO()
print("to stdout", file=out)
print("to stderr", file=err)
print(out.getvalue().rstrip())
print(err.getvalue().rstrip())
print("real stdout", file=sys.stdout)
```

```text output
to stdout
to stderr
real stdout
```

## Exercises

```python file=exercise.py
from pathlib import Path


def count_lines(path):
    """Number of lines in a text file (0 for an empty file)."""
    raise NotImplementedError


def grep(path, needle):
    """Return [(lineno, line)] for lines containing needle, lineno from 1,
    line without trailing newline."""
    raise NotImplementedError


def csv_column_sum(path, column):
    """Sum an integer column of a CSV file with a header row."""
    raise NotImplementedError


def save_json_atomic(path, obj):
    """Write obj as JSON to path atomically: write path.tmp then rename.
    The .tmp file must not exist afterwards."""
    raise NotImplementedError


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


def run():
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        (t / "a.txt").write_text("one\ntwo\nthree two\n")
        (t / "empty.txt").write_text("")
        (t / "n.csv").write_text("id,qty\n1,5\n2,7\n3,10\n")
        target = t / "o.json"
        save_json_atomic(target, {"k": [1, 2]})
        return [
            check("count_lines", count_lines(t / "a.txt"), 3),
            check("count_lines empty", count_lines(t / "empty.txt"), 0),
            check("grep", grep(t / "a.txt", "two"), [(2, "two"), (3, "three two")]),
            check("csv sum", csv_column_sum(t / "n.csv", "qty"), 22),
            check("atomic", (json.loads(target.read_text()), (t / "o.json.tmp").exists()),
                  ({"k": [1, 2]}, False)),
        ]


raise SystemExit(0 if all(run()) else 1)
```

<details><summary>Solution</summary>

```python file=solution.py
import csv
import json
import os
from pathlib import Path


def count_lines(path):
    with open(path, encoding="utf-8") as f:
        return sum(1 for _ in f)


def grep(path, needle):
    with open(path, encoding="utf-8") as f:
        return [(i, line.rstrip("\n")) for i, line in enumerate(f, 1) if needle in line]


def csv_column_sum(path, column):
    with open(path, newline="", encoding="utf-8") as f:
        return sum(int(row[column]) for row in csv.DictReader(f))


def save_json_atomic(path, obj):
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj), encoding="utf-8")
    os.replace(tmp, path)


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


def run():
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        (t / "a.txt").write_text("one\ntwo\nthree two\n")
        (t / "empty.txt").write_text("")
        (t / "n.csv").write_text("id,qty\n1,5\n2,7\n3,10\n")
        target = t / "o.json"
        save_json_atomic(target, {"k": [1, 2]})
        return [
            check("count_lines", count_lines(t / "a.txt"), 3),
            check("count_lines empty", count_lines(t / "empty.txt"), 0),
            check("grep", grep(t / "a.txt", "two"), [(2, "two"), (3, "three two")]),
            check("csv sum", csv_column_sum(t / "n.csv", "qty"), 22),
            check("atomic", (json.loads(target.read_text()), (t / "o.json.tmp").exists()),
                  ({"k": [1, 2]}, False)),
        ]


raise SystemExit(0 if all(run()) else 1)
```

</details>

Next: [11 — The Pythonic way](11-pythonic.md)
