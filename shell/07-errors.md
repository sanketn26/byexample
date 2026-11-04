# Shell 07 — Errors and Robust Scripts

By default a shell script keeps going after a failure, treats unset
variables as empty, and reports only a pipeline's last status.
Production scripts opt out of all three, clean up after themselves,
and fail loudly. Print errors to stderr. Leave stdout for data.

## `set -e` exits when a command fails

The flag has holes, below. It is not a substitute for checking the
commands you care about.

```bash file=n01.sh
attempt() { ( "$@" ) 2>&1 || echo "  -> exited with $?"; }
attempt bash -c 'set -e; echo before; false; echo "never printed"'
```

```text output
before
  -> exited with 1
```

## `set -e` is off for the test of an `if`

It is also off for `&&` and `||` lists, for `!`, and for the body of
a function called from any of those. A function that "fails fast"
silently stops doing so when you write `if myfunc; then`.

```bash file=n02.sh
set -e
f() { false; echo "function kept going"; }
if f; then echo "called from if"; fi
false && echo "and-skipped"
echo "script kept going"
```

```text output
function kept going
called from if
script kept going
```

## `set -u` rejects an unset name

A missing `$1` is that error. `${1:-}` allows it. `${1:?message}`
requires it and aborts with your text.

```bash file=n03.sh
attempt() { ( "$@" ) 2>&1 || echo "  -> exited with $?"; }
attempt bash -c 'set -u; echo "value: $undefined_var"'
set -u
echo "empty <${1:-}>"
```

```text output
bash: line 1: undefined_var: unbound variable
  -> exited with 127
empty <>
```

## `pipefail` fails when any stage fails

Without it, `false | cat` succeeds because `cat` succeeded. With
`set -e` and `pipefail`, the script stops.

```bash file=n04.sh
attempt() { ( "$@" ) 2>&1 || echo "  -> exited with $?"; }
attempt bash -c 'set -eo pipefail; false | cat; echo "never printed"'
```

```text output
  -> exited with 1
```

## Three failures `set -e` does not see

`local v=$(failing)` hides the status behind `local`. The left side
of a pipeline is ignored without `pipefail`. `(( expr ))` fails when
the value is 0, including `(( count++ ))` from 0.

```bash file=n05.sh
set -e
hide() { local v=$(false); echo "local hid it"; }
hide
echo "after local"
false | cat
echo "pipeline survived"
bash -c 'set -e; count=0; (( count++ )); echo survived' || echo "arithmetic aborted"
```

```text output
local hid it
after local
pipeline survived
arithmetic aborted
```

## An expected failure is a branch, not a crash

`if`, `|| true`, and a saved status are three ways to keep going on
purpose. `grep` exits 1 when the pattern is absent.

```bash file=n06.sh
set -e
if ! grep -q zebra <<< "apple banana"; then echo "no zebra, carrying on"; fi
grep -q zebra <<< "apple banana" || true
rc=0
grep -q zebra <<< "apple" || rc=$?
echo "grep exit: $rc"
```

```text output
no zebra, carrying on
grep exit: 1
```

## `trap EXIT` is the cleanup hook

It runs on success, on failure, and on Ctrl-C. Always `mktemp`. A
fixed `/tmp/name` is a race and a security hole. `exit` inside
`$(...)` or a pipeline stage exits only that subshell.

```bash file=n07.sh
tmp=$(mktemp -d)
cleanup() { rm -rf "$tmp"; echo "cleaned up"; }
trap cleanup EXIT
echo "work" > "$tmp/data"
[[ -f $tmp/data ]] && echo "temp file exists"
```

```text output
temp file exists
cleaned up
```

## A second EXIT trap replaces the first

Compose one `cleanup` function and trap that. Do not stack traps.
They do not stack.

```bash file=n08.sh
trap 'echo first' EXIT
trap 'echo second' EXIT
```

```text output
second
```

## `exit` in a substitution leaves the parent running

The subshell is the one that exits. With `set -e`, a failing
substitution used only as an argument of `echo` does not abort the
script either. Check the status if you need it.

```bash file=n09.sh
set +e
out=$(echo hi; exit 9)
echo "status $? value $out"
set -e
echo "captured $(echo hi; exit 9)"
echo "parent still here"
```

```text output
status 9 value hi
captured hi
parent still here
```

## `trap ERR` names the failing command

This trap is bash-only. `$LINENO` and `$BASH_COMMAND` are the line
and the text that failed. `set -e` then skips the rest.

```bash file=n10.sh
bash <<'INNER' || true
trap 'echo "failed at line $LINENO: $BASH_COMMAND"' ERR
set -e
ls /nonexistent-dir 2>/dev/null
echo never
INNER
```

```text output
failed at line 3: ls /nonexistent-dir 2> /dev/null
```

## `${1:?msg}` demands an argument

The message goes to stderr. The status is non-zero. In a subshell,
that failure does not kill the caller.

```bash file=n11.sh
name_or_die() { echo "${1:?missing NAME}"; }
( name_or_die ) 2>&1 | sed 's/^.*: //' || true
```

```text output
missing NAME
```

## Validate before you use the value

A pattern for the shape, then a range for the meaning. Print the
problem to stderr and return non-zero. Do not echo a bad value on
stdout, where a pipeline would treat it as data.

```bash file=n12.sh
set -euo pipefail
parse_port() {
  local p=$1
  [[ $p =~ ^[0-9]+$ ]] || { echo "bad port: $p" >&2; return 1; }
  (( p >= 1 && p <= 65535 )) || { echo "port out of range: $p" >&2; return 1; }
  echo "$p"
}
parse_port 8080
parse_port abc 2>&1 || true
parse_port 70000 2>&1 || true
```

```text output
8080
bad port: abc
port out of range: 70000
```

## Retry the command, not the whole script

Sleep between tries in real code. A delay of `0` keeps the demo
instant. The status of the last try is the function's status.

```bash file=n13.sh
set -euo pipefail
retry() {
  local n=$1 delay=$2
  shift 2
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
```

```text output
attempt 1/5 failed
attempt 2/5 failed
succeeded after 3 tries
```

## Exit codes are a small vocabulary

0 is success. 1 is a general error. 2 is misuse. 126 is "found, not
executable". 127 is "not found". 128+N means killed by signal N, so
SIGTERM (15) is 143 and Ctrl-C (SIGINT, 2) is 130.

```bash file=n14.sh
missing-cmd >/dev/null 2>&1
echo "missing $?"
tmp=$(mktemp)
printf 'echo hi\n' > "$tmp"
chmod a-x "$tmp"
"$tmp" >/dev/null 2>&1
echo "not-executable $?"
rm -f "$tmp"
sleep 30 &
child=$!
kill "$child"
wait "$child" 2>/dev/null
echo "signal $?"
```

```text output
missing 127
not-executable 126
signal 143
```

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
