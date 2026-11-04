# Shell 01 — Values, Variables and Quoting

In shell everything is a string. There are no types, only strings that
some commands choose to read as numbers. The shell rewrites your text
before a command runs. Quoting is how you control that.

## Assignment has no spaces around `=`

`name=value` binds a string. A space runs a command called `name`.
Braces end the name, so the next character is not part of it.

```bash file=n01.sh
name="Ada Lovelace"
echo "$name"
echo "${name}'s notes"
name = value || true
```

```text output
Ada Lovelace
Ada Lovelace's notes
n01.sh: line 4: name: command not found
```

## Single quotes are literal

Double quotes still expand `$`, backticks, and backslash. Single quotes
expand nothing. There is no apostrophe inside them. Close, escape, and
reopen: `'it'\''s'`.

```bash file=n02.sh
name="Ada Lovelace"
echo '$name'
echo 'it'\''s'
```

```text output
$name
it's
```

## Unquoted expansions split and glob

Quote `"$var"`, `"$@"`, and `"$(cmd)"`. Unquoted, the shell splits on
whitespace and then expands `*` as a glob. A value with a space becomes
two arguments. The glob match stays one argument, spaces included.

```bash file=n03.sh
name="Ada Lovelace"
words() { echo "$# word(s)"; }
words $name
words "$name"
f="my notes.txt"
printf 'split <%s>\n' $f
tmp=$(mktemp -d)
touch "$tmp/my notes.txt"
( cd "$tmp" && printf 'glob <%s>\n' my* )
```

```text output
2 word(s)
1 word(s)
split <my>
split <notes.txt>
glob <my notes.txt>
```

## `$(...)` captures stdout

The substitution pastes the command's stdout into the line and strips
trailing newlines. `$((...))` is integer arithmetic, so `$((7 / 2))` is
`3`. Decimals need `awk` or `bc`.

```bash file=n04.sh
name="Ada Lovelace"
today_len=$(printf '%s' "$name" | wc -c)
echo "length $((today_len))"
echo "sum $((3 + 4 * 2))"
x=5
x=$((x + 1))
echo "x=$x"
echo "div $((7 / 2))"
```

```text output
length 12
sum 11
x=6
div 3
```

## Defaults substitute, and `:=` assigns

`${maybe:-fallback}` is used when the value is unset or empty, and it
does not assign. `${maybe:=assigned}` does both. `${#name}` is the
length.

```bash file=n05.sh
name="Ada Lovelace"
unset maybe
echo "${maybe:-fallback}"
echo "${maybe:=assigned}"
echo "$maybe"
echo "${#name} chars"
```

```text output
fallback
assigned
assigned
12 chars
```

## `$?` is replaced by the next command

The exit status is the command's result. `0` means success. `echo`
replaces `$?`, so save it (`rc=$?`) when you still need it.

```bash file=n06.sh
true
echo "true -> $?"
false
rc=$?
echo "false -> $rc"
echo "next command cleared it -> $?"
```

```text output
true -> 0
false -> 1
next command cleared it -> 0
```

## Exported variables are copied to the child

A child sees names you `export`. It does not see the rest, and it
cannot change the parent's copy.

```bash file=n07.sh
LOCAL=1
export SHARED=2
bash -c 'echo "child sees LOCAL=[${LOCAL-}] SHARED=[${SHARED-}]"'
```

```text output
child sees LOCAL=[] SHARED=[2]
```

## Assignments are global unless you say `local`

A function that assigns a name changes the caller's variable. Lesson 03
keeps the name private with `local`.

```bash file=n08.sh
f() { leaked=yes; }
f
echo "leaked=$leaked"
```

```text output
leaked=yes
```

## `[[ ]]` compares strings; `(( ))` compares numbers

Inside `[[ ]]`, `<` is a string compare, so `"10"` is less than `"9"`.
Use `(( ))` or `-lt` when the values are numbers.

```bash file=n09.sh
a=10
b=9
[[ $a < $b ]] && echo "string compare: 10 < 9"
(( a > b )) && echo "numeric compare: 10 > 9"
```

```text output
string compare: 10 < 9
numeric compare: 10 > 9
```

## `printf` formats data; `echo` does not

`echo` disagrees across shells about `-n`, `-e`, and backslashes.
`printf` is the formatter to use when the text is data.

```bash file=n10.sh
name="Ada Lovelace"
printf '%s has %d letters, %05.1f%%\n' "$name" "${#name}" 42.5
```

```text output
Ada Lovelace has 12 letters, 042.5%
```

## `${#s}` follows the locale

In a UTF-8 locale it counts characters. In the `C` locale it counts
bytes. Scripts that care set `LC_ALL` themselves.

```bash file=n11.sh
s="héllo"
export LC_ALL=C.UTF-8
echo "utf8 ${#s}"
export LC_ALL=C
echo "c ${#s}"
```

```text output
utf8 5
c 6
```

## Decimals need `bc`

`$((...))` is integer arithmetic, so `7 / 2` is `3`. `bc` keeps a
scale. `scale=2` prints two digits after the point.

```bash file=n12.sh
echo "int $((7 / 2))"
echo "scale=2; 7 / 2" | bc
```

```text output
int 3
3.50
```

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
