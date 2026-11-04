# Shell 05 — Strings and Parameter Expansion

Before you reach for `sed` or `awk`, bash can slice, trim, replace, and
change case in-process, with no fork. That is faster, and it avoids a
whole class of quoting bugs.

## `#` and `%` trim a glob

One `#` or `%` is the shortest match. Two is the longest. The pattern
is a glob, not a regex. `*` means "anything". A character class is as
close as you get to "digits".

```bash file=n01.sh
path="/home/ada/archive.tar.gz"
echo "${path##*/}"
echo "${path%/*}"
echo "${path%%.*}"
echo "${path%.*}"
echo "${path#/home/}"
```

```text output
archive.tar.gz
/home/ada
/home/ada/archive
/home/ada/archive.tar
ada/archive.tar.gz
```

## `${var/pat/rep}` replaces a glob

One slash replaces the first match. Two replace every match. `#` and
`%` anchor it. An empty replacement deletes. Quote a needle you want
taken literally: `${s/"$needle"/x}`.

```bash file=n02.sh
s="a-b-c-d"
echo "${s/-/+}"
echo "${s//-/+}"
echo "${s/#a/A}"
echo "${s/%d/D}"
echo "${s//-}"
needle="b-c"
echo "${s/"$needle"/X}"
```

```text output
a+b-c-d
a+b+c+d
A-b-c-d
a-b-c-D
abcd
a-X-d
```

## `${var:offset:length}` slices

A negative offset needs a space or parentheses, `${s: -3}`. `${s:-3}`
is the default-value form, not "the last three characters".

```bash file=n03.sh
s="a-b-c-d"
echo "${s:2:3}"
echo "${s: -3}"
echo "default ${s:-3}"
```

```text output
b-c
c-d
default a-b-c-d
```

## `^^` and `,,` change case

Bash 4 and newer. Two carets or commas change the whole value. One
changes the first character. macOS bash 3.2 has none of this. `tr` is
the portable spelling.

```bash file=n04.sh
word="hello World"
echo "${word^^}  ${word,,}  ${word^}"
printf '%s\n' "$word" | tr '[:lower:]' '[:upper:]'
```

```text output
HELLO WORLD  hello world  Hello World
HELLO WORLD
```

## `:-` treats empty as unset; `-` does not

`${var:-x}` fires for unset or empty. `${var-x}` fires only for unset.
`${v:-}` is the safe-under-`set -u` spelling of `$v`.

```bash file=n05.sh
word="hello World"
echo "${#word}"
empty=""
echo "${empty:-default}  ${empty-unchanged}"
echo "[${empty-unchanged}]"
unset missing
echo "missing <${missing:-default}> <${missing-unchanged}>"
```

```text output
11
default  
[]
missing <default> <unchanged>
```

## `${var:?msg}` refuses a missing value

The expansion aborts with your message when the value is unset or
empty. The `:` command is a no-op that still forces the check.

```bash file=n06.sh
( : "${REQUIRED:?REQUIRED must be set}" ) 2>&1 | sed 's/^.*REQUIRED/REQUIRED/'
```

```text output
REQUIRED must be set
```

## `IFS` chooses how `read` splits

The prefix `IFS=:` applies to that one command. The underscores drop
the fields you do not want.

```bash file=n07.sh
line="root:x:0:0:root:/root:/bin/bash"
IFS=: read -r user _ uid _ _ _ shell <<< "$line"
echo "$user has uid $uid and shell $shell"
```

```text output
root has uid 0 and shell /bin/bash
```

## `read` without `-r` eats backslashes

Always pass `-r` unless you truly want the backslash to escape the
next character. `IFS=` keeps leading spaces on the same line.

```bash file=n08.sh
printf 'a\\b\n' | { IFS= read line; echo "plain [$line]"; }
printf 'a\\b\n' | { IFS= read -r line; echo "raw [$line]"; }
```

```text output
plain [ab]
raw [a\b]
```

## `extglob` adds `@()`, `+()`, and the rest

Turn it on before the shell parses the pattern. `@(c|h|cc)` is "one of
these". It is still a glob, not a regex.

```bash file=n09.sh
shopt -s extglob
for f in a.c b.h c.txt d.cc; do
  [[ $f == *.@(c|h|cc) ]] && printf '%s ' "$f"
done
echo
```

```text output
a.c b.h d.cc 
```

## Whitespace trims without a fork

Strip the leading run, then the trailing run. The class `[:space:]`
is whatever the locale calls whitespace.

```bash file=n10.sh
padded="   hi there   "
trimmed="${padded#"${padded%%[![:space:]]*}"}"
trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"
echo "[$trimmed]"
```

