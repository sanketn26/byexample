# Shell 13 — Testing Shell Code

Shell scripts are code, so test them. You need three things: a way to
assert, a way to call a function without running the whole script, and a
way to replace external commands (`curl`, `date`, `git`) with fakes.

## Example

```bash file=example.sh
#!/usr/bin/env bash
export LC_ALL=C

# ---- A tiny test harness: ~15 lines, no dependencies -------------------
pass=0 fail=0
assert_eq() { # name expected actual
  if [[ "$2" == "$3" ]]; then pass=$((pass + 1)); echo "ok   $1"
  else fail=$((fail + 1)); echo "FAIL $1"; echo "     want: $2"; echo "     got:  $3"; fi
}
assert_status() { # name expected_status command...
  local name=$1 want=$2 got=0; shift 2
  "$@" >/dev/null 2>&1 || got=$?
  assert_eq "$name" "$want" "$got"
}

# ---- Code under test: pure functions plus a thin I/O layer --------------
shopt -s extglob
slugify() { local s=${1,,}; s=${s//[^a-z0-9]/-}; s=${s//+(-)/-}; s=${s#-}; echo "${s%-}"; }
parse_version() {          # "v1.22.3" -> "1 22 3"; fail otherwise
  [[ $1 =~ ^v?([0-9]+)\.([0-9]+)\.([0-9]+)$ ]] || return 1
  echo "${BASH_REMATCH[1]} ${BASH_REMATCH[2]} ${BASH_REMATCH[3]}"
}
latest_tag() { git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0"; }
release_name() { echo "release-$(latest_tag)-$(date +%Y)"; }

# ---- 1. Pure functions: table-driven ------------------------------------
cases=(
  "Hello, World!|hello-world"
  "  Many   spaces |many-spaces"
  "ALREADY-slug|already-slug"
)
for c in "${cases[@]}"; do
  assert_eq "slugify '${c%|*}'" "${c#*|}" "$(slugify "${c%|*}")"
done

# ---- 2. Output and exit status ------------------------------------------
assert_eq "parse ok" "1 22 3" "$(parse_version v1.22.3)"
assert_status "parse rejects junk" 1 parse_version 1.2
assert_status "parse accepts plain" 0 parse_version 1.2.3

# ---- 3. Fakes: override a command with a function -----------------------
# Functions win over external commands, so tests need no network or repo.
git()  { echo "v9.9.9"; }
date() { echo "2000"; }
assert_eq "release name (faked git+date)" "release-v9.9.9-2000" "$(release_name)"
unset -f git date

# ---- 4. Fakes: a PATH shim for scripts that exec other programs ---------
shim=$(mktemp -d); trap 'rm -rf "$shim"' EXIT
printf '#!/bin/sh\necho "fake-curl called with: $*"\nexit 22\n' > "$shim/curl"
chmod +x "$shim/curl"
download() { curl -fsS "$1"; }
out=$(PATH="$shim:$PATH" download http://x.invalid/a || true)
assert_eq "PATH shim" "fake-curl called with: -fsS http://x.invalid/a" "$out"
assert_status "propagates failure" 22 env PATH="$shim:$PATH" bash -c 'curl -f http://x'

# ---- 5. Golden files: compare against saved expected output -------------
printf 'b 2\na 1\n' | sort > "$shim/actual"
printf 'a 1\nb 2\n'          > "$shim/golden"
if diff -u "$shim/golden" "$shim/actual" >/dev/null; then assert_eq "golden" same same
else assert_eq "golden" same different; fi

# ---- 6. Test the script as a black box ----------------------------------
cat > "$shim/greet" <<'EOF'
#!/usr/bin/env bash
[[ $# -eq 1 ]] || { echo "usage: greet NAME" >&2; exit 2; }
echo "hi $1"
EOF
chmod +x "$shim/greet"
assert_eq "script output" "hi Ada" "$("$shim/greet" Ada)"
assert_status "script usage error" 2 "$shim/greet"
assert_eq "script stderr" "usage: greet NAME" "$("$shim/greet" 2>&1 >/dev/null || true)"

# ---- Summary: the exit status is what CI reads --------------------------
echo "$pass passed, $fail failed"
exit $(( fail > 0 ))
```

```text output
ok   slugify 'Hello, World!'
ok   slugify '  Many   spaces '
ok   slugify 'ALREADY-slug'
ok   parse ok
ok   parse rejects junk
ok   parse accepts plain
ok   release name (faked git+date)
ok   PATH shim
ok   propagates failure
ok   golden
ok   script output
ok   script usage error
ok   script stderr
13 passed, 0 failed
```

## Details that bite

- **Make code testable**: put logic in functions, then guard `main` with
  `[[ ${BASH_SOURCE[0]} == "$0" ]] && main "$@"`. A test file can then
  `source script.sh` and call the functions without running anything.
- Functions that *print* a value are easy to test (`$(f x)`); functions that
  set globals need the assertion in the same shell, not in `$(...)`.
- Tests must not touch your real home, network or clock. Fake with
  functions, `PATH` shims, and `mktemp -d` working directories.
- Faking with a function only affects the current shell. A child script
  (`bash other.sh`) needs `export -f name` or a real `PATH` shim.
- Always test the failure paths: bad input, missing file, non-zero status.
  Scripts fail mostly there.
- Run `shellcheck` in CI beside your tests: it catches quoting bugs a test
  suite rarely hits.
- Real frameworks: [bats-core](https://github.com/bats-core/bats-core)
  (`@test "name" { run cmd; [ "$status" -eq 0 ]; }`) and
  [shunit2](https://github.com/kward/shunit2). They add `setup`/`teardown`
  and TAP output; the ideas are the ones above.

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
