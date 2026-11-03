# Shell 04 — Arrays and Associative Arrays

Plain POSIX `sh` has no arrays, only the positional parameters. Bash adds
**indexed** arrays and **associative** arrays (maps, bash 4+). Use them
instead of space-separated strings: they survive spaces in elements.

## Example

```bash file=example.sh
#!/usr/bin/env bash

# Indexed arrays
fruit=(apple "dragon fruit" cherry)
fruit+=(date)                          # append
echo "count: ${#fruit[@]}"
echo "second: ${fruit[1]}"
echo "last: ${fruit[-1]}"
echo "slice: ${fruit[@]:1:2}"

# "${a[@]}" gives one word per element, spaces preserved
for f in "${fruit[@]}"; do printf '<%s>' "$f"; done; echo
printf '<%s>' ${fruit[@]}; echo        # unquoted re-splits "dragon fruit"

# Indices (arrays can be sparse)
sparse=([2]=two [7]=seven)
echo "indices: ${!sparse[@]}"

# Remove an element, and delete a whole array
unset 'fruit[0]'
echo "after unset: ${fruit[*]}  (indices ${!fruit[@]})"

# Build arrays from command output, one element per line
mapfile -t lines < <(printf 'b\na\nc\n')
echo "lines: ${lines[*]}"
sorted=($(printf '%s\n' "${lines[@]}" | sort))   # fine here: no spaces
echo "sorted: ${sorted[*]}"

# Joining with a custom separator: "${a[*]}" uses the first char of IFS
joined=$(IFS=,; echo "${sorted[*]}")
echo "joined: $joined"

# Split a string into an array
IFS=: read -ra parts <<< "usr:local:bin"
echo "parts: ${#parts[@]} -> ${parts[2]}"

# Associative arrays must be declared
declare -A age=([ada]=36 [linus]=55)
age[grace]=85
echo "ada is ${age[ada]}"
echo "has bob? ${age[bob]-no}"
[[ -v age[linus] ]] && echo "linus present"
echo "size: ${#age[@]}"

# Keys come back in no particular order; sort them for stable output
for k in $(printf '%s\n' "${!age[@]}" | sort); do printf '%s=%s ' "$k" "${age[$k]}"; done; echo

# Counting words with a map
declare -A seen
for w in a b a c b a; do (( seen[$w]++ )); done
for k in a b c; do printf '%s:%d ' "$k" "${seen[$k]}"; done; echo

# Positional parameters are an array too
set -- x "y z" w
echo "$# args, second is '$2'"
```

```text output
count: 4
second: dragon fruit
last: date
slice: dragon fruit cherry
<apple><dragon fruit><cherry><date>
<apple><dragon><fruit><cherry><date>
indices: 2 7
after unset: dragon fruit cherry date  (indices 1 2 3)
lines: b a c
sorted: a b c
joined: a,b,c
parts: 3 -> bin
ada is 36
has bob? no
linus present
size: 3
ada=36 grace=85 linus=55 
a:3 b:2 c:1 
3 args, second is 'y z'
```

## Details that bite

- `"${a[@]}"` (each element, quoted) vs `"${a[*]}"` (one string). `$a`
  alone is **only element 0**.
- `unset 'a[0]'` leaves a hole; indices do not shift. Re-pack with
  `a=("${a[@]}")`.
- `arr=($(cmd))` word-splits **and globs** the output. For lines use
  `mapfile -t arr < <(cmd)`; for fields use `read -ra`.
- Associative arrays need `declare -A` first; without it `a[x]=1` makes an
  *indexed* array and `x` is evaluated as arithmetic.
- No nested arrays. Encode records as `"name|age"` strings or parallel
  arrays, or reach for another tool (`jq`, `awk`, Python).
- macOS ships bash 3.2: no `declare -A`, no `mapfile`, no `${a[-1]}`.
  If you must run there, install a newer bash or write for it explicitly.
- Under `set -u`, an empty array reference (`"${a[@]}"`) errors on old
  bash (< 4.4). `${a[@]+"${a[@]}"}` is the portable guard.

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
