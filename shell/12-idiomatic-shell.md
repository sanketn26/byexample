# Shell 12 — Idiomatic Shell

The rules experienced shell programmers follow, with before/after pairs.
Almost every item is a bug that only shows up on a file called
`my notes (final).txt`.

## Example

```bash file=example.sh
#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
touch -- "a b.txt" "c.txt" "-weird.txt"   # -- ends options: the name starts with a dash

show() { printf '%s\n' "$1: $2"; }

# 1. Quote every expansion.
f="a b.txt"
bad=$(ls $f 2>&1 | head -1 | cut -c1-30 || true)      # two arguments: "a" and "b.txt"
show "unquoted" "$bad"
show "quoted" "$(ls -- "$f")"

# 2. Iterate with globs and arrays, never with $(ls).
count=0
for file in ./*.txt; do count=$((count + 1)); done
show "glob loop" "$count files"

# 3. Guard against a dash-leading name with -- or ./
rm -- ./-weird.txt && show "removed" "-weird.txt"

# 4. Build commands in arrays, not strings.
args=(--color=never --almost-all)
cmd=(ls "${args[@]}" -1)
show "array command" "$("${cmd[@]}" | tr '\n' ' ')"

# 5. [[ ]] over [ ]; (( )) for numbers.
var=""
[[ -z $var ]] && show "[[ ]]" "no quoting worries with empty"

# 6. Command substitution: $(...) not backticks; nests cleanly.
show "nesting" "$(basename "$(dirname "/a/b/c")")"

# 7. read -r, IFS= for raw lines.
printf '  keep leading\n' | { IFS= read -r line; show "raw read" "[$line]"; }

# 8. printf, not echo, for data.
s='-n'; show "printf safe" "$(printf '%s' "$s")"

# 9. Variables: lowercase locals, UPPERCASE exports/constants, readonly.
readonly VERSION="1.2.3"
( VERSION=2 ) 2>&1 | sed 's/^.*: //' || true
show "constant" "$VERSION"

# 10. Do not use `cat file | cmd`, `echo $var | cmd`, or `ls | grep`.
printf 'x\n' > one.txt
show "redirect" "$(wc -l < one.txt | tr -d ' ')"
show "here-string" "$(tr a-z A-Z <<< "$f")"

# 11. Functions + main; source-safe entry point.
main() { show "main" "ran with $# args"; }
if [[ ${BASH_SOURCE[0]} == "$0" ]]; then main "$@"; fi

# 12. Cleanup with trap, temp files with mktemp (done above).
# 13. Use `local` and check substitutions separately.
f2() {
  local out
  out=$(printf 'value')                       # failure would propagate
  echo "$out"
}
show "local then assign" "$(f2)"

# 14. Prefer built-ins to forks in hot loops.
path=/a/b/c.txt
show "no fork" "${path##*/} vs $(basename "$path")"

# 15. A dependency check up front.
require() { command -v "$1" >/dev/null || { echo "missing: $1" >&2; return 1; }; }
require bash && show "dependency" "bash found"
require not-a-real-tool 2>&1 || true
```

```text output
unquoted: ls: cannot access 'a': No such
quoted: a b.txt
glob loop: 3 files
removed: -weird.txt
array command: a b.txt c.txt 
[[ ]]: no quoting worries with empty
nesting: b
raw read: [  keep leading]
printf safe: -n
readonly variable
constant: 1.2.3
redirect: 1
here-string: A B.TXT
main: ran with 0 args
local then assign: value
no fork: c.txt vs c.txt
dependency: bash found
missing: not-a-real-tool
```

## The checklist

1. `#!/usr/bin/env bash` and `set -euo pipefail`; know what each does and
   when to loosen it (lesson 07).
2. Quote all expansions; use arrays for lists; `"$@"` for passthrough.
3. `[[ ]]` and `(( ))` in bash; `[ ]` only in portable `sh`.
4. `$(...)`, never backticks.
5. `printf` for data, `echo` for fixed messages.
6. `local` for every function variable; `readonly` for constants.
7. `mktemp` + `trap EXIT` for anything temporary.
8. Errors to stderr, data to stdout, meaningful exit codes.
9. Prefer built-in parameter expansion to forking `sed`/`awk`/`basename`.
10. Run [`shellcheck`](https://www.shellcheck.net/) on every script; it
    knows these rules (SC2086 is "quote this"). Run `shfmt` for layout.
11. If a script passes ~200 lines, needs real data structures, or parses
    structured data, reach for Python or Go instead.

## Details that bite

- ShellCheck cannot know your data. It flags the *pattern*; you decide
  whether the file name might contain spaces.
- `set -e` interacts with functions and `if` in surprising ways: write
  explicit `|| return` / `|| die` on the commands that matter.
- Do not parse `ls`, `ps`, or `df` output when a machine-readable option
  exists (`stat -c`, `ps -o pid=`, `df --output`).
- A script that "works on my machine" often depends on locale, GNU vs BSD
  flags, `$PATH`, the current directory, or a tty. Set `LC_ALL`, check
  tools with `command -v`, resolve paths from `${BASH_SOURCE[0]}`.
- Do not run `sudo` inside scripts you did not write; do not
  `curl ... | bash` anything you have not read.

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
