# Shell 09 — Text Tools: grep, sed, awk, sort, cut, jq

The shell's superpower is the pipeline of small text tools. Learn six of
them well and most "scripting" is one line.

## Example

```bash file=example.sh
#!/usr/bin/env bash
export LC_ALL=C          # byte-wise sort order, identical on every machine

cat > access.log <<'EOF'
10.0.0.1 GET /index.html 200 512
10.0.0.2 GET /about.html 200 300
10.0.0.1 POST /login 302 0
10.0.0.3 GET /missing 404 120
10.0.0.2 GET /index.html 200 512
10.0.0.1 GET /index.html 500 0
EOF

# grep: select lines. -c count, -v invert, -E regex, -o only match, -w word
grep -c GET access.log
grep -v GET access.log
grep -E ' (404|500) ' access.log | wc -l
grep -oE '^[0-9.]+' access.log | head -2

# cut: pick columns by delimiter
cut -d' ' -f1,4 access.log | head -2

# sort | uniq -c | sort -rn : the frequency-table idiom
cut -d' ' -f1 access.log | sort | uniq -c | sort -rn | head -2

# sort keys: -k field, -n numeric, -r reverse, -u unique
sort -k5,5n -k1,1 access.log | tail -2 | cut -d' ' -f1,5

# awk: fields are $1..$NF; patterns select lines; BEGIN/END bracket the run
awk '$4 == 200 { n++ } END { print n " ok responses" }' access.log
awk '{ bytes[$1] += $5 } END { for (ip in bytes) print ip, bytes[ip] }' access.log | sort
awk -F'[ /]+' '$2 == "GET" && NR > 4 { print NR ": " $3 }' access.log
awk '{ printf "%-9s %s\n", $1, toupper($2) }' access.log | head -2

# sed: stream editor. s/old/new/flags, -n with p prints selected lines
sed 's/GET/get/; s/POST/post/' access.log | head -3 | cut -c1-20
sed -n '2,3p' access.log | cut -d' ' -f3
sed -E 's/^([0-9.]+) ([A-Z]+) .*/\2 from \1/' access.log | head -2
sed '/login/d' access.log | wc -l

# tr: character-for-character translate or delete
echo "Hello, World 123" | tr -d '0-9' | tr 'A-Z' 'a-z'
echo "a  b   c" | tr -s ' '

# paste / join / column: reshape
paste -sd, <(cut -d' ' -f4 access.log | sort -u)
printf '1 a\n2 b\n' > l.txt; printf '1 X\n2 Y\n' > r.txt
join l.txt r.txt

# xargs: turn lines into arguments
printf '%s\n' one two three | xargs -n 2 echo

# jq: the same idea for JSON
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
5
10.0.0.1 POST /login 302 0
2
10.0.0.1
10.0.0.2
10.0.0.1 200
10.0.0.2 200
      3 10.0.0.1
      2 10.0.0.2
10.0.0.1 512
10.0.0.2 512
3 ok responses
10.0.0.1 512
10.0.0.2 812
10.0.0.3 120
5: index.html
6: index.html
10.0.0.1  GET
10.0.0.2  GET
10.0.0.1 get /index.
10.0.0.2 get /about.
10.0.0.1 post /login
/about.html
/login
GET from 10.0.0.1
GET from 10.0.0.2
5
hello, world 
a b c
200,302,404,500
1 a X
2 b Y
one two
three
ada
linus
1
ada: math
linus: kernel/git
[{"n":"ada"},{"n":"linus"}]
```

## Details that bite

- The example's output is a good reminder to run each stage alone. When a
  pipeline surprises you, cut it at the pipe and look.
- `uniq` only collapses **adjacent** duplicates: always `sort | uniq`.
- `sort` order depends on locale (`LC_ALL=C` gives plain byte order, and
  makes scripts reproducible). `sort -n` for numbers, `-h` for `1K 2M`.
- `grep` exits **1 when nothing matches**, which `set -e` and `pipefail`
  treat as an error. Use `|| true` or `grep -q` in a condition.
- `sed -i` differs between GNU and BSD/macOS (`-i ''`). For portability
  write to a temp file and `mv`.
- Basic regex (default for `grep`/`sed`) treats `+ ? | ( )` literally;
  add `-E` for extended regex, which is what you expect.
- `awk` runs per line with fields split on whitespace; `-F` sets the
  separator. It has real variables, arrays and `printf`: reach for it
  before writing a `while read` loop.
- Never parse JSON, YAML or HTML with `grep`/`sed`. Use `jq` (or `yq`,
  `pup`).
- `cut` cannot reorder fields, and treats every delimiter as a separator
  (so `a,,b` has three fields). `awk` is the flexible answer.
- `ls | grep` and `for f in $(ls)` are the classic anti-patterns: use
  globs or `find` (next lesson).

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
