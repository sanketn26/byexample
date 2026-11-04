# Go by Example (practice edition)

Go 1.23+. Each lesson is a series of tiny `package main` programs, one concept
each: `go run n01.go`, then `n02.go`.
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
| 13 | [Testing](13-testing.md) | `testing`, table-driven tests, fakes, `httptest`-style injection |
| 14 | [Capstone: LRU cache](14-capstone-lru.md) | generics, `container/list`, maps |
| 15 | [Streaming](15-streaming.md) | short reads and writes, frames, atomic replace |
| 16 | [Network programming](16-network.md) | TCP frames, deadlines, `net/http` |
| 17 | [Advanced concurrency](17-advanced-concurrency.md) | bounded pools, `context`, backpressure, shutdown |

Lessons 15–17 are the outside world: bytes in chunks, a socket, and a bound
on how many of those you handle at once.
