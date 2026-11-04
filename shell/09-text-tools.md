# Shell 09 — Text Tools: grep, sed, awk, sort, cut, jq

The shell's superpower is the pipeline of small text tools. Learn six
of them well and most scripting is one line. When a pipeline surprises
you, cut it at the pipe and look at that stage alone. `ls | grep` and
`for f in $(ls)` are the classic anti-patterns. Use a glob or `find`
(next lesson).

## `grep` selects lines

`-c` counts, `-v` inverts, `-E` is extended regex, `-o` prints only
the match. Without `-E`, `+ ? | ( )` are literal characters. Set
`LC_ALL=C` when the script must sort the same way on every machine.

```bash file=n01.sh
export LC_ALL=C
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
cat > access.log <<'EOF'
10.0.0.1 GET /index.html 200 512
10.0.0.2 GET /about.html 200 300
10.0.0.1 POST /login 302 0
10.0.0.3 GET /missing 404 120
10.0.0.2 GET /index.html 200 512
10.0.0.1 GET /index.html 500 0
EOF
grep -c GET access.log
grep -v GET access.log
echo "$(( $(grep -E ' (404|500) ' access.log | wc -l) ))"
grep -oE '^[0-9.]+' access.log | head -2
```

```text output
5
10.0.0.1 POST /login 302 0
2
10.0.0.1
10.0.0.2
```

## `grep` exits 1 when nothing matches

`set -e` and `pipefail` treat that as a failure. Use `|| true`, or
put `grep -q` in the test of an `if`.

```bash file=n02.sh
grep -c zebra <<< apple || echo "exit $?"
```

```text output
0
exit 1
```

## `cut` picks columns and keeps their order

It cannot reorder fields: `-f3,1` still prints field 1 before field 3.
Every delimiter counts, so `a,,b` has three fields. `awk` is the
flexible answer.

```bash file=n03.sh
export LC_ALL=C
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
cat > access.log <<'EOF'
10.0.0.1 GET /index.html 200 512
10.0.0.2 GET /about.html 200 300
10.0.0.1 POST /login 302 0
10.0.0.3 GET /missing 404 120
10.0.0.2 GET /index.html 200 512
10.0.0.1 GET /index.html 500 0
EOF
cut -d' ' -f1,4 access.log | head -2
echo "a,,b" | cut -d, -f3,1
```

```text output
10.0.0.1 200
10.0.0.2 200
a,b
```

## `sort | uniq -c` counts duplicates

`uniq` only collapses adjacent copies, so sort first. `sort -rn`
puts the biggest count first. `sort -n` compares numbers. `sort -h`
understands suffixes like `1K` and `2M`. The count column is padded.
The width depends on the `uniq` you have.

```bash file=n04.sh
export LC_ALL=C
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
cat > access.log <<'EOF'
10.0.0.1 GET /index.html 200 512
10.0.0.2 GET /about.html 200 300
10.0.0.1 POST /login 302 0
10.0.0.3 GET /missing 404 120
10.0.0.2 GET /index.html 200 512
10.0.0.1 GET /index.html 500 0
EOF
cut -d' ' -f1 access.log | sort | uniq -c | sort -rn | head -2
```

```text output
   3 10.0.0.1
   2 10.0.0.2
```

## `sort -k` chooses the field

`-k5,5n` sorts field 5 numerically. A second `-k` breaks ties. With
`LC_ALL=C` the tie-break is byte order, not the locale's dictionary.

```bash file=n05.sh
export LC_ALL=C
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
cat > access.log <<'EOF'
10.0.0.1 GET /index.html 200 512
10.0.0.2 GET /about.html 200 300
10.0.0.1 POST /login 302 0
10.0.0.3 GET /missing 404 120
10.0.0.2 GET /index.html 200 512
10.0.0.1 GET /index.html 500 0
EOF
sort -k5,5n -k1,1 access.log | tail -2 | cut -d' ' -f1,5
```

```text output
10.0.0.1 512
10.0.0.2 512
```

## `awk` is a column language

Fields are `$1` through `$NF`. A pattern selects lines. `BEGIN` and
`END` bracket the run. `-F` sets the separator. It has variables,
arrays, and `printf`. Reach for it before you write a `while read`
loop over columns.

```bash file=n06.sh
export LC_ALL=C
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
cat > access.log <<'EOF'
10.0.0.1 GET /index.html 200 512
10.0.0.2 GET /about.html 200 300
10.0.0.1 POST /login 302 0
10.0.0.3 GET /missing 404 120
10.0.0.2 GET /index.html 200 512
10.0.0.1 GET /index.html 500 0
EOF
awk '$4 == 200 { n++ } END { print n " ok responses" }' access.log
awk '{ bytes[$1] += $5 } END { for (ip in bytes) print ip, bytes[ip] }' access.log | sort
awk -F'[ /]+' '$2 == "GET" && NR > 4 { print NR ": " $3 }' access.log
awk '{ printf "%-9s %s\n", $1, toupper($2) }' access.log | head -2
```

```text output
3 ok responses
10.0.0.1 512
10.0.0.2 812
10.0.0.3 120
5: index.html
6: index.html
10.0.0.1  GET
10.0.0.2  GET
```

## `sed` edits the stream

`s/old/new/flags` substitutes. `-n` with `p` prints only the lines you
ask for. `sed -i` differs between GNU and BSD: BSD wants `-i ''`.
For a script that runs on both, write a temp file and `mv`.

