# Python 10 — Files, I/O and the Standard Library

Read and write files with `pathlib` and context managers; use the standard
library for JSON, CSV, and processes.

## Example

```python file=example.py
import csv
import io
import json
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)

    # Writing and reading text (always say the encoding)
    p = root / "notes.txt"
    p.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    print(p.read_text(encoding="utf-8").splitlines())
    print(p.name, p.suffix, p.stem, p.parent == root, p.exists())

    # Streaming a large file line by line
    with open(p, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            print(lineno, line.rstrip("\n"))

    # Appending
    with open(p, "a", encoding="utf-8") as f:
        f.write("delta\n")
    print(len(p.read_text().splitlines()))

    # Binary files
    b = root / "data.bin"
    b.write_bytes(bytes([0, 1, 2, 255]))
    print(list(b.read_bytes()), b.stat().st_size)

    # JSON round-trip
    cfg = {"name": "app", "ports": [80, 443], "debug": False, "extra": None}
    j = root / "cfg.json"
    j.write_text(json.dumps(cfg, indent=2, sort_keys=True))
    print(json.loads(j.read_text()) == cfg)
    print(json.dumps({"b": 1, "a": [1, 2]}, sort_keys=True, separators=(",", ":")))

    # CSV with DictReader / DictWriter
    c = root / "people.csv"
    with open(c, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "age"])
        w.writeheader()
        w.writerow({"name": "Ada", "age": 36})
        w.writerow({"name": "Linus, T.", "age": 55})   # comma gets quoted
    print(c.read_text().splitlines()[2])
    with open(c, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(rows[1]["name"], sum(int(r["age"]) for r in rows))

    # Directory walking
    (root / "sub").mkdir()
    (root / "sub" / "x.py").write_text("print('x')")
    print(sorted(str(q.relative_to(root)) for q in root.rglob("*") if q.is_file()))
    print(sorted(q.name for q in root.glob("*.json")))

# In-memory files behave the same
buf = io.StringIO()
print("hello", file=buf)
print(repr(buf.getvalue()))

# Handling missing files
try:
    Path("/no/such/file").read_text()
except FileNotFoundError as e:
    print(type(e).__name__)

# Running a subprocess
import subprocess, sys
r = subprocess.run([sys.executable, "-c", "print(6 * 7)"],
                   capture_output=True, text=True, check=True)
print(r.stdout.strip(), r.returncode)

# Environment and arguments
import os
print(os.environ.get("DEFINITELY_NOT_SET", "default"))

# Standard streams
print("to stderr", file=sys.stderr)
```

```text output
['alpha', 'beta', 'gamma']
notes.txt .txt notes True True
1 alpha
2 beta
3 gamma
4
[0, 1, 2, 255] 4
True
{"a":[1,2],"b":1}
"Linus, T.",55
Linus, T. 91
['cfg.json', 'data.bin', 'notes.txt', 'people.csv', 'sub/x.py']
['cfg.json']
'hello\n'
FileNotFoundError
42 0
default
```

## Details that bite

- Open CSV files with `newline=""`, or you get blank rows on Windows.
- `open(p, "w")` truncates immediately — write to a temp file and
  `os.replace` for atomic updates.
- `read()` loads everything into memory; iterate the file for large inputs.
- `json` cannot encode `datetime`, `set`, `bytes`; pass `default=` or
  convert first. Dict keys become strings.
- `subprocess.run(cmd, shell=True)` with user input is a command-injection
  hole; pass a list instead.
- Use `pathlib` `/` to join paths; never concatenate with `+ "/" +`.

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
