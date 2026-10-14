# Go 05 — Strings, Bytes and Runes

A Go `string` is an immutable sequence of **bytes**, conventionally UTF-8.
A `rune` is one Unicode code point (`int32`). Mixing those up is the main
source of string bugs.

## Example

```go file=example.go
package main

import (
	"fmt"
	"strconv"
	"strings"
	"unicode/utf8"
)

func main() {
	s := "héllo, 世界"
	fmt.Println(len(s), utf8.RuneCountInString(s)) // bytes vs runes
	fmt.Println(s[0], string(s[0]), s[1:3])        // indexing yields bytes

	r := []rune(s) // decode into code points
	fmt.Println(len(r), string(r[7:]))

	bs := []byte("abc") // strings are immutable; bytes are not
	bs[0] = 'X'
	fmt.Println(string(bs))

	// strings package
	fmt.Println(strings.Contains("seafood", "foo"), strings.Index("chicken", "ken"),
		strings.Split("a,b,c", ","), strings.Fields("  a  b "), strings.TrimSpace("  x "))
	fmt.Println(strings.ToUpper("hello"), strings.Repeat("ab", 3), strings.ReplaceAll("hello", "e", "-"))

	// Build with strings.Builder, not +=
	var sb strings.Builder
	for i := 0; i < 3; i++ {
		fmt.Fprintf(&sb, "%d,", i)
	}
	fmt.Println(strings.TrimSuffix(sb.String(), ","))

	// strconv: conversions return errors
	n, err := strconv.Atoi("42")
	fmt.Println(n, err)
	n, err = strconv.Atoi("x")
	fmt.Println(n, err)
	f, _ := strconv.ParseFloat("3.5", 64)
	b, _ := strconv.ParseBool("true")
	fmt.Println(strconv.FormatInt(255, 2), strconv.Quote("hi\n"), f, b)

	// Cut is the modern split-in-two
	key, val, ok := strings.Cut("key=value", "=")
	fmt.Println(key, val, ok)

	fmt.Println(strings.EqualFold("Go", "GO"))

	// Invalid UTF-8 decodes to U+FFFD
	bad := "a\xffb"
	fmt.Println([]rune(bad), utf8.ValidString(bad))

	// Raw string literals do not process escapes
	fmt.Println(len(`\n`), len("\n"))
}
```

```text output
14 9
104 h é
9 世界
Xbc
true 4 [a b c] [a b] x
HELLO ababab h-llo
0,1,2
42 <nil>
0 strconv.Atoi: parsing "x": invalid syntax
11111111 "hi\n" 3.5 true
key value true
true
[97 65533 98] false
2 1
```

## Details that bite

- `len(s)` is a **byte** count. `s[i]` is a byte, not a character.
- `for i, r := range s` decodes runes; `for i := 0; i < len(s); i++` walks
  bytes.
- `s += x` in a loop allocates every time; use `strings.Builder` (or
  `bytes.Buffer`).
- `string(65)` is `"A"` (a rune conversion), not `"65"`; use `strconv.Itoa`.
  `go vet` flags the mistake.
- Strings are comparable and usable as map keys; `[]byte` is not.
- `strings.Title` is deprecated and wrong for Unicode; use
  `golang.org/x/text/cases` when you need proper title-casing.
- Slicing a string at a non-rune boundary yields invalid UTF-8 without
  complaint.

## Exercises

