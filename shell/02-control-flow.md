# Shell 02 — Control Flow

Shell branches on **exit status**, not on booleans. `if` runs a command;
status `0` means "true". `[[ ... ]]` and `(( ... ))` are just commands that
return 0 or 1.

## Example

```bash file=example.sh
#!/usr/bin/env bash

# if tests a command's exit status
if grep -q "needle" <<< "hay needle hay"; then echo "found"; fi

# [[ ]] is the bash test: strings, files, patterns, regex
f="report.txt"
[[ $f == *.txt ]]            && echo "glob match"
[[ $f =~ ^([a-z]+)\.txt$ ]]  && echo "regex group: ${BASH_REMATCH[1]}"
[[ -z "" ]]                  && echo "empty string"
[[ -d /tmp ]]                && echo "/tmp is a directory"
[[ -e /definitely/not/here ]] || echo "missing"

# (( )) is arithmetic; non-zero is true
n=7
if (( n % 2 )); then echo "$n is odd"; fi

# && and || chain on status; the last status wins
true && echo "and-then" || echo "never"
false || echo "or-else"

# for over words, globs, ranges and C-style
for color in red green blue; do printf '%s ' "$color"; done; echo
for i in {1..5}; do printf '%d ' "$i"; done; echo
for ((i = 10; i > 0; i -= 4)); do printf '%d ' "$i"; done; echo

# while read: the idiom for lines (-r keeps backslashes, IFS= keeps spaces)
while IFS= read -r line; do echo "[$line]"; done <<'EOF_DATA'
  indented
two words
EOF_DATA

# case matches glob patterns; ;; ends a branch
kind() {
  case "$1" in
    *.tar.gz|*.tgz) echo "tarball" ;;
    *.md)           echo "markdown" ;;
    [0-9]*)         echo "starts with digit" ;;
    *)              echo "unknown" ;;
  esac
}
kind a.tgz; kind notes.md; kind 7up; kind zzz

# break / continue, and until
count=0
until (( count >= 3 )); do
  (( ++count ))
  (( count == 2 )) && continue
  echo "count=$count"
done

# select a sum with a loop; (( )) assigns too
total=0
for n in 1 2 3 4; do (( total += n )); done
echo "total=$total"
```

```text output
found
glob match
regex group: report
empty string
/tmp is a directory
missing
7 is odd
and-then
or-else
red green blue 
1 2 3 4 5 
10 6 2 
[  indented]
[two words]
tarball
markdown
starts with digit
unknown
count=1
count=3
total=10
```

## Details that bite

- `if [ $x = y ]` with `x` empty or containing spaces is a syntax error.
  `[[ ]]` does not word-split, so prefer it in bash. (`[` is a real command,
  which is why it needs the closing `]` and spaces.)
- `a && b || c` is **not** if/then/else: if `b` fails, `c` also runs. Use a
  real `if` when `b` can fail.
- In `[[ $x == pat ]]` an *unquoted* right side is a glob pattern; quote it
  (`"$pat"`) to compare literally. For `=~` keep the regex in a variable
  instead of inline when it contains spaces.
- `(( count++ ))` returns status 1 when the old value is 0, which kills a
  script under `set -e` (lesson 07). `(( ++count ))` or `count=$((count+1))`
  are safe.
- `for f in $(ls)` splits on spaces and breaks on odd names. Use a glob:
  `for f in *.txt`. If nothing matches, the loop runs once with the
  literal `*.txt` unless you `shopt -s nullglob`.
- A `while read` fed by a pipe runs in a subshell, so variables set inside
  vanish (lesson 08). Feed it with `< file` or `<<< "$var"` instead.

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
