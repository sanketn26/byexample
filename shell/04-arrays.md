# Shell 04 — Arrays and Associative Arrays

Plain POSIX `sh` has no arrays, only the positional parameters. Bash
adds indexed arrays and associative arrays (maps, bash 4+). Use them
instead of space-separated strings: elements keep their spaces.
macOS ships bash 3.2, which has no `declare -A`, no `mapfile`, and no
`${a[-1]}`. This track wants bash 4.4+.

## An indexed array keeps each element

`+=( )` appends. `${#a[@]}` is the count. `${a[-1]}` is the last
element. `${a[@]:1:2}` is a slice: offset 1, length 2.

```bash file=n01.sh
fruit=(apple "dragon fruit" cherry)
fruit+=(date)
echo "count: ${#fruit[@]}"
echo "second: ${fruit[1]}"
echo "last: ${fruit[-1]}"
echo "slice: ${fruit[@]:1:2}"
```

```text output
count: 4
second: dragon fruit
last: date
slice: dragon fruit cherry
```

## `"${a[@]}"` is one word per element

`$a` alone is only element 0. `"${a[*]}"` is a single string.
Unquoted `${a[@]}` splits on whitespace again, so the space inside
`"dragon fruit"` comes back as a word break.

```bash file=n02.sh
fruit=(apple "dragon fruit" cherry date)
echo "zero: $fruit"
echo "star: ${fruit[*]}"
for f in "${fruit[@]}"; do printf '<%s>' "$f"; done
echo
printf '<%s>' ${fruit[@]}
echo
```

```text output
zero: apple
star: apple dragon fruit cherry date
<apple><dragon fruit><cherry><date>
<apple><dragon><fruit><cherry><date>
```

## `unset` leaves a hole

Indices do not slide down to fill the gap. Re-pack with
`a=("${a[@]}")` if you want them dense again. A sparse array is
legal: the index does not have to start at 0.

```bash file=n03.sh
sparse=([2]=two [7]=seven)
echo "indices: ${!sparse[@]}"
fruit=(apple "dragon fruit" cherry date)
unset 'fruit[0]'
echo "hole: ${fruit[*]} (indices ${!fruit[@]})"
fruit=("${fruit[@]}")
echo "repacked: ${fruit[*]} (indices ${!fruit[@]})"
```

```text output
indices: 2 7
hole: dragon fruit cherry date (indices 1 2 3)
repacked: dragon fruit cherry date (indices 0 1 2)
```

## `arr=($(cmd))` splits and globs

Command substitution is then word-split, and `*` in the output becomes
a glob. For one element per line, use `mapfile -t`. For fields on one
line, use `read -ra`.

```bash file=n04.sh
mapfile -t lines < <(printf 'b\na\nc\n')
echo "lines: ${lines[*]}"
sorted=($(printf '%s\n' "${lines[@]}" | sort))
echo "sorted: ${sorted[*]}"
tmp=$(mktemp -d)
touch "$tmp/surprise"
cd "$tmp"
mapfile -t safe < <(printf '*\n')
unsafe=($(printf '*\n'))
echo "mapfile <${safe[*]}>"
echo "split <${unsafe[*]}>"
```

```text output
lines: b a c
sorted: a b c
mapfile <*>
split <surprise>
```

## `"${a[*]}"` joins on the first character of `IFS`

Set `IFS` for the expansion only. A command in `$( )` is a subshell,
so the caller's `IFS` stays a space.

```bash file=n05.sh
sorted=(a b c)
joined=$(IFS=,; echo "${sorted[*]}")
echo "joined: $joined"
```

```text output
joined: a,b,c
```

## `read -ra` splits one line into fields

`IFS` is the separator for that `read` only when you assign it as a
prefix. `-a` stores the fields in an array. `-r` keeps backslashes.

```bash file=n06.sh
IFS=: read -ra parts <<< "usr:local:bin"
echo "parts: ${#parts[@]} -> ${parts[2]}"
```

```text output
parts: 3 -> bin
```

## Associative arrays must be `declare -A`

Without `-A`, `a[x]=1` is an indexed array and `x` is evaluated as
arithmetic. There are no nested arrays. Store a record as one string,
or hand the data to `jq`, `awk`, or Python. `${age[bob]-no}` is the
default when that key is unset. `[[ -v age[linus] ]]` asks whether the
key was set.

