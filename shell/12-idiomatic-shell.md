# Shell 12 — Idiomatic Shell

These are the rules that keep a script from breaking on a file called
`my notes (final).txt`. `#!/usr/bin/env bash` and `set -euo pipefail`
belong at the top. Know what each switch does, and when to loosen it
(lesson 07). If a script passes about 200 lines, needs real data
structures, or parses structured data, reach for Python or Go.
ShellCheck flags the pattern (SC2086 is "quote this"). It cannot know
your data. `shfmt` fixes layout. Do not `sudo` inside a script you did
not write, and do not `curl ... | bash` anything you have not read.

## Quote every expansion

Use arrays for lists and `"$@"` to pass them on. An unquoted `$f`
is two arguments when the value contains a space.

```bash file=n01.sh
set -euo pipefail
export LC_ALL=C
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
touch -- "a b.txt"
f="a b.txt"
bad=$(ls $f 2>&1 | head -1 | cut -c1-30 || true)
echo "unquoted: $bad"
echo "quoted: $(ls -- "$f")"
```

```text output
unquoted: ls: a: No such file or directo
quoted: a b.txt
```

## Walk a glob, not the output of `ls`

`$(ls)` splits on spaces. A glob does not. Do not parse `ls`, `ps`,
or `df` when a machine-readable flag exists (`stat -c`, `ps -o pid=`,
`df --output`).

```bash file=n02.sh
set -euo pipefail
export LC_ALL=C
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
touch -- "a b.txt" "c.txt" "-weird.txt"
count=0
for file in ./*.txt; do count=$((count + 1)); done
echo "$count files"
```

```text output
3 files
```

## End the option list with `--`

A name that starts with `-` is otherwise a flag. `./"$f"` is the
other way to say "this is a path".

```bash file=n03.sh
set -euo pipefail
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
touch -- "-weird.txt"
rm -- ./-weird.txt
echo "removed -weird.txt"
```

```text output
removed -weird.txt
```

## Build the command in an array

A string gets word-split and globbed when you run it. An array does
not. Long options are just elements.

```bash file=n04.sh
set -euo pipefail
export LC_ALL=C
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
touch -- "a b.txt" "c.txt"
args=(-1)
cmd=(ls "${args[@]}")
echo "$("${cmd[@]}" | tr '\n' ' ')"
```

```text output
a b.txt c.txt 
```

## `[[ ]]` and `(( ))` in bash; `[ ]` only in `sh`

`[[ ]]` does not word-split, so an empty value is safe. `(( ))` is
the arithmetic test.

```bash file=n05.sh
var=""
[[ -z $var ]] && echo "no quoting worries with empty"
(( 2 + 2 == 4 )) && echo "arithmetic ok"
```

```text output
no quoting worries with empty
arithmetic ok
```

## `$(...)` nests; backticks do not

Backticks need backslash gymnastics the moment a command contains
another command. `$(...)` is just quotes.

```bash file=n06.sh
echo "$(basename "$(dirname "/a/b/c")")"
```

```text output
b
```

## `IFS= read -r` keeps the bytes of the line

The default `read` strips leading whitespace and eats backslashes.
Data in, data out, means both flags.

```bash file=n07.sh
printf '  keep leading\n' | { IFS= read -r line; echo "[$line]"; }
```

```text output
[  keep leading]
```

## `printf` for data, `echo` for a fixed message

`echo` is fine for a sentence you typed yourself. It is the wrong
tool for a value that might be `-n` or might contain a backslash.

```bash file=n08.sh
s='-n'
printf '%s\n' "$(printf '%s' "$s")"
```

```text output
-n
```

## `local` in functions, `readonly` for constants

Lowercase names are locals. UPPERCASE is for exports and constants.
A `readonly` name cannot be assigned again, including in a subshell.

```bash file=n09.sh
set -euo pipefail
readonly VERSION="1.2.3"
( VERSION=2 ) 2>&1 | sed 's/^.*: //' || true
echo "constant: $VERSION"
f() { local name="ada"; echo "$name"; }
f
```

```text output
readonly variable
constant: 1.2.3
ada
```

## `mktemp` and `trap EXIT` own every temp file

The trap runs on the way out, including after a failure. The
directory name is unique, so two runs do not collide.

```bash file=n10.sh
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"; echo cleaned' EXIT
echo work > "$tmp/f"
[[ -f $tmp/f ]] && echo "temp exists"
```

```text output
temp exists
cleaned
```

## Errors go to stderr; data stays on stdout

The status is part of the interface. A pipeline can still read the
data when the message is on the other stream.

```bash file=n11.sh
die() { echo "error: $*" >&2; return 2; }
die "nope" || echo "status $?"
```

```text output
error: nope
status 2
```

## Redirect and here-strings beat a useless `cat`

`cmd < file` replaces `cat file | cmd`. `cmd <<< "$var"` replaces
`echo "$var" | cmd`. Both skip a process. `$(( ))` also strips the
padding some `wc` builds put on a count.

```bash file=n12.sh
tmp=$(mktemp -d)
cd "$tmp"
printf 'x\n' > one.txt
echo "$(( $(wc -l < one.txt) ))"
f="a b.txt"
tr a-z A-Z <<< "$f"
```

```text output
1
A B.TXT
```

## Guard `main` so the file can be sourced

