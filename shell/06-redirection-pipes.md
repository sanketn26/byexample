# Shell 06 — Redirection and Pipes

Every process starts with three **file descriptors**: `0` stdin, `1` stdout,
`2` stderr. Redirection rewires them *before* the command runs; pipes
connect one command's stdout to the next one's stdin. This is the heart of
the Unix philosophy: small tools, one text stream.

## Example

```bash file=example.sh
#!/usr/bin/env bash
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"

# > truncates, >> appends, < reads
echo "one" > log.txt
echo "two" >> log.txt
wc -l < log.txt

# stdout and stderr are separate streams
noisy() { echo "to-out"; echo "to-err" >&2; }
noisy 2>/dev/null                  # discard stderr
noisy >/dev/null                   # discard stdout (stderr still shows)
noisy >both.txt 2>&1               # both into a file
sort both.txt

# ORDER MATTERS: redirections apply left to right
noisy 2>&1 >/dev/null              # stderr -> where stdout WAS (the terminal)

# Capture only stderr of a command
errs=$(noisy 2>&1 >/dev/null)
echo "captured: $errs"

# Pipes
printf 'b\na\nc\na\n' | sort | uniq -c | sort -rn | head -2

# Here-doc and here-string feed stdin
tr a-z A-Z <<< "shout"
cat <<EOF | wc -w
one two
three
EOF

# tee splits a stream: save it AND keep passing it on
echo "payload" | tee copy.txt | tr a-z A-Z
cat copy.txt

# Process substitution: a command's output as a "file"
diff <(echo a; echo b) <(echo a; echo c) | head -3

# Exit statuses in a pipeline: only the last, unless pipefail
false | true;  echo "no pipefail: $?"
set -o pipefail
false | true;  echo "pipefail:    $?"
set +o pipefail
false | true | false | true; echo "PIPESTATUS: ${PIPESTATUS[*]}"

# Custom file descriptors
exec 3> fd3.txt                    # open fd 3 for writing
echo "via fd 3" >&3
exec 3>&-                          # close it
cat fd3.txt

# Reading a file line by line with fd 4, keeping stdin free
printf 'x\ny\n' > in.txt
exec 4< in.txt
while IFS= read -r -u 4 l; do echo "got $l"; done
exec 4<&-

# noclobber refuses to overwrite with >; >| forces it
set -o noclobber
( echo new > log.txt ) 2>/dev/null || echo "noclobber blocked >"
echo forced >| log.txt
set +o noclobber
cat log.txt

# Sending the same text to a command's stdin from a variable, no temp file
data=$'line1\nline2'
grep -c line <<< "$data"
```

```text output
2
to-out
to-err
to-err
to-out
to-err
captured: to-err
      2 a
      1 c
SHOUT
3
PAYLOAD
payload
2c2
< b
---
no pipefail: 0
pipefail:    1
PIPESTATUS: 1 0 1 0
via fd 3
got x
got y
noclobber blocked >
forced
2
```

## Details that bite

- `cmd > file 2>&1` sends both to the file. `cmd 2>&1 > file` does not:
  stderr was pointed at the *old* stdout (the terminal) first.
- `cmd &> file` is bash shorthand for the first form. Not POSIX.
- `cat file | cmd` is usually unnecessary: `cmd < file` saves a process
  (and keeps `$?` meaningful).
- Redirecting a file onto itself (`sort f > f`, `sed ... f > f`)
  truncates the input before it is read. Write to a temp file and `mv`,
  or use `sponge` / `sed -i`.
- Without `pipefail`, `bad_command | tee log` reports success because
  `tee` succeeded.
- A pipeline's stages run **concurrently**, each in its own subshell, which
  is why `echo hi | read x` leaves `x` unset (lesson 08).
- `>` creates the file even if the command then fails or is not found.
- Prefer `printf` over `echo` for piping data: `echo` mangles `-n`, `-e`
  and backslashes in some shells.

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
