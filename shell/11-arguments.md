# Shell 11 — Arguments, Options and Real Scripts

A script is a program. It needs a usage message, option parsing, input
validation, sensible exit codes, and a `main`. `getopts` is the POSIX
builtin for short options. It stops at the first non-option. Reset
`OPTIND=1` (and make it `local`) when you parse inside a function,
then `shift $((OPTIND - 1))`.

## `getopts` reads short options

A trailing colon on an option means it takes an argument (`n:`). The
leading colon in the spec is silent mode: you handle unknown options
and missing arguments yourself. `getopt` without the `s` understands
long options, but GNU and BSD disagree. A `case` loop is the portable
long-option parser.

```bash file=n01.sh
set -euo pipefail
main() {
  local count=1 verbose=0
  local opt OPTIND=1
  while getopts ":vn:" opt; do
    case $opt in
      v) verbose=1 ;;
      n) count=$OPTARG ;;
      \?) echo "tool: unknown option -$OPTARG" >&2; return 2 ;;
    esac
  done
  shift $((OPTIND - 1))
  local name i
  for name in "$@"; do
    for ((i = 0; i < count; i++)); do
      (( verbose )) && echo "[verbose] greeting $name ($((i + 1))/$count)" >&2
      echo "hello, $name"
    done
  done
}
main -n 2 Ada
echo "--- verbose, two names"
main -v Ada Linus
```

```text output
hello, Ada
hello, Ada
--- verbose, two names
[verbose] greeting Ada (1/1)
hello, Ada
[verbose] greeting Linus (1/1)
hello, Linus
```

## Usage is stdout; a usage error is stderr

`-h` is the output the user asked for, so it goes to stdout and exits
0. A bad option, a missing option argument, a bad value, or a missing
operand goes to stderr and exits 2. Document the codes: 0 ok, 1
runtime failure, 2 usage error.

```bash file=n02.sh
set -euo pipefail
usage() { echo "usage: tool [-v] [-n COUNT] [-o FILE] [--] NAME..."; }
die() { echo "tool: $*" >&2; exit 2; }
main() {
  local count=1 opt OPTIND=1
  while getopts ":vn:h" opt; do
    case $opt in
      v) ;;
      n) count=$OPTARG ;;
      h) usage; return 0 ;;
      :) die "option -$OPTARG needs an argument" ;;
      \?) die "unknown option -$OPTARG" ;;
    esac
  done
  shift $((OPTIND - 1))
  [[ $count =~ ^[0-9]+$ ]] || die "COUNT must be a number, got '$count'"
  (( $# > 0 )) || die "missing NAME"
  echo "ok $count $*"
}
main -h
echo "--- errors"
( main -n abc Ada ) 2>&1 || echo "exit: $?"
( main ) 2>&1 || echo "exit: $?"
( main -z Ada ) 2>&1 || echo "exit: $?"
( main -n ) 2>&1 || echo "exit: $?"
```

```text output
usage: tool [-v] [-n COUNT] [-o FILE] [--] NAME...
--- errors
tool: COUNT must be a number, got 'abc'
exit: 2
tool: missing NAME
exit: 2
tool: unknown option -z
exit: 2
tool: option -n needs an argument
exit: 2
```

## Long options are a `case` loop

`--name=value` and `--name value` are both worth accepting. A bare
`--` ends the options, so a file named `-x` can be an operand:
`tool -- -x`.

```bash file=n03.sh
set -euo pipefail
die() { echo "tool: $*" >&2; exit 2; }
parse_long() {
  local dry=0 files=()
  while (( $# )); do
    case $1 in
      --dry-run) dry=1 ;;
      --name=*)  files+=("${1#*=}") ;;
      --name)    files+=("$2"); shift ;;
      --)        shift; files+=("$@"); break ;;
      -*)        die "unknown option $1" ;;
      *)         files+=("$1") ;;
    esac
    shift
  done
  echo "dry=$dry files=${files[*]}"
}
parse_long --dry-run --name=a --name b -- -c d
```

```text output
dry=1 files=a b -c d
```

## The environment is configuration

`${TOOL_COLOR:=never}` sets a default without overriding a value the
caller already exported. The child sees the exported value, not your
default.

```bash file=n04.sh
: "${TOOL_COLOR:=never}"
echo "color: $TOOL_COLOR"
TOOL_COLOR=always bash -c 'echo "child: ${TOOL_COLOR:-unset}"'
```

```text output
color: never
child: always
```

## `$0` is how you were started

`${BASH_SOURCE[0]}` is this file, even when the file is sourced.
Never assume the current directory is the script's directory. `cd`
to `dirname` of `BASH_SOURCE` and `pwd` if you need that directory.

```bash file=n05.sh
tmp=$(mktemp -d)
cat > "$tmp/lib.sh" << 'EOF'
echo "dollar0=$(basename "$0")"
echo "source=$(basename "${BASH_SOURCE[0]}")"
EOF
echo "executed:"
bash "$tmp/lib.sh"
echo "sourced:"
source "$tmp/lib.sh"
script_dir() { cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd; }
[[ -d $(script_dir) ]] && echo "script dir resolved"
echo "name: $(basename "$0")"
```

```text output
executed:
dollar0=lib.sh
source=lib.sh
sourced:
dollar0=n05.sh
source=lib.sh
script dir resolved
name: n05.sh
```

## Keep commands in arrays, never in `eval`

Do not build a command as a string, and do not `eval` user input.
`"$@"` and `"${cmd[@]}"` pass each argument through intact, spaces
included.

```bash file=n06.sh
cmd=(printf '<%s>' 'a b' c)
"${cmd[@]}"
echo
```

```text output
<a b><c>
```

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