`[[ ${BASH_SOURCE[0]} == "$0" ]]` is true when you ran the file, and
false when another script sourced it. A test can then call functions
without running the program. A script that "works on my machine"
often depends on the locale, GNU versus BSD flags, `$PATH`, the
current directory, or a tty. Set `LC_ALL`, check tools with
`command -v`, and take paths from `${BASH_SOURCE[0]}`.

```bash file=n13.sh
tmp=$(mktemp -d)
cat > "$tmp/lib.sh" << 'EOF'
main() { echo "ran"; }
if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
  main "$@"
else
  echo "loaded"
fi
EOF
echo "executed: $(bash "$tmp/lib.sh")"
echo "sourced: $(bash -c "source \"$tmp/lib.sh\"")"
```

```text output
executed: ran
sourced: loaded
```

## Assign after `local`, and check that status

`set -e` does not see `local out=$(failing)`. Write `local out` and
then `out=$(cmd) || return`. Put `|| return` or `|| die` on the
commands that matter. `if` turns `set -e` off for the whole call.

```bash file=n14.sh
set -euo pipefail
f2() {
  local out
  out=$(printf 'value')
  echo "$out"
}
echo "$(f2)"
bad() { local out; out=$(false) || return 3; echo "nope"; }
bad || echo "returned $?"
```

```text output
value
returned 3
```

## Parameter expansion beats a fork in a loop

`basename` starts a process. `${path##*/}` does not. In a tight loop
that difference is the whole runtime.

```bash file=n15.sh
path=/a/b/c.txt
echo "${path##*/} vs $(basename "$path")"
```

```text output
c.txt vs c.txt
```

## Check a tool before you call it

`command -v` is true when the name is on `PATH`. Fail there, with a
message on stderr, instead of failing halfway through the work.

```bash file=n16.sh
require() {
  command -v "$1" >/dev/null || { echo "missing: $1" >&2; return 1; }
}
require bash && echo "bash found"
require not-a-real-tool 2>&1 || true
```

```text output
bash found
missing: not-a-real-tool
```

## `${var:-default}` fills a missing value

The default is used when the variable is unset or empty. A value that
is already set is left alone. `${name,,}` is the lowercase copy in bash
4.

```bash file=n17.sh
unset APP_PORT
echo "default ${APP_PORT:-80}"
APP_PORT=8080
echo "set ${APP_PORT:-80}"
name="Ada"
echo "${name,,}"
```

```text output
default 80
set 8080
ada
```

## Exercises

```bash file=exercise.sh
#!/usr/bin/env bash
export LC_ALL=C
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
touch "a b.txt" "c.txt" "d e f.md" ./-x.txt $'x.txt\nfoo'

# Each function below is written the *buggy* way. Fix it.

# Count *.txt files in the current directory (names may have spaces).
count_txt() {
  ls | grep '\.txt$' | wc -l | tr -d ' '
}

# Echo the first line of file $1 exactly, keeping leading whitespace.
first_line() {
  read line < $1
  echo $line
}

# Delete all files in directory $1 whose names end in .md.
rm_md() {
  rm $1/*.md
}

# Echo "yes" if $1 is empty or only whitespace, else "no".
is_blank() {
  if [ $1 = "" ]; then echo yes; else echo no; fi
}

# Run a command line given as one string: here, an array is expected;
# echo the number of arguments the command received.
argc() {
  local cmd="printf %s\\n $*"
  $cmd | wc -l | tr -d ' '
}

check "count_txt" "$(count_txt)" "3"
printf '  indented\nsecond\n' > "$tmp/in file"
check "first_line" "$(first_line "$tmp/in file")" "  indented"
rm_md "$tmp"; check "rm_md" "$(ls | tr '\n' ';')" "-x.txt;a b.txt;c.txt;in file;x.txt;foo;"
check "blank" "$(is_blank "   ")" "yes"
check "not blank" "$(is_blank "x y")" "no"
check "argc" "$(argc 'a b' c)" "2"
exit $failed
```

<details><summary>Solution</summary>

```bash file=solution.sh
#!/usr/bin/env bash
export LC_ALL=C
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
touch "a b.txt" "c.txt" "d e f.md" ./-x.txt $'x.txt\nfoo'

count_txt() {
  local n=0 f
  shopt -s nullglob
  for f in ./*.txt; do n=$((n + 1)); done
  shopt -u nullglob
  echo "$n"
}

first_line() {
  local line
  IFS= read -r line < "$1"
  printf '%s\n' "$line"
}

rm_md() {
  rm -f -- "${1:?}"/*.md
}

is_blank() {
  if [[ -z ${1//[[:space:]]/} ]]; then echo yes; else echo no; fi
}

argc() {
  local cmd=(printf '%s\n' "$@")
  "${cmd[@]}" | wc -l | tr -d ' '
}

check "count_txt" "$(count_txt)" "3"
printf '  indented\nsecond\n' > "$tmp/in file"
check "first_line" "$(first_line "$tmp/in file")" "  indented"
rm_md "$tmp"; check "rm_md" "$(ls | tr '\n' ';')" "-x.txt;a b.txt;c.txt;in file;x.txt;foo;"
check "blank" "$(is_blank "   ")" "yes"
check "not blank" "$(is_blank "x y")" "no"
check "argc" "$(argc 'a b' c)" "2"
exit $failed
```

</details>

Next: [13 — Testing shell code](13-testing.md)