```bash file=n07.sh
x=5
a[x]=1
echo "indexed ${!a[@]} -> ${a[5]}"
declare -A age=([ada]=36 [linus]=55)
age[grace]=85
echo "ada is ${age[ada]}"
echo "has bob? ${age[bob]-no}"
[[ -v age[linus] ]] && echo "linus present"
echo "size: ${#age[@]}"
```

```text output
indexed 5 -> 1
ada is 36
has bob? no
linus present
size: 3
```

## Keys come back in no particular order

Sort them yourself when the output has to be stable. The order of
`${!age[@]}` is not part of the language.

```bash file=n08.sh
declare -A age=([ada]=36 [linus]=55 [grace]=85)
for k in $(printf '%s\n' "${!age[@]}" | sort); do
  printf '%s=%s ' "$k" "${age[$k]}"
done
echo
```

```text output
ada=36 grace=85 linus=55 
```

## A map is how you count

The arithmetic context treats a missing key as 0, then stores the
increment. Read the keys you care about in a fixed order.

```bash file=n09.sh
declare -A seen
for w in a b a c b a; do (( seen[$w]++ )); done
for k in a b c; do printf '%s:%d ' "$k" "${seen[$k]}"; done
echo
```

```text output
a:3 b:2 c:1 
```

## The positional parameters are an array too

`set --` replaces `$@`. Quoted elements keep their spaces. Under
`set -u`, an empty `"${a[@]}"` is an error on bash older than 4.4.
`${a[@]+"${a[@]}"}` is the guard that stays quiet when the array is
empty. Bash 4.4 and newer accept the plain expansion.

```bash file=n10.sh
set -- x "y z" w
echo "$# args, second is '$2'"
set -u
empty=()
echo "guard <${empty[@]+"${empty[@]}"}>"
```

```text output
3 args, second is 'y z'
guard <>
```

## Exercises

```bash file=exercise.sh
#!/usr/bin/env bash
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

# Echo the elements of the array NAMED by $1 in reverse order, space separated.
reverse() {
  echo ""  # TODO (hint: local -n)
}

# Read lines from stdin; echo the number of DISTINCT lines.
distinct() {
  echo 0  # TODO (hint: declare -A)
}

# Echo the word that occurs most often in the arguments (ties: first seen).
mode() {
  echo ""  # TODO
}

# Echo the arguments whose length is at least $1, space separated.
longer_than() {
  echo ""  # TODO
}

nums=(1 2 3 4)
check "reverse" "$(reverse nums)" "4 3 2 1"
check "distinct" "$(printf 'a\nb\na\nc\nb\n' | distinct)" "3"
check "mode" "$(mode x y z y z y)" "y"
check "mode tie" "$(mode p q q p)" "p"
check "longer_than" "$(longer_than 3 ab abc "hello world" x)" "abc hello world"
exit $failed
```

<details><summary>Solution</summary>

```bash file=solution.sh
#!/usr/bin/env bash
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

reverse() {
  local -n arr=$1
  local out=() i
  for ((i = ${#arr[@]} - 1; i >= 0; i--)); do out+=("${arr[i]}"); done
  echo "${out[*]}"
}

distinct() {
  local -A seen=()
  local line
  while IFS= read -r line; do seen[$line]=1; done
  echo "${#seen[@]}"
}

mode() {
  local -A count=()
  local order=() w best="" n
  for w in "$@"; do
    [[ -v count[$w] ]] || order+=("$w")
    (( count[$w]++ ))
  done
  n=0
  for w in "${order[@]}"; do
    (( count[$w] > n )) && { best=$w; n=${count[$w]}; }
  done
  echo "$best"
}

longer_than() {
  local min=$1 out=() s
  shift
  for s in "$@"; do (( ${#s} >= min )) && out+=("$s"); done
  echo "${out[*]}"
}

nums=(1 2 3 4)
check "reverse" "$(reverse nums)" "4 3 2 1"
check "distinct" "$(printf 'a\nb\na\nc\nb\n' | distinct)" "3"
check "mode" "$(mode x y z y z y)" "y"
check "mode tie" "$(mode p q q p)" "p"
check "longer_than" "$(longer_than 3 ab abc "hello world" x)" "abc hello world"
exit $failed
```

</details>

Next: [05 — Strings and expansion](05-strings.md)
