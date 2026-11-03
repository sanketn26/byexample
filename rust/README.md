# Rust by Example (practice edition)

Rust 2021 edition. Each lesson is a single file you can build with
`rustc --edition 2021 file.rs` (no Cargo needed). Exercise stubs call
`todo!()` until you implement them.

| # | Lesson | You will practise |
|---|--------|-------------------|
| 01 | [Values](01-values.md) | immutability, shadowing, checked arithmetic, `as` |
| 02 | [Control flow](02-control-flow.md) | expressions, `match`, `if let`, `let else` |
| 03 | [Functions and closures](03-functions.md) | `Fn`/`FnMut`/`FnOnce`, `impl Trait`, iterators |
| 04 | [Collections](04-collections.md) | `Vec`, slices, `HashMap`, entry API, `BTreeMap` |
| 05 | [Strings](05-strings.md) | `String` vs `&str`, UTF-8, char boundaries |
| 06 | [Structs and enums](06-structs-enums.md) | `impl`, data-carrying enums, derives |
| 07 | [Errors](07-errors.md) | `Result`, `?`, `From`, custom error types |
| 08 | [Ownership and borrowing](08-ownership.md) | moves, borrows, lifetimes, `Drop`, `Rc`/`RefCell` |
| 09 | [Traits and generics](09-traits.md) | bounds, `dyn`, operators, `Iterator`, `FromStr` |
| 10 | [Files and I/O](10-files-io.md) | `Read`/`Write`, `BufReader`, paths, processes |
| 11 | [Concurrency](11-concurrency.md) | threads, scope, channels, `Arc<Mutex>`, atomics |
| 12 | [**Idiomatic Rust**](12-idiomatic-rust.md) | combinators, builders, type-state, the checklist |
| 13 | [Testing](13-testing.md) | `#[test]`, `rustc --test`, `Result` tests, trait fakes, `catch_unwind` |
| 14 | [Capstone: LRU cache](14-capstone-lru.md) | index-linked list arena + `HashMap` |
| 15 | [Streaming](15-streaming.md) | short reads and writes, frames, atomic replace |
| 16 | [Network programming](16-network.md) | `std::net`, frames, timeouts, HTTP/1.1 by hand |
| 17 | [Advanced concurrency](17-advanced-concurrency.md) | bounded pools, deadlines, backpressure, shutdown |

Lessons 15–17 are the outside world: bytes in chunks, a socket, and a bound
on how many of those you handle at once. Async Rust (Tokio) needs Cargo, so
lesson 16 stays on `std::net` and threads.
