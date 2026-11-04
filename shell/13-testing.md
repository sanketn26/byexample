# Shell 13 — Testing Shell Code

Shell scripts are code, so test them. You need a way to assert, a way
to call a function without running the whole script, and a way to
replace `curl`, `date`, or `git` with a fake. bats-core and shunit2
add `setup`, `teardown`, and TAP output. The ideas are the ones below.
Run `shellcheck` in CI beside the tests. It catches quoting bugs a
suite rarely hits. Tests must not touch your real home, network, or
clock.

## Assert a pure function with a table

Put the logic in a function. A row is input, a pipe, and the expected
string. `$(f x)` is the actual value. Always test the failure path
too: bad input, a missing file, a non-zero status. Scripts fail there.

```bash file=n01.sh
export LC_ALL=C
pass=0
fail=0
assert_eq() {
  if [[ "$2" == "$3" ]]; then
    pass=$((pass + 1))
    echo "ok   $1"
  else
    fail=$((fail + 1))
    echo "FAIL $1"
    echo "     want: $2"
    echo "     got:  $3"
  fi
}
shopt -s extglob
slugify() {
  local s=${1,,}
  s=${s//[^a-z0-9]/-}
  s=${s//+(-)/-}
  s=${s#-}
  echo "${s%-}"
}
cases=(
  "Hello, World!|hello-world"
  "  Many   spaces |many-spaces"
  "ALREADY-slug|already-slug"
)
for c in "${cases[@]}"; do
  assert_eq "slugify '${c%|*}'" "${c#*|}" "$(slugify "${c%|*}")"
done
echo "$pass passed, $fail failed"
exit $(( fail > 0 ))
```

```text output
ok   slugify 'Hello, World!'
ok   slugify '  Many   spaces '
ok   slugify 'ALREADY-slug'
3 passed, 0 failed
```

## Assert stdout and the exit status

`assert_status` throws away both streams and compares `$?`. A parser
that prints on success and returns 1 on junk needs both checks.

```bash file=n02.sh
export LC_ALL=C
pass=0
fail=0
assert_eq() {
  if [[ "$2" == "$3" ]]; then pass=$((pass + 1)); echo "ok   $1"
  else fail=$((fail + 1)); echo "FAIL $1"; echo "     want: $2"; echo "     got:  $3"; fi
}
assert_status() {
  local name=$1 want=$2 got=0
  shift 2
  "$@" >/dev/null 2>&1 || got=$?
  assert_eq "$name" "$want" "$got"
}
parse_version() {
  [[ $1 =~ ^v?([0-9]+)\.([0-9]+)\.([0-9]+)$ ]] || return 1
  echo "${BASH_REMATCH[1]} ${BASH_REMATCH[2]} ${BASH_REMATCH[3]}"
}
assert_eq "parse ok" "1 22 3" "$(parse_version v1.22.3)"
assert_status "parse rejects junk" 1 parse_version 1.2
assert_status "parse accepts plain" 0 parse_version 1.2.3
echo "$pass passed, $fail failed"
exit $(( fail > 0 ))
```

```text output
ok   parse ok
ok   parse rejects junk
ok   parse accepts plain
3 passed, 0 failed
```

## A function overrides an external command

Functions win over programs on `PATH`, in this shell only. The test
needs no network and no repository. A child script (`bash other.sh`)
does not see the function unless you `export -f` it.

```bash file=n03.sh
export LC_ALL=C
pass=0
fail=0
assert_eq() {
  if [[ "$2" == "$3" ]]; then pass=$((pass + 1)); echo "ok   $1"
  else fail=$((fail + 1)); echo "FAIL $1"; echo "     want: $2"; echo "     got:  $3"; fi
}
latest_tag() { git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0"; }
release_name() { echo "release-$(latest_tag)-$(date +%Y)"; }
git()  { echo "v9.9.9"; }
date() { echo "2000"; }
assert_eq "release name (faked git+date)" "release-v9.9.9-2000" "$(release_name)"
unset -f git date
echo "$pass passed, $fail failed"
exit $(( fail > 0 ))
```

