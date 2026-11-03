# Shell 05 — Strings and Parameter Expansion

Before you reach for `sed` or `awk`, know that bash can slice, trim,
replace and change the case of a variable **in-process**, with no fork.
That is faster and avoids a whole class of quoting bugs.

## Example

```bash file=example.sh
#!/usr/bin/env bash
export LC_ALL=C.UTF-8

path="/home/ada/archive.tar.gz"

# Trim from the front (#) or back (%): one char = shortest, two = longest
echo "${path##*/}"          # basename:  archive.tar.gz
echo "${path%/*}"           # dirname:   /home/ada
echo "${path%%.*}"          # drop all extensions
echo "${path%.*}"           # drop the last extension
echo "${path#/home/}"       # drop a literal prefix

# Replace: first (/) or all (//); anchors with # and %
s="a-b-c-d"
echo "${s/-/+}"
echo "${s//-/+}"
echo "${s/#a/A}"            # only at the start
echo "${s/%d/D}"            # only at the end
echo "${s//-}"              # no replacement text = delete

# Substring: ${var:offset:length}, negative offsets need a space or ()
echo "${s:2:3}"
echo "${s: -3}"

# Case conversion (bash 4+)
word="hello World"
echo "${word^^}  ${word,,}  ${word^}"

# Length, and checking for empty
echo "${#word}"
empty=""
echo "${empty:-default}  ${empty-unchanged}"   # :- treats empty as unset, - does not
echo "[${empty-unchanged}]"

# Required variables fail loudly
( : "${REQUIRED:?REQUIRED must be set}" ) 2>&1 | sed 's/^.*REQUIRED/REQUIRED/'

# Splitting with IFS
line="root:x:0:0:root:/root:/bin/bash"
IFS=: read -r user _ uid _ _ _ shell <<< "$line"
echo "$user has uid $uid and shell $shell"

# Pattern matching with extglob
shopt -s extglob
for f in a.c b.h c.txt d.cc; do
  [[ $f == *.@(c|h|cc) ]] && printf '%s ' "$f"
done; echo

# Trimming whitespace without forking
padded="   hi there   "
trimmed="${padded#"${padded%%[![:space:]]*}"}"
trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"
echo "[$trimmed]"

# Repeating and padding with printf
printf '%-8s|%8s|\n' left right
printf '%s\n' "$(printf '=%.0s' {1..10})"

# Escaping for reuse: %q makes a value safe to paste back into a shell
printf '%q\n' "it's a \"test\" \$HOME"

# Multi-line strings: here-doc keeps newlines
cat <<EOF
user: $user
home: ${path%/*}
EOF
# Quote the delimiter to stop expansion
cat <<'EOF'
literal: $user
EOF

# Byte-level work is for tools: tr, cut, wc
echo "hello" | tr 'a-y' 'b-z'
echo "a,b,c" | cut -d, -f2
```

```text output
archive.tar.gz
/home/ada
/home/ada/archive
/home/ada/archive.tar
ada/archive.tar.gz
a+b-c-d
a+b+c+d
A-b-c-d
a-b-c-D
abcd
b-c
c-d
HELLO WORLD  hello world  Hello World
11
default  
[]
REQUIRED must be set
root has uid 0 and shell /bin/bash
a.c b.h d.cc 
[hi there]
left    |   right|
==========
it\'s\ a\ \"test\"\ \$HOME
user: root
home: /home/ada
literal: $user
ifmmp
b
```

## Details that bite

- `${var#pat}` / `%pat` use **glob** patterns, not regex. `*` here means
  "anything", and you cannot say "digits" without a bracket class.
- `${s/pat/rep}` treats `pat` as a glob too; quote parts you want literal:
  `${s/"$needle"/x}`.
- `${var:-x}` vs `${var-x}`: the colon form also triggers on empty. Pick
  the one you mean; `${v:-}` is the safe-under-`set -u` spelling of "$v".
- `${s:-3}` is *not* "last three chars" (that is `${s: -3}`, with a space).
- `${var^^}` needs bash 4. On macOS's bash 3.2 use `tr`.
- `read -r` always. Without `-r`, backslashes in the input are eaten.
- `echo "$s"` with `s='-n'` or `'\n'` misbehaves; `printf '%s\n' "$s"` is
  always right.
- Strings are bytes plus a locale. `${#s}` and slicing count characters
  only in a UTF-8 locale.

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
