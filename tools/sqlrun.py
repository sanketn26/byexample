#!/usr/bin/env python3
"""Run a .sql file against a throwaway PostgreSQL database.

The database is PostgreSQL 16 in the Docker container ``byexample-pg``
(user and password ``byexample``, published on 127.0.0.1:5432). Each run
creates a fresh database and drops it on exit.

Rows print as ``a|b|c``. NULL is an empty field. Booleans are ``t`` and
``f``, which is what ``psql`` prints. A line ``.headers on`` prints column
names for the statements that follow (``.headers off`` stops that). The
comment ``-- expect-error`` marks the next statement as one that must fail:
the run prints ``Error: ...`` and carries on.

    python3 tools/sqlrun.py n01.sql
"""
import re
import subprocess
import sys
import uuid

CONTAINER = "byexample-pg"
USER = "byexample"


def psql(database, sql, check=True):
    cmd = [
        "docker", "exec", "-i", CONTAINER,
        "psql", "-U", USER, "-d", database,
        "-v", "ON_ERROR_STOP=1",
        "-A", "-F", "|",
        "-P", "footer=off",
        "-P", "tuples_only=on",
        "-c", sql,
    ]
    res = subprocess.run(cmd, text=True, capture_output=True)
    if check and res.returncode != 0:
        sys.stderr.write(res.stderr)
        sys.exit(res.returncode or 1)
    return res


def split_statements(text):
    """Split SQL on semicolons, keeping quotes and dollar quotes intact.

    Also yields ('.headers', 'on'|'off') and ('expect-error',) markers in order.
    """
    items = []
    buf = []
    i = 0
    n = len(text)
    quote = None
    dollar = None
    line_start = True
    while i < n:
        if line_start and quote is None and dollar is None and not "".join(buf).strip():
            rest = text[i:]
            if rest.startswith("-- expect-error") and (len(rest) == 15 or rest[15] in "\r\n"):
                items.append(("expect",))
                i = text.find("\n", i)
                i = n if i < 0 else i + 1
                line_start = True
                continue
            if rest.startswith(".headers"):
                word = rest.split(None, 2)
                if len(word) >= 2 and word[1][:2] in ("on", "of"):
                    items.append(("headers", "on" if word[1].startswith("on") else "off"))
                i = text.find("\n", i)
                i = n if i < 0 else i + 1
                line_start = True
                continue
        ch = text[i]
        if line_start and ch == "\n":
            buf.append(ch)
            i += 1
            continue
        line_start = ch == "\n"
        if dollar is not None:
            if text.startswith(dollar, i):
                buf.append(dollar)
                i += len(dollar)
                dollar = None
                continue
            buf.append(ch)
            i += 1
            continue
        if quote is not None:
            buf.append(ch)
            if ch == quote:
                if i + 1 < n and text[i + 1] == quote:
                    buf.append(text[i + 1])
                    i += 2
                    continue
                quote = None
            i += 1
            continue
        if ch in "'\"":
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "$":
            m = re.match(r"\$[A-Za-z0-9_]*\$", text[i:])
            if m:
                dollar = m.group(0)
                buf.append(dollar)
                i += len(dollar)
                continue
        if ch == "-" and i + 1 < n and text[i + 1] == "-" and quote is None:
            end = text.find("\n", i)
            i = n if end < 0 else end
            continue
        if ch == ";":
            statement = "".join(buf).strip()
            if statement:
                items.append(("sql", statement))
            buf = []
            i += 1
            line_start = True
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        items.append(("sql", tail))
    return items


_TAG = re.compile(
    r"^(INSERT|UPDATE|DELETE|SELECT|CREATE|DROP|ALTER|COMMENT|ANALYZE|VACUUM|"
    r"BEGIN|COMMIT|ROLLBACK|SAVEPOINT|RELEASE|SET|RESET|TRUNCATE|DO|GRANT|"
    r"REVOKE|NOTIFY|LISTEN|UNLISTEN|COPY|START|PREPARE|DEALLOCATE|DISCARD|"
    r"LOCK|CHECKPOINT|REINDEX|CLUSTER|REFRESH|SECURITY|MOVE|FETCH|CLOSE|"
    r"DECLARE|EXPLAIN)( |$)"
)


def _command_tag(line):
    return bool(_TAG.match(line))


def error_line(stderr):
    for line in stderr.splitlines():
        line = line.strip()
        if line.startswith("ERROR:"):
            return "Error: " + line[len("ERROR:"):].strip()
    text = stderr.strip().splitlines()
    return "Error: " + (text[-1].strip() if text else "statement failed")


def format_result(stdout, headers):
    lines = [ln for ln in stdout.splitlines() if ln.strip() != ""]
    # psql unaligned has no separator row when tuples_only is on.
    if not headers or not lines:
        return lines
    # Column names come from a second query path; here stdout is tuples only.
    return lines


def column_names(database, statement):
    wrapped = f"SELECT * FROM ({statement}) AS byexample_headers LIMIT 0"
    res = psql(database, wrapped, check=False)
    if res.returncode != 0:
        return None
    # tuples_only hides names. Ask with tuples_only off and take the first line.
    cmd = [
        "docker", "exec", "-i", CONTAINER,
        "psql", "-U", USER, "-d", database,
        "-v", "ON_ERROR_STOP=1",
        "-A", "-F", "|",
        "-P", "footer=off",
        "-P", "tuples_only=off",
        "-c", wrapped,
    ]
    res = subprocess.run(cmd, text=True, capture_output=True)
    if res.returncode != 0 or not res.stdout.strip():
        return None
    first = res.stdout.splitlines()[0]
    if set(first) <= set("-|+"):
        return None
    return first


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: sqlrun.py file.sql")
    try:
        text = open(sys.argv[1]).read()
    except OSError as e:
        sys.exit(f"Error: {e}")
    name = "byex_" + uuid.uuid4().hex[:12]
    psql("byexample", f'CREATE DATABASE "{name}"')
    try:
        psql(name, "SET client_min_messages TO warning")
        # The setting does not persist across -c connections, so each call
        # passes it in the command string.
        headers = False
        expect = False
        for item in split_statements(text):
            if item[0] == "headers":
                headers = item[1] == "on"
                continue
            if item[0] == "expect":
                expect = True
                continue
            statement = item[1]
            sql = "SET client_min_messages TO warning; " + statement
            res = psql(name, sql, check=False)
            if res.returncode != 0:
                if not expect:
                    print(error_line(res.stderr), file=sys.stderr)
                    sys.exit(1)
                print(error_line(res.stderr))
                expect = False
                continue
            if expect:
                print(f"Error: expected a failure from: {statement[:80]}", file=sys.stderr)
                sys.exit(1)
            expect = False
            body = [ln for ln in res.stdout.splitlines() if ln != "SET"]
            body = [ln for ln in body if ln.strip() != "" and not _command_tag(ln)]
            if not body:
                continue
            if headers and statement.lstrip()[:6].upper() in ("SELECT", "WITH", "TABLE", "VALUES", "EXPLAI"):
                names = column_names(name, statement)
                if names:
                    print(names)
            print("\n".join(body))
    finally:
        psql("byexample", f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


if __name__ == "__main__":
    main()