```text output
ok   release name (faked git+date)
1 passed, 0 failed
```

## `export -f` hands a fake to a child bash

The child is a new shell. It does not inherit functions. `export -f`
is the exception. A program that is not bash still needs a real
executable on `PATH`.

```bash file=n04.sh
hi() { echo "hello from $1"; }
export -f hi
bash -c 'hi child'
```

```text output
hello from child
```

## A `PATH` shim fakes a program the child execs

Put a tiny executable earlier on `PATH` than the real one. The child
script finds that file. Remember to delete the directory. `mktemp -d`
is the working directory, not your home.

```bash file=n05.sh
export LC_ALL=C
pass=0
fail=0
assert_eq() {
  if [[ "$2" == "$3" ]]; then pass=$((pass + 1)); echo "ok   $1"
  else fail=$((fail + 1)); echo "FAIL $1"; echo "     want: $2"; echo "     got:  $3"; fi
}
assert_status() {
  local name=$1 want=$2 got=0
  shift 2
  "$@" >/dev/null 2>&1 || got=$?
  assert_eq "$name" "$want" "$got"
}
shim=$(mktemp -d)
trap 'rm -rf "$shim"' EXIT
printf '#!/bin/sh\necho "fake-curl called with: $*"\nexit 22\n' > "$shim/curl"
chmod +x "$shim/curl"
download() { curl -fsS "$1"; }
out=$(PATH="$shim:$PATH" download http://x.invalid/a || true)
assert_eq "PATH shim" "fake-curl called with: -fsS http://x.invalid/a" "$out"
assert_status "propagates failure" 22 env PATH="$shim:$PATH" bash -c 'curl -f http://x'
echo "$pass passed, $fail failed"
exit $(( fail > 0 ))
```

```text output
ok   PATH shim
ok   propagates failure
2 passed, 0 failed
```

## A golden file is saved output

`diff -u` is the assertion. Sort first when the command's order is
not a promise.

```bash file=n06.sh
export LC_ALL=C
pass=0
fail=0
assert_eq() {
  if [[ "$2" == "$3" ]]; then pass=$((pass + 1)); echo "ok   $1"
  else fail=$((fail + 1)); echo "FAIL $1"; echo "     want: $2"; echo "     got:  $3"; fi
}
shim=$(mktemp -d)
trap 'rm -rf "$shim"' EXIT
printf 'b 2\na 1\n' | sort > "$shim/actual"
printf 'a 1\nb 2\n' > "$shim/golden"
if diff -u "$shim/golden" "$shim/actual" >/dev/null; then
  assert_eq "golden" same same
else
  assert_eq "golden" same different
fi
echo "$pass passed, $fail failed"
exit $(( fail > 0 ))
```

```text output
ok   golden
1 passed, 0 failed
```

## Run the script as a black box

Write it to a temp path, `chmod +x`, and call it. Check stdout, the
status, and stderr separately. Usage text on stderr is part of the
contract.

```bash file=n07.sh
export LC_ALL=C
pass=0
fail=0
assert_eq() {
  if [[ "$2" == "$3" ]]; then pass=$((pass + 1)); echo "ok   $1"
  else fail=$((fail + 1)); echo "FAIL $1"; echo "     want: $2"; echo "     got:  $3"; fi
}
assert_status() {
  local name=$1 want=$2 got=0
  shift 2
  "$@" >/dev/null 2>&1 || got=$?
  assert_eq "$name" "$want" "$got"
}
shim=$(mktemp -d)
trap 'rm -rf "$shim"' EXIT
cat > "$shim/greet" <<'EOF'
#!/usr/bin/env bash
[[ $# -eq 1 ]] || { echo "usage: greet NAME" >&2; exit 2; }
echo "hi $1"
EOF
chmod +x "$shim/greet"
assert_eq "script output" "hi Ada" "$("$shim/greet" Ada)"
assert_status "script usage error" 2 "$shim/greet"
assert_eq "script stderr" "usage: greet NAME" "$("$shim/greet" 2>&1 >/dev/null || true)"
echo "$pass passed, $fail failed"
exit $(( fail > 0 ))
```

