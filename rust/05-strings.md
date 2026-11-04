# Rust 05 — Strings

`String` owns its bytes and can grow. `&str` borrows some of those bytes.
Both are valid UTF-8. Byte length, the number of `char`s, and what a person
sees as one character are three different counts.

## Bytes and `char`s are different lengths

`len` counts bytes. `chars` counts Unicode scalar values. `s[i]` does not
exist, because a byte offset can land inside a character. Use `chars`,
`char_indices`, or a slice you already know is on a boundary. Grapheme
clusters (what a reader calls one character) need the `unicode-segmentation`
crate. `chars` stops at code points.

```rust file=n01.rs
fn main() {
    let s = String::from("héllo, 世界");
    println!("{} {}", s.len(), s.chars().count());
    println!("{} {:?}", &s[0..1], s.char_indices().nth(2));
    println!("{:?}", s.chars().rev().collect::<String>());
    println!("{}", s.to_uppercase());
}
```

```text output
14 9
h Some((3, 'l'))
"界世 ,olléh"
HÉLLO, 世界
```

## Slicing off a boundary panics

`&s[a..b]` panics when `a` or `b` is inside a character. `get` returns
`None` for the same range, so the caller can decide.

```rust file=n02.rs
fn main() {
    let s = String::from("héllo, 世界");
    println!("{:?} {:?}", s.get(1..2), s.get(1..3));
}
```

```text output
None Some("é")
```

## `String` grows in place

`push_str` and `push` borrow the buffer. `+` is different: `String + &str`
**moves** the left-hand `String`, so that name is gone. Use `format!` when
every piece must stay usable. Return a `String` when you build new text,
and take `&str` in parameters so both `String` and literals work.
`&String` coerces to `&str`.

```rust file=n03.rs
fn shout(s: &str) -> String {
    s.to_uppercase() + "!"
}

fn main() {
    let mut t = String::new();
    t.push_str("ab");
    t.push('c');
    t += "de";
    t.insert(0, '>');
    println!("{t} {}", t.len());

    let a = String::from("ab");
    let b = String::from("cd");
    let c = a + &b;
    println!("{c} {b}");

    let owned = String::from("hey");
    println!("{} {}", shout(&owned), shout("lit"));
}
```

```text output
>abcde 6
abcd cd
HEY! LIT!
```

## Split, trim, and search borrow the original

`split` keeps the empty pieces between separators. `split_whitespace`
does not. `split_once` stops at the first match. `find` returns a byte
index, or `None`.

```rust file=n04.rs
fn main() {
    println!(
        "{:?} {:?}",
        "a,b,,c".split(',').collect::<Vec<_>>(),
        "  x y  ".split_whitespace().collect::<Vec<_>>()
    );
    println!(
        "{:?} {:?}",
        "key=value".split_once('='),
        "novalue".split_once('=')
    );
    println!(
        "{} {} {}",
        "  pad ".trim(),
        "xxhixx".trim_matches('x'),
        "Hello".replace('l', "L")
    );
    println!("{:?} {:?}", "hello".find("ll"), "hello".find('z'));
}
```

```text output
["a", "b", "", "c"] ["x", "y"]
Some(("key", "value")) None
pad hi HeLLo
Some(2) None
```

## Ordering is by bytes, not by locale

`"abc" < "abd"` compares UTF-8 bytes. `to_lowercase` is Unicode-aware, but
it is not a full case-fold, and it does not make sort order match a
dictionary. `join` inserts the separator between borrowed pieces.

```rust file=n05.rs
fn main() {
    println!("{} {}", "abc" < "abd", "Zebra".to_lowercase() == "zebra");
    let words = vec!["a", "b", "c"];
    println!("{}", words.join("-"));
}
```

```text output
true true
a-b-c
```

## Parsing a number is a `Result`

The turbofish `parse::<i32>` picks the target type when inference cannot.
Failure is `Err`, not a panic.

```rust file=n06.rs
fn main() {
    println!("{:?}", "42".parse::<i32>());
    println!("{}", "4x".parse::<i32>().is_err());
}
```

```text output
Ok(42)
true
```

## Invalid UTF-8 is an error, or a replacement

`String::from_utf8` refuses a bad byte. `from_utf8_lossy` substitutes `�`
and always returns a string. File names are not promised to be UTF-8;
`OsString` and `Path` hold those bytes (lesson 10).

```rust file=n07.rs
fn main() {
    println!("{:?}", "hi".bytes().collect::<Vec<u8>>());
    println!("{}", String::from_utf8(vec![104, 105]).unwrap());
    println!("{}", String::from_utf8(vec![0xff]).is_err());
    println!("{}", String::from_utf8_lossy(&[0xff]));
}
```

```text output
[104, 105]
hi
true
�
```

## `format!` builds a `String`

The same format specs as `println!` work here. Nothing is written to the
terminal until you print the result.

```rust file=n08.rs
fn main() {
    let name = "Ada";
    let msg = format!("{name:>6}|{:<6}|{:^6}|", "x", "y");
    println!("{msg}");
}
```

```text output
   Ada|x     |  y   |
```

## A `char` is not a byte

`to_digit` parses one character in a radix. `to_uppercase` can yield more
than one `char`: `ß` becomes `SS`. Adding to a byte and casting with `as`
is only safe inside ASCII.

