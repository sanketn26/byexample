# Shell 10 — Files, Globs and find

Files are where scripts spend their lives: create, search, move, and
check permissions, including when a name contains spaces or newlines.

## The shell expands globs before the command

An unmatched glob stays as the literal text, so `for f in *.txt` can
run once with `f='*.txt'`. Guard with `[[ -e $f ]]` or `nullglob`.
`*` skips dotfiles and does not recurse. `shopt -s globstar` makes
`**` recurse. Quote a path. `rm -rf $dir/*` with an empty `dir`
becomes `rm -rf /*`. Write `"${dir:?}"/*`.

```bash file=n01.sh
export LC_ALL=C
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
mkdir -p src/lib docs
printf 'int main(){}\n' > src/main.c
printf 'void f();\n' > src/lib/util.h
printf '# Title\n' > docs/readme.md
printf 'two words\n' > "my notes.txt"
touch .hidden
echo *.txt
printf '[%s]\n' *.txt
echo src/*
echo *.nothing
shopt -s nullglob
echo *.nothing "[end]"
shopt -u nullglob
shopt -s globstar
ls src/**/*.h
shopt -u globstar
echo .h*
```

```text output
my notes.txt
[my notes.txt]
src/lib src/main.c
*.nothing
[end]
src/lib/util.h
.hidden
```

## Test the path before you use it

`-e` exists, `-f` is a regular file, `-d` is a directory, `-r` `-w`
`-x` are access, `-s` is non-empty, `-L` is a symlink. `readlink`
prints the target. It does not tell you the target exists.

```bash file=n02.sh
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
mkdir -p src
printf 'int main(){}\n' > src/main.c
touch .hidden
[[ -f src/main.c ]] && echo "regular file"
[[ -s .hidden ]] || echo ".hidden is empty"
ln -s src/main.c link.c
[[ -L link.c ]] && echo "symlink -> $(readlink link.c)"
```

```text output
regular file
.hidden is empty
symlink -> src/main.c
```

## A leading `-` is an option

`rm -- "$f"` or `./"$f"` stops the name from being read as a flag.
The same `--` ends options for `touch` and `ls`.

```bash file=n03.sh
tmp=$(mktemp -d)
cd "$tmp"
touch -- "a b.txt" "-weird.txt"
rm -- ./-weird.txt
[[ ! -e ./-weird.txt ]] && echo "removed -weird.txt"
printf '<%s>\n' ./*
```

```text output
removed -weird.txt
<./a b.txt>
```

## `find` walks a tree and filters it

`-name` is a glob. `-type f` is a regular file. `-maxdepth` stops the
walk. `-empty` is zero bytes. `-size -1024c` is "smaller than 1024
bytes" on both GNU and BSD find. `-size -1k` is in 1 KiB units, and
GNU rounds a file up to the next unit, so there `-1k` matches only
empty files. `rm` is permanent. Dry-run first: replace `rm` with
`echo rm`.

```bash file=n04.sh
export LC_ALL=C
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
umask 022
mkdir -p src/lib docs
printf 'int main(){}\n' > src/main.c
printf 'void f();\n' > src/lib/util.h
printf '# Title\n' > docs/readme.md
printf 'two words\n' > "my notes.txt"
touch .hidden
ln -s src/main.c link.c
find . -name '*.c' -o -name '*.h' | sort
find . -type f -name '*.md'
find . -maxdepth 1 -type d | sort
find . -type f -empty
echo "$(( $(find . -type f -size -1024c | wc -l) ))"
```

```text output
./link.c
./src/lib/util.h
./src/main.c
./docs/readme.md
.
./docs
./src
./.hidden
5
```

## `find -o` binds an action to one side

Once you add `-print` or `-exec`, parentheses group the tests:
`find . \( -name a -o -name b \) -print`. Without them, `-print`
applies only to the right-hand test.