```text output
[hi there]
```

## `printf` pads and repeats

The format spec does the alignment. `'=%.0s'` prints `=` and none of
the argument, so a brace range becomes a line of equals signs.

```bash file=n11.sh
printf '%-8s|%8s|\n' left right
printf '%s\n' "$(printf '=%.0s' {1..10})"
```

```text output
left    |   right|
==========
```

## `%q` quotes a value for the shell

The result can be pasted back into a script and it evaluates to the
same string, including quotes, spaces, and dollar signs.

```bash file=n12.sh
printf '%q\n' "it's a \"test\" \$HOME"
```

```text output
it\'s\ a\ \"test\"\ \$HOME
```

## A quoted here-doc delimiter is literal

An unquoted delimiter expands `$` in the body. Quote it (`<<'EOF'`)
when the body is a template you do not want touched.

```bash file=n13.sh
user=root
path="/home/ada/archive.tar.gz"
cat <<EOF
user: $user
home: ${path%/*}
EOF
cat <<'EOF'
literal: $user
EOF
```

```text output
user: root
home: /home/ada
literal: $user
```

## `tr` and `cut` count bytes

`${#s}` and slicing count characters only in a UTF-8 locale. In the
`C` locale they count bytes. `tr` and `cut` always work on bytes.
`echo "$s"` misbehaves when `s` is `-n` or starts with a backslash.
`printf '%s\n' "$s"` does not.

```bash file=n14.sh
echo "hello" | tr 'a-y' 'b-z'
echo "a,b,c" | cut -d, -f2
s="héllo"
export LC_ALL=C.UTF-8
echo "chars ${#s}"
export LC_ALL=C
echo "bytes ${#s}"
printf '%s\n' '-n'
```

```text output
ifmmp
b
chars 5
bytes 6
-n
```

## Exercises

```bash file=exercise.sh
#!/usr/bin/env bash
export LC_ALL=C.UTF-8
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

# basename and dirname, using only parameter expansion (no forks).
base() { echo ""; }   # TODO  base /a/b/c.txt -> c.txt
dir()  { echo ""; }   # TODO  dir  /a/b/c.txt -> /a/b

# Replace every space in $1 with an underscore and lowercase it.
slug() { echo ""; }   # TODO

# Remove leading and trailing whitespace from $1.
trim() { echo ""; }   # TODO

# Echo "yes" if $1 is a valid identifier (letters, digits, _; not starting
# with a digit), else "no". Use [[ =~ ]] or a glob.
is_ident() { echo ""; }   # TODO

# Echo the value for key $1 in a "k1=v1;k2=v2" string $2 (empty if absent).
lookup() { echo ""; }   # TODO

check "base" "$(base /a/b/c.txt)" "c.txt"
check "dir" "$(dir /a/b/c.txt)" "/a/b"
check "slug" "$(slug "Hello Big World")" "hello_big_world"
check "trim" "$(trim "   pad me  ")" "pad me"
check "ident ok" "$(is_ident _x9)" "yes"
check "ident digit" "$(is_ident 9x)" "no"
check "ident dash" "$(is_ident a-b)" "no"
check "lookup" "$(lookup b "a=1;b=22;c=3")" "22"
check "lookup none" "$(lookup z "a=1;b=22")" ""
exit $failed
```

<details><summary>Solution</summary>

```bash file=solution.sh
#!/usr/bin/env bash
export LC_ALL=C.UTF-8
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

base() { echo "${1##*/}"; }
dir()  { echo "${1%/*}"; }

slug() {
  local s=${1// /_}
  echo "${s,,}"
}

trim() {
  local s=$1
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  echo "$s"
}

is_ident() {
  if [[ $1 =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then echo yes; else echo no; fi
}

lookup() {
  local pair
  local IFS=';'
  for pair in $2; do
    [[ ${pair%%=*} == "$1" ]] && { echo "${pair#*=}"; return; }
  done
}

check "base" "$(base /a/b/c.txt)" "c.txt"
check "dir" "$(dir /a/b/c.txt)" "/a/b"
check "slug" "$(slug "Hello Big World")" "hello_big_world"
check "trim" "$(trim "   pad me  ")" "pad me"
check "ident ok" "$(is_ident _x9)" "yes"
check "ident digit" "$(is_ident 9x)" "no"
check "ident dash" "$(is_ident a-b)" "no"
check "lookup" "$(lookup b "a=1;b=22;c=3")" "22"
check "lookup none" "$(lookup z "a=1;b=22")" ""
exit $failed
```

</details>

Next: [06 — Redirection and pipes](06-redirection-pipes.md)
