# Shell 03 — Functions

A shell function is a named block that behaves like a command: it takes
arguments, reads stdin, writes stdout, and returns an **exit status**
(0–255). It cannot return a string or a number as a value. You *print* the
value and the caller captures it with `$(...)`.

## Example

```bash file=example.sh
#!/usr/bin/env bash

# Arguments: $1.. , $# (count), "$@" (all, each quoted), $0 (script name)
greet() {
  local name="${1:-world}"          # local keeps the variable out of the caller
  echo "hello, $name"
}
greet
greet Ada

# "$@" preserves word boundaries; "$*" glues everything into one string
show() { printf '[%s]' "$@"; echo; }
show "a b" c "d e"

# return sets the status; output is the "value"
is_even() { (( $1 % 2 == 0 )); }    # status of the last command is the return
if is_even 10; then echo "10 even"; fi
is_even 7 || echo "7 odd (status $?)"

# Return a value by printing it; capture with $()
square() { echo $(($1 * $1)); }
echo "square: $(square 9)"

# shift consumes arguments: a tiny option loop
sum_all() {
  local total=0
  while (( $# )); do
    total=$((total + $1))
    shift
  done
  echo "$total"
}
sum_all 1 2 3 4

# Recursion works (keep it shallow)
fact() { if (( $1 <= 1 )); then echo 1; else echo $(( $1 * $(fact $(($1 - 1))) )); fi; }
echo "5! = $(fact 5)"

# Variables are global unless declared local
leak()  { leaked=yes; }
clean() { local scoped=yes; }
leak; clean
echo "leaked=${leaked-unset} scoped=${scoped-unset}"

# Passing an array: pass elements, or a *name* and use a nameref
longest() {
  local -n arr=$1                   # nameref: arr is another name for $1
  local best=""
  for s in "${arr[@]}"; do (( ${#s} > ${#best} )) && best=$s; done
  echo "$best"
}
words=(pear banana fig)
echo "longest: $(longest words)"

# Functions read stdin like any command
upper() { tr '[:lower:]' '[:upper:]'; }
echo "shout" | upper

# Reporting errors: stderr, and a non-zero status
need() {
  [[ -n ${1-} ]] || { echo "need: missing argument" >&2; return 2; }
}
need 2>/dev/null; echo "status $?"
```

```text output
hello, world
hello, Ada
[a b][c][d e]
10 even
7 odd (status 1)
square: 81
10
5! = 120
leaked=yes scoped=unset
longest: banana
SHOUT
status 2
```

## Details that bite

- `return` takes 0–255 only. `return 256` wraps to 0. For data, `echo`.
- `$(...)` captures **stdout**, strips trailing newlines, and runs the
  function in a **subshell**: assignments inside are lost to the caller.
- A function that both prints a value *and* logs to stdout corrupts the
  capture. Send logs to stderr (`>&2`).
- `local x=$(cmd)` hides `cmd`'s exit status behind `local`'s (always 0).
  Split it: `local x; x=$(cmd) || return`.
- Unquoted `$@` re-splits arguments; always write `"$@"`.
- Functions are defined at *run* time, top to bottom. Call a function
  before its definition has executed and you get "command not found".
- A function named like a command shadows it. `command ls` or `\ls` skips
  the function.

## Exercises

```bash file=exercise.sh
#!/usr/bin/env bash
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

# Echo the largest of the integer arguments.
max() {
  echo 0  # TODO
}

# Join the arguments after the first with the separator in $1.
# join , a b c  ->  a,b,c
join() {
  echo ""  # TODO
}

# Succeed (status 0) if $1 is a prime number, else fail. No output.
is_prime() {
  return 1  # TODO
}

# Echo the number of arguments that are non-empty strings.
count_nonempty() {
  echo 0  # TODO
}

# Echo the first argument that names an existing directory, else fail.
first_dir() {
  return 1  # TODO
}

check "max" "$(max 3 41 7 12)" "41"
check "join" "$(join , a b c)" "a,b,c"
check "join one" "$(join , solo)" "solo"
primes=""; for n in 1 2 3 4 5 9 11 15 17; do is_prime "$n" && primes+="$n "; done
check "is_prime" "$primes" "2 3 5 11 17 "
check "count_nonempty" "$(count_nonempty a "" "b c" "")" "2"
check "first_dir" "$(first_dir /nonexistent /tmp /)" "/tmp"
first_dir /nonexistent; check "first_dir none" "$?" "1"
exit $failed
```

<details><summary>Solution</summary>

```bash file=solution.sh
#!/usr/bin/env bash
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

max() {
  local best=$1 n
  for n in "$@"; do (( n > best )) && best=$n; done
  echo "$best"
}

join() {
  local sep=$1 out=$2
  shift 2
  for s in "$@"; do out+="$sep$s"; done
  echo "$out"
}

is_prime() {
  local n=$1 i
  (( n >= 2 )) || return 1
  for ((i = 2; i * i <= n; i++)); do
    (( n % i )) || return 1
  done
}

count_nonempty() {
  local n=0 s
  for s in "$@"; do [[ -n $s ]] && (( ++n )); done
  echo "$n"
}

first_dir() {
  local d
  for d in "$@"; do
    [[ -d $d ]] && { echo "$d"; return 0; }
  done
  return 1
}

check "max" "$(max 3 41 7 12)" "41"
check "join" "$(join , a b c)" "a,b,c"
check "join one" "$(join , solo)" "solo"
primes=""; for n in 1 2 3 4 5 9 11 15 17; do is_prime "$n" && primes+="$n "; done
check "is_prime" "$primes" "2 3 5 11 17 "
check "count_nonempty" "$(count_nonempty a "" "b c" "")" "2"
check "first_dir" "$(first_dir /nonexistent /tmp /)" "/tmp"
first_dir /nonexistent; check "first_dir none" "$?" "1"
exit $failed
```

</details>

Next: [04 — Arrays and maps](04-arrays.md)
