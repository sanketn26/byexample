# Shell 14 — Capstone: `logstat`, a Log Analyzer

`logstat` reads web-server access logs and prints a summary: how many
requests, how many bytes, status classes, top paths, top clients. One
line is `IP METHOD PATH STATUS BYTES`. Each stage is a function that
reads stdin and writes stdout, so you can test it alone and then
compose it. Validate once, at the edge, and let later stages assume
the lines are clean.

## `valid` drops a malformed line

Five fields, a three-digit status, a byte count that is all digits.
Everything else is noise. Count what you drop if the operator needs
to know.

```bash file=n01.sh
export LC_ALL=C
valid() { awk 'NF == 5 && $4 ~ /^[0-9]{3}$/ && $5 ~ /^[0-9]+$/'; }
valid <<'EOF'
10.0.0.1 GET /index.html 200 512
this line is garbage
10.0.0.1 GET /index.html 500 0
EOF
```

```text output
10.0.0.1 GET /index.html 200 512
10.0.0.1 GET /index.html 500 0
```

## Count the lines and sum the bytes

`data=$(...)` holds the clean log so several consumers can read it.
For a huge file, stream with `tee >(consumer)` or do the whole
summary in one `awk`. `wc` on some systems pads the count. `tr -d ' '`
leaves the digits.

```bash file=n02.sh
export LC_ALL=C
valid() { awk 'NF == 5 && $4 ~ /^[0-9]{3}$/ && $5 ~ /^[0-9]+$/'; }
total() { wc -l | tr -d ' '; }
bytes() { awk '{ b += $5 } END { print b + 0 }'; }
data=$(valid <<'EOF'
10.0.0.1 GET /index.html 200 512
10.0.0.2 GET /about.html 200 300
10.0.0.1 POST /login 302 0
10.0.0.3 GET /missing 404 120
this line is garbage
10.0.0.2 GET /index.html 200 512
10.0.0.1 GET /index.html 500 0
EOF
)
echo "requests: $(total <<< "$data")"
echo "bytes: $(bytes <<< "$data")"
```

```text output
requests: 6
bytes: 1444
```

## The status class is the first digit

`2xx` is every status from 200 to 299. Sort the keys so the lines
come out in order. `awk`'s array order is not that order.

```bash file=n03.sh
export LC_ALL=C
valid() { awk 'NF == 5 && $4 ~ /^[0-9]{3}$/ && $5 ~ /^[0-9]+$/'; }
classes() {
  awk '{ c[substr($4, 1, 1) "xx"]++ } END { for (k in c) print k, c[k] }' | sort
}
valid <<'EOF' | classes
10.0.0.1 GET /index.html 200 512
10.0.0.2 GET /about.html 200 300
10.0.0.1 POST /login 302 0
10.0.0.3 GET /missing 404 120
10.0.0.2 GET /index.html 200 512
10.0.0.1 GET /index.html 500 0
EOF
```

```text output
2xx 3
3xx 1
4xx 1
5xx 1
```

## `top` is a frequency table of one column

Sort by count descending, then by the value. Without the second key,
a tie changes order between machines. `head` stops early. On a short
list it still reads everything, so this pipeline's status stays 0.

```bash file=n04.sh
export LC_ALL=C
valid() { awk 'NF == 5 && $4 ~ /^[0-9]{3}$/ && $5 ~ /^[0-9]+$/'; }
top() {
  awk -v f="$1" '{ n[$f]++ } END { for (k in n) print n[k], k }' |
    sort -k1,1nr -k2 | head -n "$2" | awk '{ print "  " $2 " (" $1 ")" }'
}
data=$(valid <<'EOF'
10.0.0.1 GET /index.html 200 512
10.0.0.2 GET /about.html 200 300
10.0.0.1 POST /login 302 0
10.0.0.3 GET /missing 404 120
10.0.0.2 GET /index.html 200 512
10.0.0.1 GET /index.html 500 0
EOF
)
echo "top paths:"
top 3 2 <<< "$data"
echo "top clients:"
top 1 2 <<< "$data"
```

```text output
top paths:
  /index.html (3)
  /about.html (1)
top clients:
  10.0.0.1 (3)
  10.0.0.2 (2)
```

## Equal counts stay in name order

`-k1,1nr` is the count. `-k2` is the text, ascending. `/a` stays
above `/b` when both occurred once.

```bash file=n05.sh
export LC_ALL=C
top() {
  awk -v f="$1" '{ n[$f]++ } END { for (k in n) print n[k], k }' |
    sort -k1,1nr -k2 | head -n "$2" | awk '{ print "  " $2 " (" $1 ")" }'
}
top 3 2 <<'EOF'
10.0.0.1 GET /b 200 1
10.0.0.2 GET /a 200 1
EOF
```

```text output
  /a (1)
  /b (1)
```

## `-s` keeps a single status

The filter is another stdin-to-stdout stage. Later stages do not
know it happened.

