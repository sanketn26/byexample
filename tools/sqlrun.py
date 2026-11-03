#!/usr/bin/env python3
"""Run a .sql file against an in-memory SQLite database.

Behaves like `sqlite3 -bail :memory: < file.sql` in its default list mode:
rows print as `a|b|c`, NULL prints as an empty string, and the first error
stops the run with a non-zero exit status. Lines starting with `.headers on`
turn on a header row for the SELECTs that follow (`.headers off` undoes it).
The comment line `-- expect-error` (a plain comment to the real sqlite3 shell)
marks the next statement as one that must fail: the run prints `Error: ...`
and carries on, and it is itself an error if the statement succeeds.

    python3 tools/sqlrun.py example.sql
"""
import sqlite3
import sys


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        out = f"{v:.15g}"  # what the sqlite3 shell prints
        return out if any(c in out for c in ".eni") else out + ".0"
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return str(v)


def plan(rows):
    """Format EXPLAIN QUERY PLAN rows (id, parent, _, detail) like the sqlite3 shell."""
    kids = {}
    for rid, parent, _, detail in rows:
        kids.setdefault(parent, []).append((rid, detail))
    lines = ["QUERY PLAN"]

    def walk(parent, prefix):
        items = kids.get(parent, [])
        for i, (rid, detail) in enumerate(items):
            last = i == len(items) - 1
            lines.append(f"{prefix}{'`--' if last else '|--'}{detail}")
            walk(rid, prefix + ("   " if last else "|  "))

    walk(0, "")
    return lines


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: sqlrun.py file.sql")
    db = sqlite3.connect(":memory:", isolation_level=None)
    headers = False
    expect_error = False
    buf = ""
    for line in open(sys.argv[1]):
        if not buf.strip() and (not line.strip() or line.lstrip().startswith("--")):
            if line.strip() == "-- expect-error":
                expect_error = True
            continue  # blank lines and comments between statements
        if not buf.strip() and line.startswith("."):
            cmd = line.split()
            if cmd[0] == ".headers":
                headers = cmd[1] == "on"
            continue
        buf += line
        if not sqlite3.complete_statement(buf):
            continue
        try:
            cur = db.execute(buf)
            if buf.lstrip().upper().startswith("EXPLAIN QUERY PLAN"):
                print("\n".join(plan(cur.fetchall())))
            elif cur.description:
                if headers:
                    print("|".join(d[0] for d in cur.description))
                for row in cur:
                    print("|".join(fmt(v) for v in row))
            if expect_error:
                print(f"Error: expected a failure from: {buf.strip()[:80]}", file=sys.stderr)
                sys.exit(1)
        except sqlite3.Error as e:
            if not expect_error:
                print(f"Error: {e} in: {buf.strip()[:80]}", file=sys.stderr)
                sys.exit(1)
            print(f"Error: {e}")
        expect_error = False
        buf = ""
    if buf.strip():
        print("Error: incomplete statement", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
