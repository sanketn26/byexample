# Shell 02 — Control Flow

Shell branches on exit status, not on booleans. `if` runs a command.
Status `0` means true. `[[ ... ]]` and `(( ... ))` are commands that
return 0 or 1.

## `if` runs a command

There is no boolean type. The branch is taken when the command exits 0.

```bash file=n01.sh
if grep -q "needle" <<< "hay needle hay"; then echo "found"; fi
```

```text output
found
```

## `[` splits words; `[[ ]]` does not

`[` is a real command, so it needs spaces and a closing `]`. An empty
or spaced value is a syntax error. Prefer `[[ ]]` in bash.

```bash file=n02.sh
x=""
[ $x = y ] || true
x="a b"
[[ $x == "a b" ]] && echo "[[ ]] kept the spaces"
```

```text output
n02.sh: line 2: [: =: unary operator expected
[[ ]] kept the spaces
```

## `[[ ]]` tests strings, files, and patterns

An unquoted right-hand side of `==` is a glob. Quote it (`"$pat"`) to
compare literally. `=~` is a regex, and the capture lands in
`BASH_REMATCH`. Keep a regex that contains spaces in a variable.

```bash file=n03.sh
f="report.txt"
[[ $f == *.txt ]] && echo "glob match"
pat="*.txt"
[[ $f == $pat ]] && echo "unquoted pat globs"
[[ $f == "$pat" ]] || echo "quoted pat is literal"
re='^([a-z]+)\.txt$'
[[ $f =~ $re ]] && echo "regex group: ${BASH_REMATCH[1]}"
[[ -z "" ]] && echo "empty string"
[[ -d /tmp ]] && echo "/tmp is a directory"
[[ -e /definitely/not/here ]] || echo "missing"
```

```text output
glob match
unquoted pat globs
quoted pat is literal
regex group: report
empty string
/tmp is a directory
missing
```

## `(( ))` is true when the value is non-zero

The test is arithmetic. A remainder of 1 is true, so odd numbers pass.

```bash file=n04.sh
n=7
if (( n % 2 )); then echo "$n is odd"; fi
```

```text output
7 is odd
```

## `(( count++ ))` fails when the old value is 0

The status is the value before the increment. Under `set -e` that exits
the script. `(( ++count ))` or `count=$((count + 1))` stays safe.

```bash file=n05.sh
bash -c 'set -e; count=0; (( count++ )); echo survived' || echo "post-increment aborted"
bash -c 'set -e; count=0; (( ++count )); echo "pre-increment survived"'
```

```text output
post-increment aborted
pre-increment survived
```

## `a && b || c` is not if/then/else

`&&` and `||` chain on status, and the last status wins. If `b` fails,
`c` runs too. Use a real `if` when the middle command can fail.

```bash file=n06.sh
true && echo "and-then" || echo "never"
false || echo "or-else"
echo middle && false || echo "also ran"
```

```text output
and-then
or-else
middle
also ran
```

## `for` walks words, ranges, and arithmetic

Brace expansion (`{1..5}`) happens before the loop. The C-style form
is arithmetic, like `(( ))`.

```bash file=n07.sh
for color in red green blue; do printf '%s ' "$color"; done
echo
for i in {1..5}; do printf '%d ' "$i"; done
echo
for ((i = 10; i > 0; i -= 4)); do printf '%d ' "$i"; done
echo
```

```text output
red green blue 
1 2 3 4 5 
10 6 2 
```

## An unmatched glob is left as text

`for f in *.txt` runs once with the literal `*.txt` when nothing
matches. `shopt -s nullglob` makes it run zero times. `for f in $(ls)`
splits on spaces. Use the glob.

```bash file=n08.sh
tmp=$(mktemp -d)
cd "$tmp"
touch "my notes.txt"
for f in *.txt; do printf 'match <%s>\n' "$f"; done
for f in *.md; do printf 'miss <%s>\n' "$f"; done
shopt -s nullglob
for f in *.md; do printf 'null <%s>\n' "$f"; done
echo "nullglob done"
for f in $(ls); do printf 'ls <%s>\n' "$f"; done
```

```text output
match <my notes.txt>
miss <*.md>
nullglob done
ls <my>
ls <notes.txt>
```

## `while IFS= read -r` keeps the line

`-r` keeps backslashes. An empty `IFS` keeps leading spaces. The
here-doc is quoted (`<<'EOF'`) so the body is not expanded.

