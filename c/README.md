# C by Example (practice edition)

C11. Lessons are built with
`gcc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -g file.c -lm`
so that undefined behaviour and leaks fail loudly. Exercise stubs compile
but report `FAIL` until solved.

| # | Lesson | You will practise |
|---|--------|-------------------|
| 01 | [Values](01-values.md) | sizes, integer conversions, bit ops, `printf` |
| 02 | [Control flow](02-control-flow.md) | loops, `switch` fall-through, `goto` cleanup |
| 03 | [Functions](03-functions.md) | pass-by-value, out-params, `static`, variadics |
| 04 | [Arrays and collections](04-arrays.md) | decay, `qsort`, `bsearch`, growable vector |
| 05 | [Strings](05-strings.md) | `'\0'`, `snprintf`, `strtol`, `memmove` |
| 06 | [Structs, unions, enums](06-structs.md) | layout/padding, tagged unions, bit-fields |
| 07 | [Errors](07-errors.md) | return codes, `errno`, `goto` cleanup, `assert` |
| 08 | [Memory](08-memory.md) | `malloc`/`realloc`/`free`, ownership, arenas |
| 09 | [Abstraction](09-abstraction.md) | function pointers, callbacks, vtables, `_Generic` |
| 10 | [Files and I/O](10-files-io.md) | `FILE *`, binary I/O, `fgets`, `sscanf` |
| 11 | [**Idiomatic C**](11-idiomatic-c.md) | X-macros, opaque types, `restrict`, the checklist |
| 12 | [Threads](12-threads.md) | `pthreads`, mutexes, condition variables, C11 atomics |
| 13 | [Capstone: LRU cache](13-capstone-lru.md) | hash table + intrusive list, ownership |
