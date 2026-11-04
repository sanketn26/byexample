# Shell 15 — Portable POSIX `sh`

Bash is what you get on a machine you control. In containers (Alpine
has BusyBox `ash`), Debian's `/bin/sh` (`dash`), installers, and
Makefiles, you get POSIX `sh`: smaller, and without arrays, `[[ ]]`,
`${var^^}`, `<(...)`, or `==` inside `[ ]`. The shebang decides.
`#!/bin/sh` means POSIX only, even when `/bin/sh` is bash. Bash then
runs in a restricted mode and still accepts bashisms that dash
rejects. Test with `dash` or `busybox sh` before you ship.
`shellcheck -s sh` reports every bashism. If you need arrays, maps, or
non-trivial string handling, require bash (`#!/usr/bin/env bash`) and
say so. Do not contort `sh` to avoid it.

## This `sh` still accepts some bashisms

The checks below call `sh`, the way a `#!/bin/sh` script will. On a
machine whose `sh` is bash, `[[ ]]`, arrays, and `==` still run.
Process substitution and `${var^^}` do not.

```bash file=n01.sh
works() { if sh -c "$1" >/dev/null 2>&1; then echo works; else echo fails; fi; }
echo "[[ ]]:  $(works '[[ -n x ]]')"
echo "arrays: $(works 'a=(1 2); echo ${a[0]}')"
echo "==:     $(works '[ a == a ]')"
echo "<( ):   $(works 'cat <(echo hi)')"
echo "^^:     $(works 'w=hi; echo ${w^^}')"
```

```text output
[[ ]]:  works
arrays: works
==:     works
<( ):   fails
^^:     fails
```

## `dash` rejects those bashisms

`dash` is a strict `sh`. The same five snippets all fail there.
`declare`, `typeset -A`, `mapfile`, `read -a`, and `${!var}` are not
portable either. `local` is not in POSIX, but dash, ash, and bash all
accept it.

```bash file=n02.sh
works() { if dash -c "$1" >/dev/null 2>&1; then echo works; else echo fails; fi; }
echo "[[ ]]:  $(works '[[ -n x ]]')"
echo "arrays: $(works 'a=(1 2); echo ${a[0]}')"
echo "==:     $(works '[ a == a ]')"
echo "<( ):   $(works 'cat <(echo hi)')"
echo "^^:     $(works 'w=hi; echo ${w^^}')"
dash -c 'declare x=1' >/dev/null 2>&1 || echo "declare: fails"
```

```text output
[[ ]]:  fails
arrays: fails
==:     fails
<( ):   fails
^^:     fails
declare: fails
```

## `[ ]` is the POSIX test

Use `=` , not `==`. Combine tests with `&&` and `||`, not `-a` or
`-o`. Quote every expansion. `[ -n $x ]` with an empty `x` is true:
the command becomes `[ -n ]`, which tests the string `-n`.

```bash file=n03.sh
sh -c 'x=""; [ -n $x ] && echo "unquoted is true"; [ -n "$x" ] || echo "quoted is false"'
sh -c 'x=""; if [ -z "$x" ] && [ "$#" -eq 0 ]; then echo "empty and no args"; fi'
```

```text output
unquoted is true
quoted is false
empty and no args
```

## `case` is the portable pattern match

There is no `[[ == glob ]]` and no `=~`. `case` patterns are globs.
The first match wins.

```bash file=n04.sh
sh -c 'f=notes.txt; case $f in *.txt) echo "text file";; *) echo other;; esac'
```

```text output
text file
```

## The positional parameters are the only array

`set --` replaces them. `shift` drops the first. `"$@"` keeps each
argument, spaces included. There is nowhere to store a second list.

```bash file=n05.sh
sh -c 'set -- a "b c" d; for x in "$@"; do printf "<%s>" "$x"; done; echo'
```

```text output
<a><b c><d>
```

## Arithmetic is `$(( ))`

The double-parentheses command `(( ))` is bash. Assignment through
`$(( ))` is POSIX, and the result is text, like everything else.

```bash file=n06.sh
sh -c 'i=0; i=$((i + 1)); echo "i=$i"'
```

```text output
i=1
```

## A few expansions are POSIX

`#`, `##`, `%`, `%%`, `:-`, `:=`, and `:?` are. `^^`, `,,`, `/`,
`//`, and the substring form `${var:offset}` are not. Patterns here
are globs.

