# Shell 10 — Files, Globs and find

Files are where scripts spend their lives: create, search, move, check
permissions, and do it safely when names contain spaces or newlines.

## Example

```bash file=example.sh
#!/usr/bin/env bash
export LC_ALL=C
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
umask 022

mkdir -p src/lib docs
printf 'int main(){}\n'  > src/main.c
printf 'void f();\n'     > src/lib/util.h
printf '# Title\n'       > docs/readme.md
printf 'two words\n'     > "my notes.txt"
touch .hidden

# Globs: expanded by the shell BEFORE the command sees them
echo *.txt                         # one file with a space: still ONE argument
printf '[%s]\n' *.txt
echo src/*                         # a directory's entries
echo *.nothing                     # no match: the pattern itself (a trap!)
shopt -s nullglob; echo *.nothing "[end]"; shopt -u nullglob
shopt -s globstar; ls src/**/*.h; shopt -u globstar
echo .h*                           # dotfiles need an explicit dot

# Tests: -e exists, -f file, -d dir, -r/-w/-x access, -s non-empty, -L link
[[ -f src/main.c ]]  && echo "regular file"
[[ -s .hidden ]]     || echo ".hidden is empty"
ln -s src/main.c link.c
[[ -L link.c ]]      && echo "symlink -> $(readlink link.c)"

# find: walk a tree and filter by name, type, size, age, perms
# symlinks match by name too (link.c)
find . -name '*.c' -o -name '*.h' | sort
find . -type f -name '*.md'
find . -maxdepth 1 -type d | sort
find . -type f -empty
find . -type f -size -1k | wc -l

# -exec ... {} + batches many files into one command; -print0 is NUL-safe
find . -type f -name '*.c' -exec wc -l {} +
find src -type f -print0 | sort -z | xargs -0 -n1 basename

# Reading NUL-delimited names is the only fully safe loop over find output
while IFS= read -r -d '' f; do printf 'file: %s\n' "$f"; done \
  < <(find . -name '*.txt' -print0)

# stat, wc, file metadata
stat -c '%s bytes, mode %a' src/main.c
chmod 600 src/main.c; stat -c '%a' src/main.c
chmod u+x src/main.c;  stat -c '%A' src/main.c

# Copy, move, remove: and what the flags mean
cp -r src backup                   # -r recurse
mv backup/main.c backup/entry.c
rm -r backup                       # -r recurse; add -f only if you mean it
[[ ! -e backup ]] && echo "backup removed"

# Safe temp files, atomic replace
out=$(mktemp "$tmp/out.XXXXXX")
echo "new content" > "$out"
mv -f "$out" "$tmp/final.txt"      # rename is atomic on the same filesystem
cat final.txt

# basename / dirname / realpath
basename /usr/lib/libc.so .so
dirname /usr/lib/libc.so
realpath -m /a/b/../c
```

```text output
my notes.txt
[my notes.txt]
src/lib src/main.c
*.nothing
[end]
src/lib/util.h
.hidden
regular file
.hidden is empty
symlink -> src/main.c
./link.c
./src/lib/util.h
./src/main.c
./docs/readme.md
.
./docs
./src
./.hidden
1
1 ./src/main.c
util.h
main.c
file: ./my notes.txt
13 bytes, mode 644
600
-rwx------
backup removed
new content
libc
/usr/lib
/a/c
```

## Details that bite

- Always quote variables holding paths: `rm -rf $dir/*` with an empty
  `dir` becomes `rm -rf /*`. Use `"${dir:?}"/*`.
- An unmatched glob stays as the literal text, so `for f in *.txt` can
  run once with `f='*.txt'`. Guard with `[[ -e $f ]]` or `nullglob`.
- Globs do not match dotfiles and do not recurse (unless `globstar`).
- A file name can contain spaces, quotes, `-`, even newlines. A name that
  starts with `-` becomes an *option*: write `rm -- "$f"` or `./"$f"`.
- `find ... -exec cmd {} \;` runs `cmd` once per file; `{} +` batches.
- `find -o` needs parentheses once you add an action:
  `find . \( -name a -o -name b \) -print`.
- `rm` is permanent. Dry-run first: replace `rm` with `echo rm`.
- `cp`, `mv`, `stat`, `date` and `sed -i` flags differ between GNU and
  BSD/macOS. The examples here are GNU. For scripts that must run on both,
  stick to POSIX options or check `uname`.
- `mv` within one filesystem is an atomic rename; across filesystems it is
  copy + delete.

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
mkdir -p a/b c
echo 1 > a/x.log; echo 2 > a/b/y.log; echo 3 > c/z.txt; : > "a/odd name.log"

# Echo the relative paths (./...) of all *.log files under $1, sorted,
# one per line, safe for names with spaces.
list_logs() { echo ""; }       # TODO

# Echo how many regular files live under $1 (any depth).
count_files() { echo 0; }      # TODO

# Echo the total number of lines across all *.log files under $1.
total_lines() { echo 0; }      # TODO

# Create a backup of file $1 named $1.bak, but only if it does not exist
# yet. Return 0 if created, 1 if it already existed. Never overwrite.
backup_once() { return 1; }    # TODO

# Atomically write stdin to file $1 (temp file in the same directory, then mv).
write_atomic() { cat > /dev/null; }   # TODO

check "list_logs" "$(cd a && list_logs . | tr '\n' ';')" "./b/y.log;./odd name.log;./x.log;"
check "count_files" "$(count_files .)" "4"
check "total_lines" "$(total_lines .)" "2"
backup_once c/z.txt; check "backup 1st" "$?" "0"
echo changed > c/z.txt.bak.expected
backup_once c/z.txt; check "backup 2nd" "$?" "1"
check "backup content" "$(cat c/z.txt.bak)" "3"
echo new | write_atomic c/out; check "atomic" "$(cat c/out)" "new"
check "no temp left" "$(ls c | grep -c tmp)" "0"
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
mkdir -p a/b c
echo 1 > a/x.log; echo 2 > a/b/y.log; echo 3 > c/z.txt; : > "a/odd name.log"

list_logs() { find "$1" -type f -name '*.log' | sort; }

count_files() { find "$1" -type f | wc -l | tr -d ' '; }

total_lines() {
  find "$1" -type f -name '*.log' -print0 | xargs -0 cat | wc -l | tr -d ' '
}

backup_once() {
  [[ -e $1.bak ]] && return 1
  cp -- "$1" "$1.bak"
}

write_atomic() {
  local tmpf
  tmpf=$(mktemp "$(dirname "$1")/.tmp.XXXXXX") || return
  cat > "$tmpf" && mv -f "$tmpf" "$1"
}

check "list_logs" "$(cd a && list_logs . | tr '\n' ';')" "./b/y.log;./odd name.log;./x.log;"
check "count_files" "$(count_files .)" "4"
check "total_lines" "$(total_lines .)" "2"
backup_once c/z.txt; check "backup 1st" "$?" "0"
echo changed > c/z.txt.bak.expected
backup_once c/z.txt; check "backup 2nd" "$?" "1"
check "backup content" "$(cat c/z.txt.bak)" "3"
echo new | write_atomic c/out; check "atomic" "$(cat c/out)" "new"
check "no temp left" "$(ls c | grep -c tmp)" "0"
exit $failed
```

</details>

Next: [11 — Arguments and scripts](11-arguments.md)
