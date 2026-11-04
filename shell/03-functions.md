# Shell 03 — Functions

A shell function is a command. It takes arguments, reads stdin, writes
stdout, and returns an exit status from 0 to 255. It cannot return a
string. Print the value and let the caller capture it with `$(...)`.

## Arguments are `$1`, `$#`, and `"$@"`

`local` keeps a variable out of the caller. `${1:-world}` supplies a
default when the argument is missing or empty. `$0` is the script, not
the function.

```bash file=n01.sh
greet() {
  local name="${1:-world}"
  echo "hello, $name"
}
greet
greet Ada
```

```text output
hello, world
hello, Ada
```

## `"$@"` keeps each argument

`"$*"` joins them into one string, using the first character of `IFS`.
Unquoted `$@` splits them again. Always write `"$@"`.

```bash file=n02.sh
show() { printf '[%s]' "$@"; echo; }
show "a b" c "d e"
joined() { printf '[%s]' "$*"; echo; }
joined "a b" c "d e"
bad() { printf '[%s]' $@; echo; }
bad "a b" c
```

```text output
[a b][c][d e]
[a b c d e]
[a][b][c]
```

## `return` sets the status, not the value

With no `return`, the status is whatever the last command returned.
`return` takes 0–255 only. `return 256` wraps to 0. For data, `echo`.

```bash file=n03.sh
is_even() { (( $1 % 2 == 0 )); }
if is_even 10; then echo "10 even"; fi
is_even 7 || echo "7 odd (status $?)"
wrap() { return 256; }
wrap
echo "256 -> $?"
```

```text output
10 even
7 odd (status 1)
256 -> 0
```

## `$(...)` captures stdout in a subshell

Trailing newlines are stripped. Assignments inside the substitution
die with the subshell. They do not change the caller.

```bash file=n04.sh
square() { echo $(($1 * $1)); }
echo "square: $(square 9)"
nl() { printf 'a\n\n'; }
echo "stripped [$(nl)]"
inner=outer
echo "captured $(inner=inner; echo "$inner")"
echo "caller still $inner"
```

```text output
square: 81
stripped [a]
captured inner
caller still outer
```

## Logs on stdout corrupt the capture

A function that prints a value and a log to the same stream mixes them.
Send the log to stderr (`>&2`).

```bash file=n05.sh
noisy() { echo "log" >&2; echo "value"; }
echo "got $(noisy)"
```

```text output
log
got value
```

## `local x=$(cmd)` hides a failure

`local` itself succeeds, so the command's status is lost. Split it:
`local x; x=$(cmd) || return`.

```bash file=n06.sh
bad() { local x; x=$(false); echo "split status $?"; }
bad
hide() { local x=$(false); echo "hidden status $?"; }
hide
strict() { local x; x=$(false) || return 4; echo "nope"; }
strict
echo "strict $?"
```

```text output
split status 1
hidden status 0
strict 4
```

## `shift` drops the first argument

The rest slide down, and `$#` shrinks. A loop can consume every
argument that way.

```bash file=n07.sh
sum_all() {
  local total=0
  while (( $# )); do
    total=$((total + $1))
    shift
  done
  echo "$total"
}
sum_all 1 2 3 4
```

```text output
10
```

## A function may call itself

Each call is its own set of arguments. Keep the recursion shallow. The
shell is not a good place for a deep call stack.

```bash file=n08.sh
fact() {
  if (( $1 <= 1 )); then
    echo 1
  else
    echo $(( $1 * $(fact $(($1 - 1))) ))
  fi
}
echo "5! = $(fact 5)"
```

```text output
5! = 120
```

## Without `local`, the name leaks

`local` is what stops a function from writing over the caller. The
default is one global namespace.

```bash file=n09.sh
leak()  { leaked=yes; }
clean() { local scoped=yes; }
leak
clean
echo "leaked=${leaked-unset} scoped=${scoped-unset}"
```

```text output
leaked=yes scoped=unset
```

## A nameref passes an array by name

There are no nested arrays. Pass the elements, or pass the array's
name and bind it with `local -n`.

```bash file=n10.sh
longest() {
  local -n arr=$1
  local best=""
  for s in "${arr[@]}"; do
    (( ${#s} > ${#best} )) && best=$s
  done
  echo "$best"
}
words=(pear banana fig)
echo "longest: $(longest words)"
```

```text output
longest: banana
```

## A function reads stdin like any command

Nothing about a function is special to pipes. If it reads stdin, the
caller can pipe into it.

```bash file=n11.sh
upper() { tr '[:lower:]' '[:upper:]'; }
echo "shout" | upper
```

```text output
SHOUT
```

## Fail on stderr, with a non-zero status

Stdout stays the value. Stderr is the message. The caller checks `$?`.

```bash file=n12.sh
need() {
  [[ -n ${1-} ]] || { echo "need: missing argument" >&2; return 2; }
}
need
echo "status $?"
```

```text output
need: missing argument
status 2
```

## A function exists after its definition runs

Definitions run top to bottom, like any other command. A call before
that is "command not found".

```bash file=n13.sh
early || echo "not defined yet"
early() { echo "now defined"; }
early
```

```text output
n13.sh: line 1: early: command not found
not defined yet
now defined
```

## A function shadows a command of the same name

The function wins. `command echo` or `\echo` skips it and runs the
real command.

```bash file=n14.sh
echo() { printf 'fn\n'; }
echo hi
command echo hi
```

```text output
fn
hi
```

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
