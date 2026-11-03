# Shell 07 — Errors and Robust Scripts

By default a shell script **keeps going after a failure**, uses unset
variables as empty strings, and reports a pipeline's last status only.
Production scripts opt out of all three, clean up after themselves, and
fail loudly.

## Example

```bash file=example.sh
#!/usr/bin/env bash
# The "strict mode" header. Know what each switch does:
#   -e          exit when a command fails (with exceptions, see below)
#   -u          error on use of an unset variable
#   -o pipefail a pipeline fails if ANY stage fails
set -euo pipefail

die() { echo "error: $*" >&2; exit 1; }

# 1. Run a risky part in a subshell so the demo can continue
attempt() { ( "$@" ) 2>&1 || echo "  -> exited with $?"; }

attempt bash -c 'set -e; echo before; false; echo "never printed"'
attempt bash -c 'set -u; echo "value: $undefined_var"'
attempt bash -c 'set -eo pipefail; false | cat; echo "never printed"'

# 2. Handle an expected failure explicitly
if ! grep -q zebra <<< "apple banana"; then echo "no zebra, carrying on"; fi
grep -q zebra <<< "apple banana" || true      # ignore on purpose
rc=0; grep -q zebra <<< "apple" || rc=$?      # capture on purpose
echo "grep exit: $rc"

# 3. trap EXIT runs on success, failure, and Ctrl-C: the place for cleanup
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"; echo "cleaned up"' EXIT
echo "work" > "$tmp/data"
[[ -f $tmp/data ]] && echo "temp file exists"

# 4. trap ERR reports where a failure happened (bash only)
bash <<'INNER' || true
trap 'echo "failed at line $LINENO: $BASH_COMMAND"' ERR
set -e
ls /nonexistent-dir 2>/dev/null
echo never
INNER

# 5. Required arguments and variables
usage() { echo "usage: $0 NAME" >&2; }
name_or_die() { echo "${1:?missing NAME}"; }
( name_or_die ) 2>&1 | sed 's/^.*: //' || true

# 6. Validate input before using it
parse_port() {
  local p=$1
  [[ $p =~ ^[0-9]+$ ]] || { echo "bad port: $p" >&2; return 1; }
  (( p >= 1 && p <= 65535 )) || { echo "port out of range: $p" >&2; return 1; }
  echo "$p"
}
parse_port 8080
parse_port abc 2>&1 || true
parse_port 70000 2>&1 || true

# 7. retry with backoff: a function that takes a command
retry() {
  local n=$1 delay=$2; shift 2
  local i
  for ((i = 1; i <= n; i++)); do
    "$@" && return 0
    echo "attempt $i/$n failed" >&2
    sleep "$delay"
  done
  return 1
}
flaky_count=0
flaky() { (( ++flaky_count >= 3 )); }
retry 5 0 flaky 2>&1 && echo "succeeded after $flaky_count tries"

echo "done"
```

```text output
before
  -> exited with 1
bash: line 1: undefined_var: unbound variable
  -> exited with 127
  -> exited with 1
no zebra, carrying on
grep exit: 1
temp file exists
failed at line 3: ls /nonexistent-dir 2> /dev/null
missing NAME
8080
bad port: abc
port out of range: 70000
attempt 1/5 failed
attempt 2/5 failed
succeeded after 3 tries
done
cleaned up
```

## Details that bite

- `set -e` is **ignored** inside `if` conditions, `&&`/`||` lists, `!`
  negations and any function called from them. A function that "fails
  fast" under `set -e` silently stops doing so when you call it as
  `if myfunc; then`.
- `set -e` does not trigger for `local v=$(failing)`, for the left side of
  a pipeline without `pipefail`, or for `(( expr ))` evaluating to 0.
  Do not lean on it for control flow; check what matters explicitly.
- `set -u` makes `$1` an error when no argument was given. Use `${1:-}`
  (or `${1:?message}` to *require* it).
- `trap ... EXIT` replaces any earlier EXIT trap. Compose: keep one
  `cleanup` function and trap that.
- `exit` inside `$(...)` or a pipeline stage exits only that subshell.
- Exit codes: 0 success, 1 general, 2 misuse, 126 not executable, 127 not
  found, 128+N killed by signal N (130 is Ctrl-C).
- Always `mktemp`, never a fixed `/tmp/name`: it is a race and a
  security hole.
- Print errors to **stderr** and keep stdout for data, so pipelines work.

## Exercises

```bash file=exercise.sh
#!/usr/bin/env bash
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

# Run the command "$@" and echo its exit status; the command may fail but
# the function must not abort a `set -e` script.
status_of() {
  "$@"  # TODO
  echo 0
}

# Make a temp dir, write "x" into $1/file inside it, echo the dir's path,
# and arrange for the dir to be removed when the SCRIPT exits (trap EXIT).
# Return the path through the global variable WORKDIR (not via $(...), which
# would run the trap in a subshell).
make_workdir() {
  WORKDIR=""  # TODO
}

# Echo the number of seconds in "HH:MM:SS". Reject anything else by printing
# "invalid" and returning 1. Hours/minutes/seconds are digits only.
to_seconds() {
  echo 0  # TODO
}

# Run "$@" up to 3 times; succeed as soon as one run succeeds, fail if
# all three fail. No sleeping.
try3() {
  return 1  # TODO
}

check "status ok" "$(status_of true)" "0"
check "status fail" "$(status_of bash -c 'exit 7')" "7"
make_workdir; d=$WORKDIR
check "workdir exists" "$([[ -d $d ]] && echo yes)" "yes"
check "to_seconds" "$(to_seconds 01:02:03)" "3723"
check "to_seconds bad" "$(to_seconds 1:2 2>/dev/null)" "invalid"
n=0; flaky() { (( ++n >= 2 )); }
try3 flaky; check "try3" "$n" "2"
always_bad() { return 1; }
try3 always_bad; check "try3 fail" "$?" "1"
exit $failed
```

<details><summary>Solution</summary>

```bash file=solution.sh
#!/usr/bin/env bash
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

status_of() {
  local rc=0
  "$@" || rc=$?
  echo "$rc"
}

make_workdir() {
  WORKDIR=$(mktemp -d)
  trap 'rm -rf "$WORKDIR"' EXIT
  echo x > "$WORKDIR/file"
}

to_seconds() {
  if [[ $1 =~ ^([0-9]+):([0-9]+):([0-9]+)$ ]]; then
    echo $(( 10#${BASH_REMATCH[1]} * 3600 + 10#${BASH_REMATCH[2]} * 60 + 10#${BASH_REMATCH[3]} ))
  else
    echo invalid
    return 1
  fi
}

try3() {
  local i
  for i in 1 2 3; do
    "$@" && return 0
  done
  return 1
}

check "status ok" "$(status_of true)" "0"
check "status fail" "$(status_of bash -c 'exit 7')" "7"
make_workdir; d=$WORKDIR
check "workdir exists" "$([[ -d $d ]] && echo yes)" "yes"
check "to_seconds" "$(to_seconds 01:02:03)" "3723"
check "to_seconds bad" "$(to_seconds 1:2 2>/dev/null)" "invalid"
n=0; flaky() { (( ++n >= 2 )); }
try3 flaky; check "try3" "$n" "2"
always_bad() { return 1; }
try3 always_bad; check "try3 fail" "$?" "1"
exit $failed
```

</details>

Next: [08 — Processes and jobs](08-processes.md)