```go file=exercise.go
package main

import (
	"fmt"
	"os"
	"reflect"
)

// IsPalindrome ignores case and everything that is not a letter or digit.
func IsPalindrome(s string) bool {
	return false // TODO
}

// Reverse reverses by rune, so "héllo" -> "olléh".
func Reverse(s string) string {
	return "" // TODO
}

// Caesar shifts ASCII letters by shift (may be negative), keeping case.
func Caesar(text string, shift int) string {
	return "" // TODO
}

// TitleCase uppercases the first rune of each space-separated word and
// lowercases the rest. Keep the original spacing.
func TitleCase(s string) string {
	return "" // TODO
}

// ParseKV parses "a=1,b=two" into a map. Empty input gives an empty map.
func ParseKV(line string) map[string]string {
	return nil // TODO
}

var failed bool

func check(label string, got, want any) {
	if reflect.DeepEqual(got, want) {
		fmt.Println("PASS", label)
		return
	}
	failed = true
	fmt.Printf("FAIL %s: got %v, want %v\n", label, got, want)
}

func main() {
	check("palindrome", IsPalindrome("A man, a plan, a canal: Panama"), true)
	check("not palindrome", IsPalindrome("hello"), false)
	check("reverse", Reverse("héllo"), "olléh")
	check("caesar", Caesar("Hello, World!", 3), "Khoor, Zruog!")
	check("caesar neg", Caesar("Khoor, Zruog!", -3), "Hello, World!")
	check("title", TitleCase("hELLO wORLD  x"), "Hello World  X")
	check("kv", ParseKV("a=1,b=two"), map[string]string{"a": "1", "b": "two"})
	check("kv empty", ParseKV(""), map[string]string{})
	if failed {
		os.Exit(1)
	}
}
```

<details><summary>Solution</summary>

```go file=solution.go
package main

import (
	"fmt"
	"os"
	"reflect"
	"strings"
	"unicode"
)

func IsPalindrome(s string) bool {
	var rs []rune
	for _, r := range s {
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			rs = append(rs, unicode.ToLower(r))
		}
	}
	for i, j := 0, len(rs)-1; i < j; i, j = i+1, j-1 {
		if rs[i] != rs[j] {
			return false
		}
	}
	return true
}

func Reverse(s string) string {
	rs := []rune(s)
	for i, j := 0, len(rs)-1; i < j; i, j = i+1, j-1 {
		rs[i], rs[j] = rs[j], rs[i]
	}
	return string(rs)
}

func Caesar(text string, shift int) string {
	shift = ((shift % 26) + 26) % 26
	return strings.Map(func(r rune) rune {
		switch {
		case r >= 'a' && r <= 'z':
			return 'a' + (r-'a'+rune(shift))%26
		case r >= 'A' && r <= 'Z':
			return 'A' + (r-'A'+rune(shift))%26
		}
		return r
	}, text)
}

func TitleCase(s string) string {
	words := strings.Split(s, " ")
	for i, w := range words {
		rs := []rune(w)
		for j := range rs {
			if j == 0 {
				rs[j] = unicode.ToUpper(rs[j])
			} else {
				rs[j] = unicode.ToLower(rs[j])
			}
		}
		words[i] = string(rs)
	}
	return strings.Join(words, " ")
}

func ParseKV(line string) map[string]string {
	out := map[string]string{}
	if line == "" {
		return out
	}
	for _, pair := range strings.Split(line, ",") {
		k, v, _ := strings.Cut(pair, "=")
		out[k] = v
	}
	return out
}

var failed bool

func check(label string, got, want any) {
	if reflect.DeepEqual(got, want) {
		fmt.Println("PASS", label)
		return
	}
	failed = true
	fmt.Printf("FAIL %s: got %v, want %v\n", label, got, want)
}

func main() {
	check("palindrome", IsPalindrome("A man, a plan, a canal: Panama"), true)
	check("not palindrome", IsPalindrome("hello"), false)
	check("reverse", Reverse("héllo"), "olléh")
	check("caesar", Caesar("Hello, World!", 3), "Khoor, Zruog!")
	check("caesar neg", Caesar("Khoor, Zruog!", -3), "Hello, World!")
	check("title", TitleCase("hELLO wORLD  x"), "Hello World  X")
	check("kv", ParseKV("a=1,b=two"), map[string]string{"a": "1", "b": "two"})
	check("kv empty", ParseKV(""), map[string]string{})
	if failed {
		os.Exit(1)
	}
}
```

</details>

Next: [06 — Structs and methods](06-structs.md)