```rust file=n09.rs
fn main() {
    println!(
        "{} {} {:?} {}",
        'a'.is_alphabetic(),
        '9'.to_digit(10).unwrap(),
        'ß'.to_uppercase().collect::<String>(),
        (b'a' + 2) as char
    );
}
```

```text output
true 9 "SS" c
```

## Exercises

```rust file=exercise.rs
use std::collections::HashMap;

/// Ignoring case and non-alphanumerics.
fn is_palindrome(_s: &str) -> bool {
    todo!()
}

/// Reverse the order of words: "a b  c" -> "c b a" (single spaces out).
fn reverse_words(_s: &str) -> String {
    todo!()
}

/// Shift ASCII letters by `shift` (may be negative), keeping case.
fn caesar(_text: &str, _shift: i32) -> String {
    todo!()
}

/// Uppercase the first char of each space-separated word, lowercase the
/// rest, preserving the original spacing.
fn title_case(_s: &str) -> String {
    todo!()
}

/// Parse "a=1,b=two" into a map. Empty input gives an empty map.
fn parse_kv(_line: &str) -> HashMap<String, String> {
    todo!()
}

/// Number of vowels (a, e, i, o, u in either case).
fn count_vowels(_s: &str) -> usize {
    todo!()
}

fn check<T: PartialEq + std::fmt::Debug>(label: &str, got: T, want: T) -> bool {
    let ok = got == want;
    if ok {
        println!("PASS {label}");
    } else {
        println!("FAIL {label}: got {got:?}, want {want:?}");
    }
    ok
}

fn main() {
    let mut kv = HashMap::new();
    kv.insert("a".to_string(), "1".to_string());
    kv.insert("b".to_string(), "two".to_string());
    let results = [
        check("palindrome", is_palindrome("A man, a plan, a canal: Panama"), true),
        check("not palindrome", is_palindrome("hello"), false),
        check("reverse_words", reverse_words("  the quick  brown fox "), "fox brown quick the".to_string()),
        check("caesar", caesar("Hello, World!", 3), "Khoor, Zruog!".to_string()),
        check("caesar neg", caesar("Khoor, Zruog!", -3), "Hello, World!".to_string()),
        check("title", title_case("hELLO wORLD  x"), "Hello World  X".to_string()),
        check("kv", parse_kv("a=1,b=two"), kv),
        check("kv empty", parse_kv("").len(), 0),
        check("vowels", count_vowels("Rustacean Éa"), 5),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

<details><summary>Solution</summary>

```rust file=solution.rs
use std::collections::HashMap;

fn is_palindrome(s: &str) -> bool {
    let cleaned: Vec<char> = s
        .chars()
        .filter(|c| c.is_alphanumeric())
        .flat_map(|c| c.to_lowercase())
        .collect();
    cleaned.iter().eq(cleaned.iter().rev())
}

fn reverse_words(s: &str) -> String {
    s.split_whitespace().rev().collect::<Vec<_>>().join(" ")
}

fn caesar(text: &str, shift: i32) -> String {
    let shift = shift.rem_euclid(26) as u8;
    text.chars()
        .map(|c| match c {
            'a'..='z' => ((c as u8 - b'a' + shift) % 26 + b'a') as char,
            'A'..='Z' => ((c as u8 - b'A' + shift) % 26 + b'A') as char,
            _ => c,
        })
        .collect()
}

fn title_case(s: &str) -> String {
    s.split(' ')
        .map(|w| {
            let mut chars = w.chars();
            match chars.next() {
                Some(first) => {
                    first.to_uppercase().collect::<String>() + &chars.as_str().to_lowercase()
                }
                None => String::new(),
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

fn parse_kv(line: &str) -> HashMap<String, String> {
    line.split(',')
        .filter(|p| !p.is_empty())
        .filter_map(|p| p.split_once('='))
        .map(|(k, v)| (k.to_string(), v.to_string()))
        .collect()
}

fn count_vowels(s: &str) -> usize {
    s.chars().filter(|c| "aeiouAEIOU".contains(*c)).count()
}

fn check<T: PartialEq + std::fmt::Debug>(label: &str, got: T, want: T) -> bool {
    let ok = got == want;
    if ok {
        println!("PASS {label}");
    } else {
        println!("FAIL {label}: got {got:?}, want {want:?}");
    }
    ok
}

fn main() {
    let mut kv = HashMap::new();
    kv.insert("a".to_string(), "1".to_string());
    kv.insert("b".to_string(), "two".to_string());
    let results = [
        check("palindrome", is_palindrome("A man, a plan, a canal: Panama"), true),
        check("not palindrome", is_palindrome("hello"), false),
        check("reverse_words", reverse_words("  the quick  brown fox "), "fox brown quick the".to_string()),
        check("caesar", caesar("Hello, World!", 3), "Khoor, Zruog!".to_string()),
        check("caesar neg", caesar("Khoor, Zruog!", -3), "Hello, World!".to_string()),
        check("title", title_case("hELLO wORLD  x"), "Hello World  X".to_string()),
        check("kv", parse_kv("a=1,b=two"), kv),
        check("kv empty", parse_kv("").len(), 0),
        check("vowels", count_vowels("Rustacean Éa"), 5),
    ];
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

</details>

Next: [06 — Structs and enums](06-structs-enums.md)
