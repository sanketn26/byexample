# Shell 15 — Portable POSIX `sh`

Bash is everywhere you control the machine. In containers (`alpine` has
BusyBox `ash`), Debian's `/bin/sh` (`dash`), installers and Makefiles, you
get **POSIX `sh`**: smaller, faster, and without arrays, `[[ ]]`, `local`
(officially), `${var^^}`, `<(...)` or `==` in `[ ]`.

## Example

```bash file=example.sh
#!/usr/bin/env bash
# This lesson's example runs small scripts under `sh` (dash on Debian/Ubuntu,
# BusyBox ash on Alpine) and shows what breaks and what the portable form is.

run_sh() { sh -c "$1" 2>&1; }
works()  { if sh -c "$1" >/dev/null 2>&1; then echo works; else echo "fails"; fi; }

echo "--- bashisms that fail in dash/ash (bash-as-sh may accept them)"
echo "[[ ]]:  $(works '[[ -n x ]]')"
echo "arrays: $(works 'a=(1 2); echo ${a[0]}')"
echo "==:     $(works '[ a == a ]')"
echo "<( ):   $(works 'cat <(echo hi)')"
echo "^^:     $(works 'w=hi; echo ${w^^}')"

echo "--- portable replacements"
# 1. Tests: [ ] with = and quoting; combine with && and ||, not -a / -o
run_sh 'x=""; if [ -z "$x" ] && [ "$#" -eq 0 ]; then echo "empty and no args"; fi'

# 2. case instead of [[ == glob ]] / =~
run_sh 'f=notes.txt; case $f in *.txt) echo "text file";; *) echo other;; esac'

# 3. Positional parameters are the only array: set --, shift, "$@"
run_sh 'set -- a "b c" d; for x in "$@"; do printf "<%s>" "$x"; done; echo'

# 4. Arithmetic: $(( )) works; (( )) does not
run_sh 'i=0; i=$((i + 1)); echo "i=$i"'

# 5. Parameter expansion: # ## % %% :- := :? are POSIX; ^^ ,, / // : are not
run_sh 'p=/a/b/c.txt; echo "${p##*/} ${p%/*} ${p%.txt}"'

# 6. printf, not echo -n / echo -e
run_sh 'printf "%d items, %s\n" 3 "no echo -n needed"'

# 7. command -v, not which or type -p
run_sh 'command -v ls >/dev/null && echo "ls available"'

# 8. No process substitution: use a pipe, a temp file, or a here-doc
run_sh 'printf "b\na\n" | sort | while read -r l; do printf "%s " "$l"; done; echo'
run_sh 'while read -r l; do printf "[%s]" "$l"; done <<EOF
one
two
EOF
echo'

# 9. Functions: name() { ...; } only; `local` is accepted by dash, ash and
#    bash, though it is not strictly POSIX.
run_sh 'f() { local v=1; echo "v=$v"; }; f'

# 10. set -e / -u work; pipefail does not exist in POSIX sh (before 2024).
run_sh 'set -eu; echo strict-ok'

echo "--- which shell is sh here?"
if [ "$(readlink -f "$(command -v sh)")" != "$(readlink -f "$(command -v bash)")" ]; then
  echo "sh is not bash"
fi
```

```text output
--- bashisms that fail in dash/ash (bash-as-sh may accept them)
[[ ]]:  fails
arrays: fails
==:     fails
<( ):   fails
^^:     fails
--- portable replacements
empty and no args
text file
<a><b c><d>
i=1
c.txt /a/b /a/b/c
3 items, no echo -n needed
ls available
a b 
[one][two]
v=1
strict-ok
--- which shell is sh here?
sh is not bash
```

## Details that bite

- **Shebang decides the shell**: `#!/bin/sh` means POSIX only, even if
  `/bin/sh` is bash on your machine (it then runs in a restricted mode, but
  still accepts bashisms that dash will reject). Test with `dash` or
  `busybox sh` before shipping.
- `shellcheck -s sh script.sh` reports every bashism for you.
- `local` is not in POSIX, yet every real `sh` accepts it. `declare`,
  `typeset -A`, `mapfile`, `read -a` and `${!var}` are not portable.
- `echo` flags and escape handling differ per shell. `printf` does not.
- GNU vs BSD tools matter as much as the shell: `sed -i`, `date -d`,
  `stat`, `readlink -f`, `xargs -r`, `grep -P` are GNU. macOS has BSD
  versions. Stick to POSIX flags or test on each target.
- Use `[ ]` carefully: `[ -n $x ]` with empty `x` is *true* (it tests the
  string `-n`). Always quote: `[ -n "$x" ]`.
- Decide per script: if you need arrays, associative maps, or non-trivial
  string handling, require bash (`#!/usr/bin/env bash`) and say so. Do not
  contort `sh` code to avoid it.

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