```bash file=n07.sh
sh -c 'p=/a/b/c.txt; echo "${p##*/} ${p%/*} ${p%.txt}"'
```

```text output
c.txt /a/b /a/b/c
```

## `printf` is the portable output

`echo -n` and `echo -e` differ per shell. `printf` does not. GNU and
BSD tools matter as much as the shell: `sed -i`, `date -d`, `stat`,
`readlink -f`, `xargs -r`, and `grep -P` are GNU. macOS has the BSD
versions. Stick to POSIX flags, or test on each target.

```bash file=n08.sh
sh -c 'printf "%d items, %s\n" 3 "no echo -n needed"'
```

```text output
3 items, no echo -n needed
```

## `command -v` finds a program

`which` and `type -p` are not the portable check. `command -v` is
silent when you redirect it, and its status is the answer.

```bash file=n09.sh
sh -c 'command -v ls >/dev/null && echo "ls available"'
```

```text output
ls available
```

## A pipe or a here-doc replaces `<(...)`

POSIX `sh` has no process substitution. A pipe, a temp file, or a
here-doc feeds stdin. The `while read` in a pipe still runs in a
subshell, on bash and on dash.

```bash file=n10.sh
sh -c 'printf "b\na\n" | sort | while read -r l; do printf "%s " "$l"; done; echo'
sh -c 'while read -r l; do printf "[%s]" "$l"; done <<EOF
one
two
EOF
echo'
```

```text output
a b 
[one][two]
```

## A function is `name()`

The only portable form is `name() { ...; }`. `local` happens to work
on dash, ash, and bash. Do not depend on it if the script must be
strict POSIX, and do not use `declare`.

```bash file=n11.sh
sh -c 'f() { local v=1; echo "v=$v"; }; f'
```

```text output
v=1
```

## `set -e` and `set -u` are POSIX

`pipefail` was not, before the 2024 revision. This machine's `sh` is
bash, so it accepts `pipefail` and a failing stage fails the
pipeline. dash rejects the option.

```bash file=n12.sh
sh -c 'set -eu; echo strict-ok'
sh -c 'set -o pipefail; false | true; echo "sh pipefail:$?"'
dash -c 'set -o pipefail' >/dev/null 2>&1 || echo "dash: no pipefail"
```

```text output
strict-ok
sh pipefail:1
dash: no pipefail
```

## Compare `sh` with `bash` before you assume

`readlink -f` resolves both names. If they differ, `/bin/sh` is not
your bash, and a script that worked under `bash` can still fail under
`sh`. GNU `readlink -f` is not on every BSD. This host has it.

```bash file=n13.sh
if [ "$(readlink -f "$(command -v sh)")" != "$(readlink -f "$(command -v bash)")" ]; then
  echo "sh is not bash"
fi
```

```text output
sh is not bash
```

## Exercises

```bash file=exercise.sh
#!/usr/bin/env bash
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

# Each snippet below is bash-only. Rewrite it (keep it a string) so that
# it runs correctly under `sh` and prints the same thing.

snippet_upper='w=hello; echo "${w^^}"'                        # TODO (use tr)
snippet_array='a=(x y z); echo "${#a[@]} ${a[1]}"'            # TODO (use set --)
snippet_match='f=a.tar.gz; [[ $f == *.gz ]] && echo gz'       # TODO (use case)
snippet_incr='i=0; (( i++ )); (( i += 2 )); echo "$i"'        # TODO (use $(( )))

run() { sh -c "$1" 2>&1; }

check "upper" "$(run "$snippet_upper")" "HELLO"
check "array" "$(run "$snippet_array")" "3 y"
check "match" "$(run "$snippet_match")" "gz"
check "incr" "$(run "$snippet_incr")" "3"
exit $failed
```

<details><summary>Solution</summary>

```bash file=solution.sh
#!/usr/bin/env bash
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

snippet_upper='w=hello; printf "%s\n" "$w" | tr "[:lower:]" "[:upper:]"'
snippet_array='set -- x y z; echo "$# $2"'
snippet_match='f=a.tar.gz; case $f in *.gz) echo gz;; esac'
snippet_incr='i=0; i=$((i + 1)); i=$((i + 2)); echo "$i"'

run() { sh -c "$1" 2>&1; }

check "upper" "$(run "$snippet_upper")" "HELLO"
check "array" "$(run "$snippet_array")" "3 y"
check "match" "$(run "$snippet_match")" "gz"
check "incr" "$(run "$snippet_incr")" "3"
exit $failed
```

</details>
