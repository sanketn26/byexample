# Shell 11 — Arguments, Options and Real Scripts

A script is a program: it needs a usage message, option parsing, input
validation, sensible exit codes, and a `main`. This lesson turns a bag of
commands into a tool other people can run.

## Example

```bash file=example.sh
#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
usage: tool [-v] [-n COUNT] [-o FILE] [--dry-run] [--] NAME...
  -n COUNT   repeat count (default 1)
  -o FILE    output file (default: stdout)
  -v         verbose
  --dry-run  print what would happen
EOF
}

die() { echo "tool: $*" >&2; exit 2; }

main() {
  local count=1 verbose=0 out="" dry=0

  # getopts handles short options; options with ':' take an argument
  local opt OPTIND=1
  while getopts ":vn:o:h" opt; do
    case $opt in
      v) verbose=1 ;;
      n) count=$OPTARG ;;
      o) out=$OPTARG ;;
      h) usage; return 0 ;;
      :) die "option -$OPTARG needs an argument" ;;
      \?) die "unknown option -$OPTARG" ;;
    esac
  done
  shift $((OPTIND - 1))                  # what is left are the operands

  [[ $count =~ ^[0-9]+$ ]] || die "COUNT must be a number, got '$count'"
  (( $# > 0 )) || die "missing NAME"

  local name i
  for name in "$@"; do
    for ((i = 0; i < count; i++)); do
      (( verbose )) && echo "[verbose] greeting $name ($((i + 1))/$count)" >&2
      echo "hello, $name"
    done
  done > "${out:-/dev/stdout}"
}

# Run the same function with different command lines
main -n 2 Ada
echo "--- verbose, two names"
main -v Ada Linus 2>&1
echo "--- errors"
( main -n abc Ada ) 2>&1 || echo "exit: $?"
( main ) 2>&1 || echo "exit: $?"
( main -z Ada ) 2>&1 || echo "exit: $?"
( main -n ) 2>&1 || echo "exit: $?"

# Hand-rolled loop for long options (getopts has none)
parse_long() {
  local dry=0 files=()
  while (( $# )); do
    case $1 in
      --dry-run)  dry=1 ;;
      --name=*)   files+=("${1#*=}") ;;
      --name)     files+=("$2"); shift ;;
      --)         shift; files+=("$@"); break ;;
      -*)         die "unknown option $1" ;;
      *)          files+=("$1") ;;
    esac
    shift
  done
  echo "dry=$dry files=${files[*]}"
}
parse_long --dry-run --name=a --name b -- -c d

# Environment as configuration, with defaults and a documented override
: "${TOOL_COLOR:=never}"
echo "color: $TOOL_COLOR"
TOOL_COLOR=always bash -c 'echo "child: ${TOOL_COLOR:-unset}"'

# Script location and arguments
script_dir() { cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd; }
[[ -d $(script_dir) ]] && echo "script dir resolved"
echo "args: $# ; name: $(basename "$0")"
```

```text output
hello, Ada
hello, Ada
--- verbose, two names
[verbose] greeting Ada (1/1)
hello, Ada
[verbose] greeting Linus (1/1)
hello, Linus
--- errors
tool: COUNT must be a number, got 'abc'
exit: 2
tool: missing NAME
exit: 2
tool: unknown option -z
exit: 2
tool: option -n needs an argument
exit: 2
dry=1 files=a b -c d
color: never
child: always
script dir resolved
args: 0 ; name: example.sh
```

## Details that bite

- `getopts` is a POSIX builtin: short options only, stops at the first
  non-option, and sets `OPTIND`. Always `shift $((OPTIND - 1))`. Reset
  `OPTIND=1` (and make it `local`) when parsing inside a function.
- The leading `:` in `":vn:o:h"` switches to *silent* mode, where *you*
  handle `\?` (unknown) and `:` (missing argument).
- `getopt` (no `s`) supports long options but differs between GNU and BSD.
  Hand-rolled `case` loops, as above, are the portable answer.
