# Rust 05 — Strings

Two main string types: `String` (owned, growable) and `&str` (a borrowed
view). Both are always valid UTF-8, so byte length, `char` count and
"visible characters" are three different things.

## Example

```rust file=example.rs
fn shout(s: &str) -> String {
    s.to_uppercase() + "!"
}

fn main() {
    let s = String::from("héllo, 世界");
    println!("{} {}", s.len(), s.chars().count()); // bytes vs chars
    println!("{} {:?}", &s[0..1], s.char_indices().nth(2));
    println!("{:?}", s.chars().rev().collect::<String>());
    println!("{}", s.to_uppercase());

    // Building
    let mut t = String::new();
    t.push_str("ab");
    t.push('c');
    t += "de";
    t.insert(0, '>');
    println!("{t} {}", t.len());

    // Splitting and trimming
    println!(
        "{:?} {:?}",
        "a,b,,c".split(',').collect::<Vec<_>>(),
        "  x y  ".split_whitespace().collect::<Vec<_>>()
    );
    println!("{:?} {:?}", "key=value".split_once('='), "novalue".split_once('='));
    println!("{} {} {}", "  pad ".trim(), "xxhixx".trim_matches('x'), "Hello".replace('l', "L"));
    println!("{:?} {:?}", "hello".find("ll"), "hello".find('z'));
    println!("{} {}", "abc" < "abd", "Zebra".to_lowercase() == "zebra");

    let words = vec!["a", "b", "c"];
    println!("{}", words.join("-"));

    // Parsing
    println!("{:?}", "42".parse::<i32>());
    println!("{}", "4x".parse::<i32>().is_err());

    // Slicing mid-character would panic; `get` returns None instead
    println!("{:?} {:?}", s.get(1..2), s.get(1..3));

    // Bytes and UTF-8 validation
    println!("{:?}", "hi".bytes().collect::<Vec<u8>>());
    println!("{}", String::from_utf8(vec![104, 105]).unwrap());
    println!("{}", String::from_utf8(vec![0xff]).is_err());

    // format!
    let name = "Ada";
    let msg = format!("{name:>6}|{:<6}|{:^6}|", "x", "y");
    println!("{msg}");

    // chars
    println!(
        "{} {} {:?} {}",
        'a'.is_alphabetic(),
        '9'.to_digit(10).unwrap(),
        'ß'.to_uppercase().collect::<String>(),
        (b'a' + 2) as char
    );

    // &String coerces to &str, so take &str in parameters
    let owned = String::from("hey");
    println!("{} {}", shout(&owned), shout("lit"));
}
```

```text output
14 9
h Some((3, 'l'))
"界世 ,olléh"
HÉLLO, 世界
>abcde 6
["a", "b", "", "c"] ["x", "y"]
Some(("key", "value")) None
pad hi HeLLo
Some(2) None
true true
a-b-c
Ok(42)
true
None Some("é")
[104, 105]
hi
true
   Ada|x     |  y   |
true 9 "SS" c
HEY! LIT!
```

## Details that bite

- `s[i]` does not exist: strings are not indexable by integer because a
  byte offset may land inside a character. Use `.chars().nth(i)`,
  `.char_indices()`, or byte slicing on known boundaries.
- Slicing `&s[a..b]` panics if `a` or `b` is not a character boundary.
  `s.get(a..b)` returns `None` instead.
- `String + &str` moves the left side: `let c = a + &b;` makes `a`
  unusable. Use `format!` when you want to keep everything.
- Comparing/sorting is by bytes, not by locale; `to_lowercase()` is
  Unicode-aware but not a full case-fold.
- "User-perceived characters" (grapheme clusters) need the
  `unicode-segmentation` crate; `chars()` yields code points.
- `String::from_utf8_lossy` replaces invalid sequences with `�`;
  `OsString`/`Path` exist for non-UTF-8 file names.
- Function parameters should usually be `&str`; return `String` when you
  produce new text.

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
