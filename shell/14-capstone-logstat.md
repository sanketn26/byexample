# Shell 14 — Capstone: `logstat`, a Log Analyzer

Put the track together: a real tool with options, validation, a pipeline of
small commands, tests, and clean failure. `logstat` reads web-server access
logs and prints a summary: status classes, top paths, top clients, bytes.

Log format: `IP METHOD PATH STATUS BYTES`, one request per line.

## Example

```bash file=example.sh
#!/usr/bin/env bash
# logstat: summarise access logs.
#   logstat [-n TOP] [-s STATUS] FILE...        (use - or no FILE for stdin)
set -euo pipefail
export LC_ALL=C

die()   { echo "logstat: $*" >&2; exit 2; }
usage() { echo "usage: logstat [-n TOP] [-s STATUS] [FILE...]"; }

# --- pure pieces: each reads stdin, writes stdout -------------------------
valid()      { awk 'NF == 5 && $4 ~ /^[0-9]{3}$/ && $5 ~ /^[0-9]+$/'; }
only_status() { awk -v s="$1" '$4 == s'; }              # "" would match none
total()      { wc -l | tr -d ' '; }
bytes()      { awk '{ b += $5 } END { print b + 0 }'; }
classes()    { awk '{ c[substr($4, 1, 1) "xx"]++ } END { for (k in c) print k, c[k] }' | sort; }
top()        { # top FIELD N : most frequent values of a column
  awk -v f="$1" '{ n[$f]++ } END { for (k in n) print n[k], k }' |
    sort -k1,1nr -k2 | head -n "$2" | awk '{ print "  " $2 " (" $1 ")" }'
}

report() {
  local top=$1 status=$2 data
  data=$(valid)                                       # drop malformed lines
  [[ -n $status ]] && data=$(only_status "$status" <<< "$data" || true)
  if [[ -z $data ]]; then echo "no matching requests"; return 0; fi
  echo "requests: $(total <<< "$data")"
  echo "bytes:    $(bytes <<< "$data")"
  echo "status classes:"; classes <<< "$data" | sed 's/^/  /'
  echo "top paths:";   top 3 "$top" <<< "$data"
  echo "top clients:"; top 1 "$top" <<< "$data"
}

main() {
  local top=3 status="" opt OPTIND=1
  while getopts ":n:s:h" opt; do
    case $opt in
      n) [[ $OPTARG =~ ^[1-9][0-9]*$ ]] || die "-n needs a positive number"; top=$OPTARG ;;
      s) [[ $OPTARG =~ ^[0-9]{3}$ ]]    || die "-s needs a 3-digit status"; status=$OPTARG ;;
      h) usage; return 0 ;;
      :) die "option -$OPTARG needs an argument" ;;
      *) die "unknown option -$OPTARG" ;;
    esac
  done
  shift $((OPTIND - 1))

  if (( $# == 0 )); then set -- -; fi
  local f
  for f in "$@"; do
    [[ $f == - || -r $f ]] || die "cannot read '$f'"
  done
  cat -- "$@" | report "$top" "$status"      # cat - reads stdin
}

# --- demo -----------------------------------------------------------------
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/a.log" <<'EOF'
10.0.0.1 GET /index.html 200 512
10.0.0.2 GET /about.html 200 300
10.0.0.1 POST /login 302 0
10.0.0.3 GET /missing 404 120
this line is garbage
10.0.0.2 GET /index.html 200 512
10.0.0.1 GET /index.html 500 0
EOF

echo "== all"
main -n 2 "$tmp/a.log"
echo "== only 200, from stdin"
main -s 200 < "$tmp/a.log"
echo "== no matches"
main -s 418 "$tmp/a.log"
echo "== errors"
( main -n zero "$tmp/a.log" ) 2>&1 || echo "exit $?"
( main nonexistent.log ) 2>&1 || echo "exit $?"
```

