# Go by Example (practice edition)

Go 1.23+. Each lesson is a single `package main` file: `go run file.go`.
Exercises use a tiny `check` helper and exit non-zero until solved.

| # | Lesson | You will practise |
|---|--------|-------------------|
| 01 | [Values](01-values.md) | types, zero values, constants, `Printf` verbs |
| 02 | [Control flow](02-control-flow.md) | `for`, `switch`, labels, type switch |
| 03 | [Functions](03-functions.md) | multiple returns, closures, `defer`, generics |
| 04 | [Collections](04-collections.md) | arrays, slices (len/cap/aliasing), maps, `slices` |
| 05 | [Strings](05-strings.md) | bytes vs runes, `strings`, `strconv`, `Builder` |
| 06 | [Structs and methods](06-structs.md) | receivers, embedding, constructors, JSON tags |
| 07 | [Errors](07-errors.md) | `errors.Is/As`, wrapping, typed-nil trap, `recover` |
| 08 | [Pointers and memory](08-pointers-memory.md) | `&`/`*`, escape analysis, struct layout |
| 09 | [Interfaces](09-interfaces.md) | implicit satisfaction, `io.Writer`, test doubles |
| 10 | [Files and I/O](10-files-io.md) | `os`, `bufio`, `encoding/json`, `exec` |
| 11 | [Concurrency](11-concurrency.md) | goroutines, channels, `sync`, `context` |
| 12 | [**Idiomatic Go**](12-idiomatic-go.md) | options, enums, zero values, the checklist |
| 13 | [Capstone: LRU cache](13-capstone-lru.md) | generics, `container/list`, maps |
