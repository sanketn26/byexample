# Shell 06 — Redirection and Pipes

Every process starts with three file descriptors: `0` stdin, `1`
stdout, `2` stderr. Redirection rewires them before the command runs.
A pipe connects one command's stdout to the next command's stdin.

## `>` truncates, `>>` appends, `<` reads

`cat file | cmd` is usually an extra process. `cmd < file` does the
same read and leaves `$?` as that command's status.

```bash file=n01.sh
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
echo "one" > log.txt
echo "two" >> log.txt
echo "$(( $(wc -l < log.txt) ))"
```

```text output
2
```

## Stdout and stderr are different streams

`2>/dev/null` drops stderr. `>/dev/null` drops stdout. `>file 2>&1`
sends both to the file. `&>file` is bash shorthand for that form, and
it is not POSIX.

```bash file=n02.sh
noisy() { echo "to-out"; echo "to-err" >&2; }
noisy 2>/dev/null
noisy >/dev/null
tmp=$(mktemp -d)
noisy >"$tmp/both.txt" 2>&1
sort "$tmp/both.txt"
```

```text output
to-out
to-err
to-err
to-out
```

## Redirections apply left to right

`cmd >file 2>&1` points stderr at the file. `cmd 2>&1 >file` points
stderr at the old stdout, the terminal, and only then moves stdout
to the file.

```bash file=n03.sh
noisy() { echo "to-out"; echo "to-err" >&2; }
noisy 2>&1 >/dev/null
```

```text output
to-err
```

## Swap the streams to capture stderr

Point stderr at the current stdout, then point stdout at `/dev/null`.
The substitution receives what used to be stderr.

```bash file=n04.sh
noisy() { echo "to-out"; echo "to-err" >&2; }
errs=$(noisy 2>&1 >/dev/null)
echo "captured: $errs"
```

```text output
captured: to-err
```

## A pipe feeds stdout to the next stdin

Prefer `printf` for data in a pipe. `echo` mangles `-n`, `-e`, and
backslashes in some shells.

```bash file=n05.sh
printf 'b\na\nc\na\n' | sort | uniq -c | sort -rn | head -2
```

```text output
   2 a
   1 c
```

## Here-docs and here-strings are stdin

`<<<` sends one string. `<<EOF` sends the following lines, up to a
line that is only the delimiter. The delimiter in the script below is
unquoted, but the body has nothing to expand.

```bash file=n06.sh
tr a-z A-Z <<< "shout"
words=$(cat <<EOF | wc -w
one two
three
EOF
)
echo "$((words))"
```

```text output
SHOUT
3
```

## `tee` saves a copy and passes the stream on

The file gets the same bytes the next command sees.

```bash file=n07.sh
tmp=$(mktemp -d)
cd "$tmp"
echo "payload" | tee copy.txt | tr a-z A-Z
cat copy.txt
```

```text output
PAYLOAD
payload
```

## Process substitution is a command with a file name

`<(...)` expands to a path the program can read. `diff` wants two
files, not two pipes, so this is how both sides stay commands.

```bash file=n08.sh
diff <(echo a; echo b) <(echo a; echo c) | head -3
```

```text output
2c2
< b
---
```

## Without `pipefail`, only the last status counts

`bad | tee log` looks successful because `tee` succeeded. `set -o
pipefail` fails the pipeline if any stage fails. `PIPESTATUS` holds
every stage's status from the pipeline just above it.

```bash file=n09.sh
false | true
echo "no pipefail: $?"
set -o pipefail
false | true
echo "pipefail:    $?"
set +o pipefail
false | true | false | true
echo "PIPESTATUS: ${PIPESTATUS[*]}"
```

```text output
no pipefail: 0
pipefail:    1
PIPESTATUS: 1 0 1 0
```

## A pipeline stage is a subshell

The stages run at the same time. `echo hi | read x` leaves `x` unset
in the current shell, because `read` assigned it in the other one.
Lesson 08 shows how to keep the variable.

```bash file=n10.sh
x=unset
echo hi | read -r x
echo "after pipe: $x"
```

```text output
after pipe: unset
```

## Extra descriptors leave stdin free

`exec 3>file` opens descriptor 3 for the rest of the script. `>&3`
writes there. `exec 3>&-` closes it. `read -u 4` reads that
descriptor and does not touch stdin.