```bash file=n09.sh
while IFS= read -r line; do echo "[$line]"; done <<'EOF_DATA'
  indented
two words
EOF_DATA
```

```text output
[  indented]
[two words]
```

## A pipe runs `while read` in a subshell

Variables set in that loop disappear. Feed the loop with `< file` or
`<<< "$var"` instead. Lesson 08 shows the same rule for pipelines.

```bash file=n10.sh
n=0
printf 'a\nb\n' | while read -r _; do n=$((n + 1)); done
echo "pipe n=$n"
n=0
while read -r _; do n=$((n + 1)); done <<'EOF'
a
b
EOF
echo "redirect n=$n"
```

```text output
pipe n=0
redirect n=2
```

## `case` matches glob patterns

`;;` ends a branch. The first match wins. `*` is the default.

```bash file=n11.sh
kind() {
  case "$1" in
    *.tar.gz|*.tgz) echo "tarball" ;;
    *.md)           echo "markdown" ;;
    [0-9]*)         echo "starts with digit" ;;
    *)              echo "unknown" ;;
  esac
}
kind a.tgz
kind notes.md
kind 7up
kind zzz
```

```text output
tarball
markdown
starts with digit
unknown
```

## `until` stops when the test succeeds

`continue` skips the rest of the body. `break` leaves the loop. Use
`(( ++count ))` so a zero start does not look like a failure.

```bash file=n12.sh
count=0
until (( count >= 3 )); do
  (( ++count ))
  (( count == 2 )) && continue
  echo "count=$count"
done
```

```text output
count=1
count=3
```

## `(( ))` assigns as well as tests

The same arithmetic context that `if` tests can update a variable.

```bash file=n13.sh
total=0
for n in 1 2 3 4; do (( total += n )); done
echo "total=$total"
```

```text output
total=10
```

## Exercises

```bash file=exercise.sh
#!/usr/bin/env bash
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

# Echo "even" or "odd" for the integer $1.
parity() {
  echo ""  # TODO
}

# FizzBuzz for 1..$1 on one line, space separated.
fizzbuzz() {
  echo ""  # TODO
}

# Echo the file extension of $1 (no dot), or "none" if it has none.
# "a.tar.gz" -> "gz", "Makefile" -> "none". Use case or [[ ]].
ext() {
  echo ""  # TODO
}

# Echo how many lines of stdin are non-empty. Use while read.
non_empty() {
  echo 0  # TODO
}

check "parity even" "$(parity 4)" "even"
check "parity odd" "$(parity 7)" "odd"
check "fizzbuzz" "$(fizzbuzz 15)" "1 2 Fizz 4 Buzz Fizz 7 8 Fizz Buzz 11 Fizz 13 14 FizzBuzz"
check "ext" "$(ext a.tar.gz)" "gz"
check "ext none" "$(ext Makefile)" "none"
check "non_empty" "$(printf 'a\n\nb\n\n\nc\n' | non_empty)" "3"
exit $failed
```

<details><summary>Solution</summary>

```bash file=solution.sh
#!/usr/bin/env bash
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

parity() {
  if (( $1 % 2 == 0 )); then echo even; else echo odd; fi
}

fizzbuzz() {
  local i out=()
  for ((i = 1; i <= $1; i++)); do
    if   (( i % 15 == 0 )); then out+=(FizzBuzz)
    elif (( i % 3 == 0 ));  then out+=(Fizz)
    elif (( i % 5 == 0 ));  then out+=(Buzz)
    else out+=("$i"); fi
  done
  echo "${out[*]}"
}

ext() {
  if [[ $1 == *.* ]]; then echo "${1##*.}"; else echo none; fi
}

non_empty() {
  local n=0 line
  while IFS= read -r line; do
    [[ -n $line ]] && (( ++n ))
  done
  echo "$n"
}

check "parity even" "$(parity 4)" "even"
check "parity odd" "$(parity 7)" "odd"
check "fizzbuzz" "$(fizzbuzz 15)" "1 2 Fizz 4 Buzz Fizz 7 8 Fizz Buzz 11 Fizz 13 14 FizzBuzz"
check "ext" "$(ext a.tar.gz)" "gz"
check "ext none" "$(ext Makefile)" "none"
check "non_empty" "$(printf 'a\n\nb\n\n\nc\n' | non_empty)" "3"
exit $failed
```

</details>

Next: [03 — Functions](03-functions.md)
