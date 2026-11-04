# Python by Example

Python 3.12+. Each lesson is a series of tiny programs, one concept each:
`python3 n01.py`, then `n02.py`.

| # | Lesson | You will practise |
|---|--------|-------------------|
| 01 | [Values](01-values.md) | numbers, truthiness, f-strings, unpacking |
| 02 | [Control flow](02-control-flow.md) | `for`/`while`/`match`, comprehensions |
| 03 | [Functions](03-functions.md) | closures, decorators, generators, mutable-default trap |
| 04 | [Collections](04-collections.md) | list/tuple/dict/set, `Counter`, slicing, copies |
| 05 | [Strings](05-strings.md) | Unicode, formatting, `re`, `str` vs `bytes` |
| 06 | [Classes](06-classes.md) | dataclasses, dunders, properties, `__slots__` |
| 07 | [Errors](07-errors.md) | `try`/`except`, chaining, context managers |
| 08 | [References and memory](08-references-memory.md) | identity, mutability, refcounts, `gc`, `weakref` |
| 09 | [Protocols](09-protocols.md) | duck typing, `ABC`, `Protocol`, `singledispatch` |
| 10 | [Files and I/O](10-files-io.md) | `pathlib`, JSON, CSV, `subprocess` |
| 11 | [**The Pythonic way**](11-pythonic.md) | idioms, `itertools`, `functools`, the checklist |
| 12 | [asyncio](12-asyncio.md) | tasks, `gather`, `TaskGroup`, queues, cancellation |
| 13 | [Testing](13-testing.md) | `unittest`, fakes, `mock`, `doctest`, dependency injection |
| 14 | [Capstone: LRU cache](14-capstone-lru.md) | a real data structure, start to finish |
| 15 | [Streaming](15-streaming.md) | short reads and writes, frames, atomic replace |
| 16 | [Network programming](16-network.md) | TCP frames, timeouts, HTTP/1.1, asyncio streams |
| 17 | [Advanced concurrency](17-advanced-concurrency.md) | bounded pools, deadlines, backpressure, shutdown |

Start at 01, or jump to 11 if you already know the language and want the
idioms.

Lessons 15–17 are the outside world: bytes in chunks, a socket, and a bound
on how many of those you handle at once.