```bash file=n11.sh
tmp=$(mktemp -d)
cd "$tmp"
exec 3> fd3.txt
echo "via fd 3" >&3
exec 3>&-
cat fd3.txt
printf 'x\ny\n' > in.txt
exec 4< in.txt
while IFS= read -r -u 4 l; do echo "got $l"; done
exec 4<&-
```

```text output
via fd 3
got x
got y
```

## `noclobber` refuses to truncate

`set -o noclobber` makes `>` fail when the file exists. `>|` forces
the truncation.

```bash file=n12.sh
tmp=$(mktemp -d)
cd "$tmp"
echo old > log.txt
set -o noclobber
( echo new > log.txt ) 2>/dev/null || echo "noclobber blocked >"
echo forced >| log.txt
cat log.txt
```

```text output
noclobber blocked >
forced
```

## `>` creates the file before the command runs

The file appears even when the command is not found or fails later.
Check the status. Do not treat an empty file as proof the command
worked.

```bash file=n13.sh
tmp=$(mktemp -d)
cd "$tmp"
missing-cmd > created.txt 2>/dev/null || true
[[ -f created.txt ]] && echo "created"
```

```text output
created
```

## Redirecting a file onto itself truncates it first

`sort f > f` empties `f` before `sort` reads it. Write to a temp file
and `mv`, or use `sponge` / `sed -i`.

```bash file=n14.sh
tmp=$(mktemp -d)
cd "$tmp"
printf 'b\na\n' > f
sort f > f
echo "left [$(cat f)]"
```

```text output
left []
```

## A here-string sends a variable, not a temp file

`<<< "$data"` is stdin for one command. No file is left behind.

```bash file=n15.sh
data=$'line1\nline2'
grep -c line <<< "$data"
```

```text output
2
```

## Exercises

```bash file=exercise.sh
#!/usr/bin/env bash
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT

noisy() { echo out; echo err >&2; }

# Run noisy, echo ONLY what it wrote to stderr.
only_stderr() {
  noisy  # TODO
}

# Run noisy, send BOTH streams to the file $1.
both_to() {
  noisy  # TODO
}

# Echo the 3 most common lines of stdin as "COUNT LINE" (count, one space,
# line), most common first.
top3() {
  cat  # TODO (sort | uniq -c | sort -rn | head)
}

# Echo "ok" if the pipeline `false | true` is reported as FAILING.
detects_pipe_failure() {
  echo ""  # TODO (pipefail, inside a subshell so it does not leak)
}

# Append stdin to file $1 and also pass it through to stdout.
keep() {
  cat  # TODO
}

check "only_stderr" "$(only_stderr)" "err"
both_to "$tmp/b.txt"; check "both_to" "$(sort "$tmp/b.txt" | tr '\n' ' ')" "err out "
check "top3" "$(printf 'x\ny\nx\nz\nx\ny\n' | top3 | sed 's/^ *//')" "$(printf '3 x\n2 y\n1 z')"
check "pipe failure" "$(detects_pipe_failure)" "ok"
check "keep out" "$(echo hi | keep "$tmp/k.txt")" "hi"
check "keep file" "$(cat "$tmp/k.txt")" "hi"
exit $failed
```

<details><summary>Solution</summary>

```bash file=solution.sh
#!/usr/bin/env bash
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT

noisy() { echo out; echo err >&2; }

only_stderr() {
  noisy 2>&1 >/dev/null
}

both_to() {
  noisy >"$1" 2>&1
}

top3() {
  sort | uniq -c | sort -rn | head -3
}

detects_pipe_failure() {
  (
    set -o pipefail
    if false | true; then echo "missed"; else echo ok; fi
  )
}

keep() {
  tee -a "$1"
}

check "only_stderr" "$(only_stderr)" "err"
both_to "$tmp/b.txt"; check "both_to" "$(sort "$tmp/b.txt" | tr '\n' ' ')" "err out "
check "top3" "$(printf 'x\ny\nx\nz\nx\ny\n' | top3 | sed 's/^ *//')" "$(printf '3 x\n2 y\n1 z')"
check "pipe failure" "$(detects_pipe_failure)" "ok"
check "keep out" "$(echo hi | keep "$tmp/k.txt")" "hi"
check "keep file" "$(cat "$tmp/k.txt")" "hi"
exit $failed
```

</details>

Next: [07 — Errors and robust scripts](07-errors.md)