```text output
== all
requests: 6
bytes:    1444
status classes:
  2xx 3
  3xx 1
  4xx 1
  5xx 1
top paths:
  /index.html (3)
  /about.html (1)
top clients:
  10.0.0.1 (3)
  10.0.0.2 (2)
== only 200, from stdin
requests: 3
bytes:    1324
status classes:
  2xx 3
top paths:
  /index.html (2)
  /about.html (1)
top clients:
  10.0.0.2 (2)
  10.0.0.1 (1)
== no matches
no matching requests
== errors
logstat: -n needs a positive number
exit 2
logstat: cannot read 'nonexistent.log'
exit 2
```

## Details that bite

- Every stage is a function that reads stdin and writes stdout, so each can
  be tested on its own (see the exercise) and recombined in a pipeline.
- Validate input once, at the edge (`valid`), and let later stages assume
  clean lines. Count what you drop if the user needs to know.
- `data=$(...)` stores a result so several consumers can use it. For huge
  logs, stream with `tee >(...)` or run `awk` once with several arrays
  instead.
- `head -n` closing early can make an upstream stage die of `SIGPIPE`
  (status 141), which `pipefail` reports as failure. When truncating a
  pipeline on purpose, either end in a stage that reads everything or
  tolerate 141 explicitly.
- Sort ties explicitly (`-k1,1nr -k2`) or the output order changes between
  runs and machines.

## Exercises

```bash file=exercise.sh
#!/usr/bin/env bash
export LC_ALL=C
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

log='10.0.0.1 GET /a 200 10
10.0.0.2 POST /b 404 20
10.0.0.1 GET /a 200 30
bad line
10.0.0.3 GET /c 503 5'

# Stage 1: keep only lines with exactly 5 fields.
valid() { cat; }                      # TODO

# Stage 2: print the 95th-percentile-ish value: the largest BYTES (5th
# field) among the lines. Print just the number (0 for no input).
max_bytes() { echo 0; }               # TODO

# Stage 3: "errors per client": for status >= 400 count lines per IP and
# print "IP COUNT", sorted by count descending then IP.
error_clients() { cat; }              # TODO

# Stage 4: print the error RATE as a whole-number percent of valid lines
# (status >= 400). 2 of 4 valid lines -> 50.
error_rate() { echo 0; }              # TODO

check "valid" "$(valid <<< "$log" | wc -l | tr -d ' ')" "4"
check "max_bytes" "$(valid <<< "$log" | max_bytes)" "30"
check "max_bytes empty" "$(max_bytes < /dev/null)" "0"
check "error_clients" "$(valid <<< "$log" | error_clients | tr '\n' ';')" "10.0.0.2 1;10.0.0.3 1;"
check "error_rate" "$(valid <<< "$log" | error_rate)" "50"
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

log='10.0.0.1 GET /a 200 10
10.0.0.2 POST /b 404 20
10.0.0.1 GET /a 200 30
bad line
10.0.0.3 GET /c 503 5'

valid() { awk 'NF == 5'; }

max_bytes() { awk '$5 > m { m = $5 } END { print m + 0 }'; }

error_clients() {
  awk '$4 >= 400 { n[$1]++ } END { for (ip in n) print ip, n[ip] }' |
    sort -k2,2nr -k1,1
}

error_rate() {
  awk '{ t++ } $4 >= 400 { e++ } END { print (t ? int(100 * e / t) : 0) }'
}

check "valid" "$(valid <<< "$log" | wc -l | tr -d ' ')" "4"
check "max_bytes" "$(valid <<< "$log" | max_bytes)" "30"
check "max_bytes empty" "$(max_bytes < /dev/null)" "0"
check "error_clients" "$(valid <<< "$log" | error_clients | tr '\n' ';')" "10.0.0.2 1;10.0.0.3 1;"
check "error_rate" "$(valid <<< "$log" | error_rate)" "50"
exit $failed
```

</details>

Next: [15 — Portable POSIX sh](15-posix-sh.md)