```bash file=n06.sh
export LC_ALL=C
valid() { awk 'NF == 5 && $4 ~ /^[0-9]{3}$/ && $5 ~ /^[0-9]+$/'; }
only_status() { awk -v s="$1" '$4 == s'; }
total() { wc -l | tr -d ' '; }
bytes() { awk '{ b += $5 } END { print b + 0 }'; }
data=$(valid <<'EOF'
10.0.0.1 GET /index.html 200 512
10.0.0.2 GET /about.html 200 300
10.0.0.1 POST /login 302 0
10.0.0.3 GET /missing 404 120
10.0.0.2 GET /index.html 200 512
10.0.0.1 GET /index.html 500 0
EOF
)
data=$(only_status 200 <<< "$data")
echo "requests: $(total <<< "$data")"
echo "bytes: $(bytes <<< "$data")"
```

```text output
requests: 3
bytes: 1324
```

## No rows is an empty result, not a crash

An unknown status matches nothing. Say so and exit 0. The user asked
a question that has an answer.

```bash file=n07.sh
export LC_ALL=C
valid() { awk 'NF == 5 && $4 ~ /^[0-9]{3}$/ && $5 ~ /^[0-9]+$/'; }
only_status() { awk -v s="$1" '$4 == s'; }
data=$(valid <<'EOF'
10.0.0.1 GET /index.html 200 512
EOF
)
data=$(only_status 418 <<< "$data" || true)
if [[ -z $data ]]; then echo "no matching requests"; fi
```

```text output
no matching requests
```

## Reject a bad option before reading the log

`-n` is a positive integer. `-s` is three digits. A path that is not
`-` and is not readable is a usage error, status 2. `die` writes to
stderr.

```bash file=n08.sh
set -euo pipefail
die() { echo "logstat: $*" >&2; exit 2; }
check_n() { [[ $1 =~ ^[1-9][0-9]*$ ]] || die "-n needs a positive number"; }
check_file() { [[ $1 == - || -r $1 ]] || die "cannot read '$1'"; }
( check_n zero ) 2>&1 || echo "exit $?"
( check_file nonexistent.log ) 2>&1 || echo "exit $?"
```

```text output
logstat: -n needs a positive number
exit 2
logstat: cannot read 'nonexistent.log'
exit 2
```

## `head` can SIGPIPE the stage before it

`head -n` closes its input when it has enough lines. The previous
command then dies with status 141 (128+13). `pipefail` reports that
as failure. When you truncate on purpose, either let the last stage
read everything or tolerate 141. A short `top` does not hit this.
`yes` does, because it never ends.

```bash file=n09.sh
set +e
set -o pipefail
yes | head -n 1 >/dev/null
echo "pipefail $?"
set +o pipefail
yes | head -n 1 >/dev/null
echo "default $?"
```

```text output
pipefail 141
default 0
```

## The pieces are one program

`main` parses options, checks the paths, and `cat`s every file into
`report`. `-` or no file means stdin. `cat -` is that stdin. Run the
stages on their own, above, before you trust the combination.

```bash file=n10.sh
set -euo pipefail
export LC_ALL=C
die() { echo "logstat: $*" >&2; exit 2; }
valid() { awk 'NF == 5 && $4 ~ /^[0-9]{3}$/ && $5 ~ /^[0-9]+$/'; }
only_status() { awk -v s="$1" '$4 == s'; }
total() { wc -l | tr -d ' '; }
bytes() { awk '{ b += $5 } END { print b + 0 }'; }
classes() { awk '{ c[substr($4, 1, 1) "xx"]++ } END { for (k in c) print k, c[k] }' | sort; }
top() {
  awk -v f="$1" '{ n[$f]++ } END { for (k in n) print n[k], k }' |
    sort -k1,1nr -k2 | head -n "$2" | awk '{ print "  " $2 " (" $1 ")" }'
}
report() {
  local topn=$1 status=$2 data
  data=$(valid)
  [[ -n $status ]] && data=$(only_status "$status" <<< "$data" || true)
  if [[ -z $data ]]; then echo "no matching requests"; return 0; fi
  echo "requests: $(total <<< "$data")"
  echo "bytes:    $(bytes <<< "$data")"
  echo "status classes:"
  classes <<< "$data" | sed 's/^/  /'
  echo "top paths:"
  top 3 "$topn" <<< "$data"
  echo "top clients:"
  top 1 "$topn" <<< "$data"
}
main() {
  local topn=3 status="" opt OPTIND=1
  while getopts ":n:s:h" opt; do
    case $opt in
      n) [[ $OPTARG =~ ^[1-9][0-9]*$ ]] || die "-n needs a positive number"; topn=$OPTARG ;;
      s) [[ $OPTARG =~ ^[0-9]{3}$ ]] || die "-s needs a 3-digit status"; status=$OPTARG ;;
      h) echo "usage: logstat [-n TOP] [-s STATUS] [FILE...]"; return 0 ;;
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
  cat -- "$@" | report "$topn" "$status"
}
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
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
