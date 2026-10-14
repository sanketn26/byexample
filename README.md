# By Example — a practice-first programming course

Learn **Python, Go, Rust and C** the *by example* way: every lesson is a
short, annotated, runnable program with its real output, the details that
trip people up, and graded exercises with a hidden solution. Light on
theory, heavy on practice, and nothing important left out.

| Language | Start here | Lessons |
|----------|-----------|---------|
| Python 3.12 | [python/](python/README.md) | 14 (incl. *The Pythonic Way*, asyncio, testing, capstone) |
| Go 1.23+ | [go/](go/README.md) | 13 (incl. concurrency, *Idiomatic Go*, capstone) |
| Rust 2021 | [rust/](rust/README.md) | 13 (incl. concurrency, *Idiomatic Rust*, capstone) |
| C11 | [c/](c/README.md) | 13 (incl. threads, *Idiomatic C*, capstone) |

Every language follows the same arc, so you can learn a second language by
walking the same path:

| # | Topic | Question it answers |
|---|-------|---------------------|
| 01 | Values | What are the types, and how do I print them? |
| 02 | Control flow | How do I branch and loop? |
| 03 | Functions | How do I package behaviour? |
| 04 | Collections | Lists, maps, sets: what is built in? |
| 05 | Strings | What is a string *really* (bytes, code points)? |
| 06 | Structs / classes | How do I model data? |
| 07 | Errors | How does failure travel? |
| 08 | Memory / references | Who owns what, and for how long? |
| 09 | Abstraction | Interfaces, traits, protocols, vtables |
| 10 | Files and I/O | Talk to the outside world |
| 11+ | Concurrency, **Idiomatic X**, testing, capstone (LRU cache) | Write it the way experts do |

## Anatomy of a lesson

Each lesson is one Markdown file:

1. **Example** — a complete program, commented line by line.
2. **Output** — exactly what it prints, so you can predict before running.
3. **Details that bite** — the gotchas, undefined behaviour, and
   "why does it do that" notes.
4. **Exercises** — a starter file whose tests fail until you fix it. Run
   it; make every line say `PASS`.
5. **Solution** — folded away. Try first.

## How to practise

```sh
# pull the example and exercise files out of a lesson
make extract LESSON=go/04-collections.md        # writes ./work/go-04-collections/

cd work/go-04-collections
go run example.go                               # read it, run it, change it
$EDITOR exercise.go && go run exercise.go       # make it all PASS

make extract LESSON=go/04-collections.md SOLUTION=1   # peek when stuck
```

The run command for each language is printed by `make extract`. Or just
copy the code blocks straight out of the Markdown.

## Verified, not hand-waved

Every code block in this repository is executed by CI-style tooling:

```sh
make verify            # all languages
make verify-rust       # one language
```

`tools/verify.py` extracts each lesson's blocks, builds them, checks that

* the **example** compiles and prints exactly the documented output,
* the **solution** compiles and passes all its checks, and
* the **exercise** compiles but *fails* until solved.

Toolchains it needs on `PATH`: `python3` (3.12+), `go` (1.23+), `rustc`
(2021 edition, built with `-D warnings`), `gcc` (C11, built with
`-Wall -Wextra -Werror -fsanitize=address,undefined`).

## Contributing a lesson

* Put the file at `<lang>/NN-topic.md`.
* Use fences with `file=` for code (`example.*`, `exercise.*`,
  `solution.*`) and ```` ```text output ```` for expected output.
* Exercises print `PASS`/`FAIL` per check and exit non-zero on any failure.
* Run `make verify-<lang>` before opening a PR.