- Support `--` so a file named `-x` can be passed: `tool -- -x`.
- Print usage to **stdout** for `-h` (it is the requested output, exit 0)
  and to **stderr** for errors (exit 2).
- `$0` is how the script was invoked; `${BASH_SOURCE[0]}` is the file even
  when the script is `source`d. Never assume the current directory is the
  script's directory.
- Pick exit codes on purpose and document them: 0 ok, 1 runtime failure,
  2 usage error, plus any domain-specific ones.
- Do not `eval` user input, and do not build commands as strings. Keep
  arguments in arrays and run `"${cmd[@]}"`.

## Exercises

```bash file=exercise.sh
#!/usr/bin/env bash
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

# Parse: -u (uppercase flag), -s SEP (separator, default ","), then operands.
# Echo the operands joined with SEP, uppercased if -u was given.
# Return 2 and print "usage" to stderr on an unknown option.
join_args() {
  echo ""  # TODO
}

# Parse long options --count=N / --count N and --verbose. Echo
# "count=<N> verbose=<0|1> rest=<remaining args space separated>".
parse_flags() {
  echo ""  # TODO
}

# Run the command given as an array in $@ and echo its output
# trimmed of its trailing newline, with each argument passed intact
# (arguments may contain spaces). Prefix the output with "ran: ".
run_quoted() {
  echo ""  # TODO
}

check "join" "$(join_args a b c)" "a,b,c"
check "join sep" "$(join_args -s - a b c)" "a-b-c"
check "join upper" "$(join_args -u -s : x y)" "X:Y"
join_args -q a 2>/dev/null; check "join bad option" "$?" "2"
check "flags" "$(parse_flags --count=3 --verbose a b)" "count=3 verbose=1 rest=a b"
check "flags 2" "$(parse_flags --count 7 x)" "count=7 verbose=0 rest=x"
check "flags --" "$(parse_flags -- --verbose)" "count=1 verbose=0 rest=--verbose"
check "run_quoted" "$(run_quoted printf '[%s]' 'a b' c)" "ran: [a b][c]"
exit $failed
```

<details><summary>Solution</summary>

```bash file=solution.sh
#!/usr/bin/env bash
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

join_args() {
  local upper=0 sep="," opt OPTIND=1
  while getopts ":us:" opt; do
    case $opt in
      u) upper=1 ;;
      s) sep=$OPTARG ;;
      *) echo "usage: join_args [-u] [-s SEP] ARG..." >&2; return 2 ;;
    esac
  done
  shift $((OPTIND - 1))
  local out=$1
  shift
  local a
  for a in "$@"; do out+="$sep$a"; done
  (( upper )) && out=${out^^}
  echo "$out"
}

parse_flags() {
  local count=1 verbose=0
  while (( $# )); do
    case $1 in
      --count=*) count=${1#*=} ;;
      --count)   count=$2; shift ;;
      --verbose) verbose=1 ;;
      --)        shift; break ;;
      *)         break ;;
    esac
    shift
  done
  echo "count=$count verbose=$verbose rest=$*"
}

run_quoted() {
  local out
  out=$("$@")
  echo "ran: $out"
}

check "join" "$(join_args a b c)" "a,b,c"
check "join sep" "$(join_args -s - a b c)" "a-b-c"
check "join upper" "$(join_args -u -s : x y)" "X:Y"
join_args -q a 2>/dev/null; check "join bad option" "$?" "2"
check "flags" "$(parse_flags --count=3 --verbose a b)" "count=3 verbose=1 rest=a b"
check "flags 2" "$(parse_flags --count 7 x)" "count=7 verbose=0 rest=x"
check "flags --" "$(parse_flags -- --verbose)" "count=1 verbose=0 rest=--verbose"
check "run_quoted" "$(run_quoted printf '[%s]' 'a b' c)" "ran: [a b][c]"
exit $failed
```

</details>

Next: [12 — Idiomatic Shell](12-idiomatic-shell.md)
