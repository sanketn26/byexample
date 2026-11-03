# Shell 01 — Values, Variables and Quoting

In shell everything is a **string**. There are no types, only strings that
some commands choose to read as numbers. The whole language is about *when
the shell rewrites your text* — and quoting is how you control that.

## Example

```bash file=example.sh
#!/usr/bin/env bash
name="Ada Lovelace"          # no spaces around '='
echo "$name"
echo '$name'                 # single quotes: nothing is expanded
echo "${name}'s notes"       # braces end the variable name

# Quoting decides how many words a value becomes
words() { echo "$# word(s)"; }
words $name                  # unquoted: split on whitespace
words "$name"                # quoted: one word

# Command substitution and arithmetic
today_len=$(echo -n "$name" | wc -c)
echo "length $today_len"
echo "sum $((3 + 4 * 2))"
x=5; x=$((x + 1)); echo "x=$x"

# Defaults and required values
unset maybe
echo "${maybe:-fallback}"    # use fallback, do not assign
echo "${maybe:=assigned}"    # use and assign
echo "$maybe"
echo "${#name} chars"        # length

# Exit status is the "return value" of a command: 0 means success
true;  echo "true -> $?"
false; echo "false -> $?"

# Environment: exported variables are visible to child processes
LOCAL=1
export SHARED=2
bash -c 'echo "child sees LOCAL=[${LOCAL-}] SHARED=[${SHARED-}]"'

# Numbers are strings until arithmetic touches them
a="10"; b="9"
[[ $a < $b ]] && echo "string compare: 10 < 9"
(( a > b )) && echo "numeric compare: 10 > 9"

# printf is the portable way to format; echo is not
printf '%s has %d letters, %05.1f%%\n' "$name" "${#name}" 42.5
```

```text output
Ada Lovelace
$name
Ada Lovelace's notes
2 word(s)
1 word(s)
length 12
sum 11
x=6
fallback
assigned
assigned
12 chars
true -> 0
false -> 1
child sees LOCAL=[] SHARED=[2]
string compare: 10 < 9
numeric compare: 10 > 9
Ada Lovelace has 12 letters, 042.5%
```

## Details that bite

- `name = value` (with spaces) runs a *command* called `name`. Assignment
  has no spaces.
- **Always quote expansions**: `"$var"`, `"$@"`, `"$(cmd)"`. Unquoted, the
  shell splits on whitespace *and* expands `*` as a glob. A file called
  `my notes.txt` becomes two arguments.
- Single quotes are literal. Double quotes allow `$`, `` ` ``, `\`.
  There is no way to put a `'` inside single quotes; close, escape, reopen:
  `'it'\''s'`.
- `$?` is overwritten by the very next command, even `echo`. Save it
  (`rc=$?`) if you need it.
- Inside `[[ ]]`, `<` compares as **strings**; use `(( ))` or `-lt` for
  numbers.
- Integers only: `$(( 7 / 2 ))` is `3`. For decimals use `awk` or `bc`.
- Variables are global by default, even inside functions (lesson 03 fixes
  that with `local`).
- `${#s}` counts characters only if the locale is UTF-8; in the `C` locale
  it counts bytes. Scripts that care set `LC_ALL` explicitly.
- `echo` varies between shells (`-n`, `-e`, backslashes). Use `printf`
  whenever the text is data.

## Exercises

```bash file=exercise.sh
#!/usr/bin/env bash
export LC_ALL=C.UTF-8   # length counts characters only in a UTF-8 locale
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

count_args() { echo $#; }

# Return the number of arguments produced when "$1" is passed to
# count_args *correctly quoted*, so a value with spaces is ONE argument.
one_arg() {
  count_args  # TODO
}

# Echo the value of $1, or "n/a" when it is unset or empty.
or_na() {
  echo ""  # TODO
}

# Echo the length of the string $1.
length_of() {
  echo 0  # TODO
}

# Echo the product of the two integers $1 and $2.
product() {
  echo 0  # TODO
}

check "quoting" "$(one_arg "a b c")" "1"
check "default" "$(or_na "")" "n/a"
check "default set" "$(or_na "x")" "x"
check "length" "$(length_of "héllo")" "5"
check "product" "$(product 6 7)" "42"
exit $failed
```

<details><summary>Solution</summary>

```bash file=solution.sh
#!/usr/bin/env bash
export LC_ALL=C.UTF-8   # length counts characters only in a UTF-8 locale
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

count_args() { echo $#; }

one_arg() {
  count_args "$1"
}

or_na() {
  echo "${1:-n/a}"
}

length_of() {
  echo "${#1}"
}

product() {
  echo $(($1 * $2))
}

check "quoting" "$(one_arg "a b c")" "1"
check "default" "$(or_na "")" "n/a"
check "default set" "$(or_na "x")" "x"
check "length" "$(length_of "héllo")" "5"
check "product" "$(product 6 7)" "42"
exit $failed
```

</details>

Next: [02 — Control flow](02-control-flow.md)