```bash file=n07.sh
export LC_ALL=C
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
cat > access.log <<'EOF'
10.0.0.1 GET /index.html 200 512
10.0.0.2 GET /about.html 200 300
10.0.0.1 POST /login 302 0
10.0.0.3 GET /missing 404 120
10.0.0.2 GET /index.html 200 512
10.0.0.1 GET /index.html 500 0
EOF
sed 's/GET/get/; s/POST/post/' access.log | head -3 | cut -c1-20
sed -n '2,3p' access.log | cut -d' ' -f3
sed -E 's/^([0-9.]+) ([A-Z]+) .*/\2 from \1/' access.log | head -2
echo "$(( $(sed '/login/d' access.log | wc -l) ))"
```

```text output
10.0.0.1 get /index.
10.0.0.2 get /about.
10.0.0.1 post /login
/about.html
/login
GET from 10.0.0.1
GET from 10.0.0.2
5
```

## `tr` maps or deletes characters

It is not a regex tool. `-d` deletes a set. `-s` squeezes repeats
down to one.

```bash file=n08.sh
echo "Hello, World 123" | tr -d '0-9' | tr 'A-Z' 'a-z'
echo "a  b   c" | tr -s ' '
```

```text output
hello, world 
a b c
```

## `paste` and `join` reshape columns

`paste -sd,` joins a column into one line. `join` merges two sorted
files on the first field. Sort both inputs first or the merge is wrong.

```bash file=n09.sh
export LC_ALL=C
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
cat > access.log <<'EOF'
10.0.0.1 GET /index.html 200 512
10.0.0.2 GET /about.html 200 300
10.0.0.1 POST /login 302 0
10.0.0.3 GET /missing 404 120
10.0.0.2 GET /index.html 200 512
10.0.0.1 GET /index.html 500 0
EOF
paste -sd, <(cut -d' ' -f4 access.log | sort -u)
printf '1 a\n2 b\n' > l.txt
printf '1 X\n2 Y\n' > r.txt
join l.txt r.txt
```

```text output
200,302,404,500
1 a X
2 b Y
```

## `xargs` turns lines into arguments

`-n 2` passes two inputs per command. The command runs again for
whatever is left.

```bash file=n10.sh
printf '%s\n' one two three | xargs -n 2 echo
```

```text output
one two
three
```

## `jq` is how you read JSON

Do not parse JSON, YAML, or HTML with `grep` or `sed`. `-r` is raw
strings. `-c` is one compact object per line.

```bash file=n11.sh
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
cat > data.json <<'EOF'
{"users":[{"name":"ada","age":36,"tags":["math"]},
          {"name":"linus","age":55,"tags":["kernel","git"]}]}
EOF
jq -r '.users[].name' data.json
jq '[.users[] | select(.age > 40)] | length' data.json
jq -r '.users[] | "\(.name): \(.tags | join("/"))"' data.json
jq -c '.users | map({n: .name})' data.json
```

```text output
ada
linus
1
ada: math
linus: kernel/git
[{"n":"ada"},{"n":"linus"}]
```

## Exercises

```bash file=exercise.sh
#!/usr/bin/env bash
export LC_ALL=C
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

data='ada,36,uk
linus,55,fi
grace,85,us
alan,41,uk'

# Echo the names (first CSV column) of stdin, one per line.
names() { cat; }                 # TODO

# Echo the sum of the second CSV column.
total_age() { echo 0; }          # TODO

# Echo how many lines have country (3rd column) equal to $1.
count_country() { echo 0; }      # TODO

# Echo the name of the oldest person (largest second column).
oldest() { echo ""; }            # TODO

# Replace every run of digits with "#" in stdin.
mask_digits() { cat; }           # TODO

# Echo the distinct countries, sorted, each with how many people: "uk 2".
by_country() { cat; }            # TODO

check "names" "$(names <<< "$data" | tr '\n' ' ')" "ada linus grace alan "
check "total" "$(total_age <<< "$data")" "217"
check "count" "$(count_country uk <<< "$data")" "2"
check "oldest" "$(oldest <<< "$data")" "grace"
check "mask" "$(echo 'a12b345c6' | mask_digits)" "a#b#c#"
check "by_country" "$(by_country <<< "$data" | tr '\n' ';')" "fi 1;uk 2;us 1;"
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

data='ada,36,uk
linus,55,fi
grace,85,us
alan,41,uk'

names() { cut -d, -f1; }

total_age() { awk -F, '{ s += $2 } END { print s }'; }

count_country() { awk -F, -v c="$1" '$3 == c { n++ } END { print n + 0 }'; }

oldest() { sort -t, -k2,2nr | head -1 | cut -d, -f1; }

mask_digits() { sed -E 's/[0-9]+/#/g'; }

by_country() { cut -d, -f3 | sort | uniq -c | awk '{ print $2, $1 }'; }

check "names" "$(names <<< "$data" | tr '\n' ' ')" "ada linus grace alan "
check "total" "$(total_age <<< "$data")" "217"
check "count" "$(count_country uk <<< "$data")" "2"
check "oldest" "$(oldest <<< "$data")" "grace"
check "mask" "$(echo 'a12b345c6' | mask_digits)" "a#b#c#"
check "by_country" "$(by_country <<< "$data" | tr '\n' ';')" "fi 1;uk 2;us 1;"
exit $failed
```

</details>

Next: [10 — Files and find](10-files-find.md)