```text output
ok   script output
ok   script usage error
ok   script stderr
3 passed, 0 failed
```

## Source the file; do not run `main`

Guard the entry point with `[[ ${BASH_SOURCE[0]} == "$0" ]]`. A test
then sources the script and calls one function. The CI status is the
script's exit status: non-zero when any assertion failed.

```bash file=n08.sh
tmp=$(mktemp -d)
cat > "$tmp/lib.sh" << 'EOF'
slug() { echo "ok-$1"; }
main() { echo "ran main"; }
if [[ ${BASH_SOURCE[0]} == "$0" ]]; then main "$@"; fi
EOF
source "$tmp/lib.sh"
echo "called $(slug ada)"
```

```text output
called ok-ada
```

## A global has to be asserted in this shell

`$(f)` runs `f` in a subshell. An assignment inside it never reaches
the assertion. Call `f`, then look at the variable.

```bash file=n09.sh
set_count() { COUNT=4; }
COUNT=0
set_count
echo "same shell $COUNT"
COUNT=0
echo "$(set_count)" >/dev/null
echo "inside capture $COUNT"
```

```text output
same shell 4
inside capture 0
```

## Exercises

```bash file=exercise.sh
#!/usr/bin/env bash
export LC_ALL=C
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

# Code under test: needs `date` and `uname`.
banner() { echo "built $(date +%Y-%m-%d) on $(uname -s)"; }

# Echo the banner with `date` and `uname` replaced by fakes that print
# 2020-01-02 and Plan9. Do not change banner(); fake the commands
# (functions are fine) in a way that does not leak out of this function.
test_banner() {
  banner  # TODO
}

# Code under test: calls the external tool `wc`.
count_in_file() { wc -l < "$1" | tr -d ' '; }

# Return (echo) the result of count_in_file when `wc` is replaced by a PATH
# shim script that prints 999. Clean the shim up afterwards.
with_fake_wc() {
  count_in_file /dev/null  # TODO
}

# Write assert_contains NAME NEEDLE HAYSTACK that echoes "ok NAME" when
# HAYSTACK contains NEEDLE, and "FAIL NAME" otherwise; always return 0.
assert_contains() {
  :  # TODO
}

check "fake date/uname" "$(test_banner)" "built 2020-01-02 on Plan9"
check "real still works" "$(banner | cut -c1-6)" "built "
check "wc shim" "$(with_fake_wc)" "999"
check "real wc restored" "$(count_in_file /dev/null)" "0"
check "contains yes" "$(assert_contains t foo 'a food b')" "ok t"
check "contains no" "$(assert_contains t zzz 'a food b')" "FAIL t"
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

banner() { echo "built $(date +%Y-%m-%d) on $(uname -s)"; }

test_banner() {
  # a subshell keeps the fakes from leaking
  (
    date()  { echo 2020-01-02; }
    uname() { echo Plan9; }
    banner
  )
}

count_in_file() { wc -l < "$1" | tr -d ' '; }

with_fake_wc() {
  local shim
  shim=$(mktemp -d)
  printf '#!/bin/sh\necho 999\n' > "$shim/wc"
  chmod +x "$shim/wc"
  PATH="$shim:$PATH" count_in_file /dev/null
  rm -rf "$shim"
}

assert_contains() {
  if [[ $3 == *"$2"* ]]; then echo "ok $1"; else echo "FAIL $1"; fi
  return 0
}

check "fake date/uname" "$(test_banner)" "built 2020-01-02 on Plan9"
check "real still works" "$(banner | cut -c1-6)" "built "
check "wc shim" "$(with_fake_wc)" "999"
check "real wc restored" "$(count_in_file /dev/null)" "0"
check "contains yes" "$(assert_contains t foo 'a food b')" "ok t"
check "contains no" "$(assert_contains t zzz 'a food b')" "FAIL t"
exit $failed
```

</details>

Next: [14 — Capstone: log analyzer](14-capstone-logstat.md)