```bash file=n05.sh
export LC_ALL=C
tmp=$(mktemp -d)
cd "$tmp"
mkdir -p src/lib
touch src/main.c src/lib/util.h link.c
echo "no parens:"
find . -name '*.c' -o -name '*.h' -print | sort
echo "parens:"
find . \( -name '*.c' -o -name '*.h' \) -print | sort
```

```text output
no parens:
./src/lib/util.h
parens:
./link.c
./src/lib/util.h
./src/main.c
```

## `-exec {} +` batches; `-print0` is NUL-safe

`{} \;` runs the command once per file. `{} +` packs many paths into
one command. A name can contain spaces, quotes, newlines, or a
leading dash. NUL is the only separator that cannot appear in a name.
`sort -z` and `xargs -0` keep that separator.

```bash file=n06.sh
export LC_ALL=C
tmp=$(mktemp -d)
cd "$tmp"
mkdir -p src/lib
printf 'int main(){}\n' > src/main.c
printf 'void f();\n' > src/lib/util.h
find . -type f -name '*.c' -exec wc -l {} + | awk '{ print $1, $2 }'
find src -type f -print0 | sort -z | xargs -0 -n1 basename
```

```text output
1 ./src/main.c
util.h
main.c
```

## Read `find -print0` with `read -d ''`

This is the only fully safe loop over `find` output. `IFS=` and `-r`
matter here too: the name is data, not words.

```bash file=n07.sh
tmp=$(mktemp -d)
cd "$tmp"
printf 'two words\n' > "my notes.txt"
while IFS= read -r -d '' f; do
  printf 'file: %s\n' "$f"
done < <(find . -name '*.txt' -print0)
```

```text output
file: ./my notes.txt
```

## `stat` reports size and mode

`cp`, `mv`, `stat`, `date`, and `sed -i` flags differ between GNU and
BSD. GNU `stat -c` and BSD `stat -f` can print the same facts. `mv`
inside one filesystem is an atomic rename. Across filesystems it is
copy plus delete.

```bash file=n08.sh
tmp=$(mktemp -d)
cd "$tmp"
umask 022
mkdir -p src
printf 'int main(){}\n' > src/main.c
if stat -c '%a' src/main.c >/dev/null 2>&1; then
  stat -c '%s bytes, mode %a' src/main.c
  chmod 600 src/main.c
  stat -c '%a' src/main.c
  chmod u+x src/main.c
  stat -c '%A' src/main.c
else
  stat -f '%z bytes, mode %Lp' src/main.c
  chmod 600 src/main.c
  stat -f '%Lp' src/main.c
  chmod u+x src/main.c
  stat -f '%Sp' src/main.c
fi
```

```text output
13 bytes, mode 644
600
-rwx------
```

## Copy, move, then remove

`cp -r` recurses. `rm -r` recurses. Add `-f` only when you mean to
ignore a missing target.

```bash file=n09.sh
tmp=$(mktemp -d)
cd "$tmp"
mkdir -p src
printf 'int main(){}\n' > src/main.c
cp -r src backup
mv backup/main.c backup/entry.c
rm -r backup
[[ ! -e backup ]] && echo "backup removed"
```

```text output
backup removed
```

## Rename into place in the same directory

Write the temp file beside the destination, then `mv -f`. Readers
never see a half-written target. The name from `mktemp` is unique.

```bash file=n10.sh
tmp=$(mktemp -d)
cd "$tmp"
out=$(mktemp "$tmp/out.XXXXXX")
echo "new content" > "$out"
mv -f "$out" "$tmp/final.txt"
cat final.txt
```

```text output
new content
```

## `basename`, `dirname`, and `realpath`

`basename` can also strip a suffix. GNU `realpath -m` canonicalizes a
path that does not exist. BSD `realpath` has no `-m`. `grealpath`
from coreutils is that flag when the system one lacks it.

```bash file=n11.sh
basename /usr/lib/libc.so .so
dirname /usr/lib/libc.so
if realpath -m /a/b/../c >/dev/null 2>&1; then
  realpath -m /a/b/../c
else
  grealpath -m /a/b/../c
fi
```

```text output
libc
/usr/lib
/a/c
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
