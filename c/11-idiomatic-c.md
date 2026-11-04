# C 11 — Idiomatic C

Idiomatic C is defensive and explicit: make illegal states hard to
express, make ownership obvious, and keep the surface small. Communities
disagree on the details (kernel, embedded, POSIX, games). Follow the
project's style guide first. The common core is below.

Build with `-std=c11 -Wall -Wextra -Wpedantic -Werror`, and with
`-fsanitize=address,undefined` in development and CI. Do not silence a
warning with a cast. Undefined behaviour is not an error you will see; it
is a contract the optimiser assumes you kept. Sanitizers and analysers
(`clang-tidy`, `cppcheck`, `gcc -fanalyzer`) are the detectors.

Use `size_t` for sizes and indexes, `bool` from `<stdbool.h>`, and
`uint8_t` and the rest from `<stdint.h>`. Initialize at the declaration,
and zero a struct with `= {0}`. Put `const` on every pointer you only
read, and `static` on file-private functions and data. Prefer `snprintf`
and `memcpy` with a length to `strcpy`, `strcat`, `sprintf`, and `gets`.
Prefer an enum to a `#define` integer constant. Document ownership
("caller frees", "borrowed"). Hide a struct in the `.c` file when callers
must not touch the fields. Headers get an include guard and the minimum
includes, and they do not define variables. Return a status and write the
result through a pointer when the obvious error value, such as `-1`, can
also be a real result. One `goto cleanup` beats a copy of the same
`free`s in every branch. Keep functions short and at one level of
abstraction: a 300-line function with six labels is a smell. `main`
should parse arguments and call something you can test.

## One list expands into the enum and the names

An X-macro is the exception to "prefer a function": the list has to be
text, because it is generated twice. The name table is indexed by the
enum. Anything outside the range is rejected, not read off the end.
A `switch` on an enum with no `default` lets `-Wswitch` tell you when a
new enumerator is unhandled. That is the same idea as this bounds check.

```c file=n01.c
#include <stdio.h>

#define COLORS(X) \
    X(RED, "red") \
    X(GREEN, "green") \
    X(BLUE, "blue")

enum color {
#define X(id, name) COLOR_##id,
    COLORS(X)
#undef X
    COLOR_COUNT
};

static const char *color_name(enum color c) {
    static const char *const names[COLOR_COUNT] = {
#define X(id, name) [COLOR_##id] = name,
        COLORS(X)
#undef X
    };
    return (unsigned)c < COLOR_COUNT ? names[c] : "invalid";
}

int main(void) {
    printf("%s %s %s\n", color_name(COLOR_RED), color_name(COLOR_BLUE),
           color_name((enum color)9));
    return 0;
}
```

```text output
red blue invalid
```

## A function evaluates its argument once

A function-like macro substitutes text. Parenthesize every argument and
the whole expression, and if the macro is several statements, wrap it in
`do { ... } while (0)`. It still evaluates each argument every time that
argument appears. A `static inline` function evaluates once and keeps the
type. Use the macro only when you must, as with the X-macro above.

```c file=n02.c
#include <stdio.h>

static inline int square(int x) { return x * x; }

int main(void) {
    int n = 4;
    printf("%d\n", square(n));
    return 0;
}
```

```text output
16
```

## _Static_assert runs at compile time

The program does not print the assertion. If `COLOR_COUNT` were not 3,
or `int32_t` were not 4 bytes, this file would not build. That is the
point: the assumption is next to the code, and it fails closed.

```c file=n03.c
#include <stdint.h>
#include <stdio.h>

enum { COLOR_COUNT = 3 };

_Static_assert(COLOR_COUNT == 3, "update the docs when adding a colour");
_Static_assert(sizeof(int32_t) == 4, "int32_t must be 4 bytes");

int main(void) {
    printf("%d %zu\n", COLOR_COUNT, sizeof(int32_t));
    return 0;
}
```

```text output
3 4
```

## An options struct replaces a long parameter list

Designated initializers set what you care about and zero the rest, so
`verbose` is false without being named. The callee takes `const` because
it only reads. Adding a field later does not break every call site.

```c file=n04.c
#include <stdbool.h>
#include <stdio.h>

struct options {
    const char *name;
    int retries;
    bool verbose;
};

static void show(const struct options *o) {
    printf("%s %d %d\n", o->name, o->retries, o->verbose);
}

int main(void) {
    struct options o = {.name = "job", .retries = 3};
    show(&o);
    return 0;
}
```

```text output
job 3 0
```

## restrict promises the pointers do not alias

The compiler may then keep values in registers across the loop. You are
promising that `out`, `a`, and `b` do not overlap. Breaking the promise
is undefined.

```c file=n05.c
#include <stddef.h>
#include <stdio.h>

static void add_arrays(size_t n, int *restrict out, const int *restrict a,
                       const int *restrict b) {
    for (size_t i = 0; i < n; i++) {
        out[i] = a[i] + b[i];
    }
}

int main(void) {
    int a[] = {1, 2, 3}, b[] = {10, 20, 30}, out[3];
    add_arrays(3, out, a, b);
    printf("%d %d %d\n", out[0], out[1], out[2]);
    return 0;
}
```

```text output
11 22 33
```

## create and destroy own the object

`calloc` zeroes, and `sizeof *r` tracks the type. Capacity zero is
rejected. `ring_destroy` takes `ring **` so it can set the caller's
pointer to `NULL`, and it is safe on a null pointer. The struct can stay
opaque in a header (`typedef struct ring ring;`) while the body lives
here. The caller frees by calling destroy, not by freeing the fields.

```c file=n06.c
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct ring ring;
struct ring {
    int *buf;
    size_t cap, head, len;
};

static ring *ring_create(size_t cap) {
    if (cap == 0) {
        return NULL;
    }
    ring *r = calloc(1, sizeof *r);
    if (!r) {
        return NULL;
    }
    r->buf = calloc(cap, sizeof *r->buf);
    if (!r->buf) {
        free(r);
        return NULL;
    }
    r->cap = cap;
    return r;
}

static bool ring_push(ring *r, int v) {
    if (r->len == r->cap) {
        return false;
    }
    r->buf[(r->head + r->len) % r->cap] = v;
    r->len++;
    return true;
}

static bool ring_pop(ring *r, int *out) {
    if (r->len == 0) {
        return false;
    }
    *out = r->buf[r->head];
    r->head = (r->head + 1) % r->cap;
    r->len--;
    return true;
}

static void ring_destroy(ring **r) {
    if (!r || !*r) {
        return;
    }
    free((*r)->buf);
    free(*r);
    *r = NULL;
}

int main(void) {
    if (ring_create(0) != NULL) {
        return 1;
    }
    ring *r = ring_create(3);
    if (!r) {
        return 1;
    }
    for (int i = 1; i <= 3; i++) {
        ring_push(r, i);
    }
    int v = 0;
    bool pushed = ring_push(r, 4);
    ring_pop(r, &v);
    printf("push4=%d pop=%d\n", pushed, v);
    ring_push(r, 4);
    while (ring_pop(r, &v)) {
        printf("%d ", v);
    }
    printf("\n");
    ring_destroy(&r);
    printf("destroyed=%d\n", r == NULL);
    ring_destroy(&r);
    return 0;
}
```

```text output
push4=0 pop=1
2 3 4 
destroyed=1
```

## A header guard includes the file once

`#ifndef` / `#define` / `#endif` make a second `#include` of the same
header a no-op. Without the guard, two includes of a file that defines
an object are a redefinition error. Do not put a non-`static` variable
definition in a header: every file that includes it would export that
symbol.

```c file=guard.h
#ifndef GUARD_H
#define GUARD_H
static const int guarded = 7;
#endif
```

```c file=n07.c
#include "guard.h"
#include "guard.h"
#include <stdio.h>

int main(void) {
    printf("%d\n", guarded);
    return 0;
}
```

```text output
7
```

## `snprintf` writes a number into a buffer

The size argument includes the terminating `'\0'`. Check the return
when the buffer might be too small; here 16 bytes is enough for `42`.

```c file=n08.c
#include <stdio.h>

int main(void) {
    char buf[16];
    snprintf(buf, sizeof buf, "%d", 42);
    printf("%s\n", buf);
    return 0;
}
```

```text output
42
```

## `getenv` returns NULL when the name is unset

`setenv` puts a value in the process environment. A missing name is
`NULL`, so the caller picks the default. Do not free the pointer
`getenv` returns.

```c file=n09.c
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    setenv("APP_PORT", "8080", 1);
    const char *port = getenv("APP_PORT");
    const char *missing = getenv("APP_MISSING");
    printf("%s %s\n", port, missing ? missing : "80");
    return 0;
}
```

```text output
8080 80
```

## Exercises

```c file=exercise.c
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* A fixed-capacity FIFO ring buffer of ints with create/destroy. */
struct ring {
    int *buf;
    size_t cap, head, len;
};

/* NULL when cap == 0 or allocation fails. */
struct ring *ring_create(size_t cap) {
    (void)cap;
    return NULL; /* TODO */
}

/* false when full. */
bool ring_push(struct ring *r, int v) {
    (void)r; (void)v;
    return true; /* TODO */
}

/* false when empty; otherwise stores the oldest value in *out. */
bool ring_pop(struct ring *r, int *out) {
    (void)r; (void)out;
    return true; /* TODO */
}

size_t ring_len(const struct ring *r) {
    (void)r;
    return 99; /* TODO */
}

/* Frees the ring and sets *r to NULL. Safe on NULL or already-NULL. */
void ring_destroy(struct ring **r) {
    (void)r; /* TODO */
}

enum weekday { MON, TUE, WED, THU, FRI, SAT, SUN, WEEKDAY_COUNT };

/* "Mon".."Sun" using a table; "?" for out-of-range values. */
const char *weekday_name(enum weekday d) {
    (void)d;
    return ""; /* TODO */
}

struct options {
    char name[16];
    int retries;
    bool verbose;
};

/* name "default", retries 3, verbose false. */
struct options options_default(void) {
    return (struct options){0}; /* TODO */
}

/* Apply "retries=N", "verbose=0|1" or "name=TEXT" (TEXT < 16 chars).
   0 on success, -1 on unknown key, bad value, or missing '='. */
int options_set(struct options *o, const char *kv) {
    (void)o; (void)kv;
    return 0; /* TODO */
}

static int failed;
#define CHECK(label, cond)                         \
    do {                                           \
        if (cond) {                                \
            printf("PASS %s\n", label);            \
        } else {                                   \
            failed = 1;                            \
            printf("FAIL %s\n", label);            \
        }                                          \
    } while (0)

int main(void) {
    CHECK("create 0", ring_create(0) == NULL);
    struct ring *r = ring_create(3);
    CHECK("create", r != NULL);
    int v = -1;
    CHECK("pop empty", r && !ring_pop(r, &v));
    for (int i = 1; i <= 3; i++) {
        if (r) {
            ring_push(r, i * 10);
        }
    }
    CHECK("len", r && ring_len(r) == 3);
    CHECK("push full", r && !ring_push(r, 99));
    CHECK("fifo", r && ring_pop(r, &v) && v == 10);
    CHECK("wraparound", r && ring_push(r, 40) && ring_len(r) == 3);
    int got[3] = {0};
    for (int i = 0; i < 3 && r; i++) {
        ring_pop(r, &got[i]);
    }
    CHECK("order", got[0] == 20 && got[1] == 30 && got[2] == 40);
    ring_destroy(&r);
    CHECK("destroy nulls", r == NULL);
    ring_destroy(&r);
    ring_destroy(NULL);

    CHECK("weekday", strcmp(weekday_name(MON), "Mon") == 0 && strcmp(weekday_name(SUN), "Sun") == 0);
    CHECK("weekday invalid", strcmp(weekday_name((enum weekday)42), "?") == 0);

    struct options o = options_default();
    CHECK("defaults", strcmp(o.name, "default") == 0 && o.retries == 3 && !o.verbose);
    CHECK("set retries", options_set(&o, "retries=5") == 0 && o.retries == 5);
    CHECK("set verbose", options_set(&o, "verbose=1") == 0 && o.verbose);
    CHECK("set name", options_set(&o, "name=job") == 0 && strcmp(o.name, "job") == 0);
    CHECK("bad key", options_set(&o, "color=red") == -1);
    CHECK("bad value", options_set(&o, "retries=abc") == -1);
    CHECK("no equals", options_set(&o, "retries") == -1);
    CHECK("name too long", options_set(&o, "name=abcdefghijklmnopqrstuvwxyz") == -1);
    return failed;
}
```

<details><summary>Solution</summary>

```c file=solution.c
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct ring {
    int *buf;
    size_t cap, head, len;
};

struct ring *ring_create(size_t cap) {
    if (cap == 0) {
        return NULL;
    }
    struct ring *r = calloc(1, sizeof *r);
    if (!r) {
        return NULL;
    }
    r->buf = calloc(cap, sizeof *r->buf);
    if (!r->buf) {
        free(r);
        return NULL;
    }
    r->cap = cap;
    return r;
}

bool ring_push(struct ring *r, int v) {
    if (r->len == r->cap) {
        return false;
    }
    r->buf[(r->head + r->len) % r->cap] = v;
    r->len++;
    return true;
}

bool ring_pop(struct ring *r, int *out) {
    if (r->len == 0) {
        return false;
    }
    *out = r->buf[r->head];
    r->head = (r->head + 1) % r->cap;
    r->len--;
    return true;
}

size_t ring_len(const struct ring *r) {
    return r->len;
}

void ring_destroy(struct ring **r) {
    if (!r || !*r) {
        return;
    }
    free((*r)->buf);
    free(*r);
    *r = NULL;
}

enum weekday { MON, TUE, WED, THU, FRI, SAT, SUN, WEEKDAY_COUNT };

const char *weekday_name(enum weekday d) {
    static const char *const names[WEEKDAY_COUNT] = {
        [MON] = "Mon", [TUE] = "Tue", [WED] = "Wed", [THU] = "Thu",
        [FRI] = "Fri", [SAT] = "Sat", [SUN] = "Sun",
    };
    return (unsigned)d < WEEKDAY_COUNT ? names[d] : "?";
}

struct options {
    char name[16];
    int retries;
    bool verbose;
};

struct options options_default(void) {
    struct options o = {.retries = 3, .verbose = false};
    strcpy(o.name, "default"); /* fits: 8 bytes into 16 */
    return o;
}

int options_set(struct options *o, const char *kv) {
    const char *eq = strchr(kv, '=');
    if (!eq) {
        return -1;
    }
    size_t klen = (size_t)(eq - kv);
    const char *val = eq + 1;
    if (klen == 7 && strncmp(kv, "retries", 7) == 0) {
        char *end;
        long n = strtol(val, &end, 10);
        if (*val == '\0' || *end != '\0' || n < 0 || n > 1000000) {
            return -1;
        }
        o->retries = (int)n;
        return 0;
    }
    if (klen == 7 && strncmp(kv, "verbose", 7) == 0) {
        if (strcmp(val, "0") == 0) {
            o->verbose = false;
        } else if (strcmp(val, "1") == 0) {
            o->verbose = true;
        } else {
            return -1;
        }
        return 0;
    }
    if (klen == 4 && strncmp(kv, "name", 4) == 0) {
        size_t n = strlen(val);
        if (n >= sizeof o->name) {
            return -1;
        }
        memcpy(o->name, val, n + 1);
        return 0;
    }
    return -1;
}

static int failed;
#define CHECK(label, cond)                         \
    do {                                           \
        if (cond) {                                \
            printf("PASS %s\n", label);            \
        } else {                                   \
            failed = 1;                            \
            printf("FAIL %s\n", label);            \
        }                                          \
    } while (0)

int main(void) {
    CHECK("create 0", ring_create(0) == NULL);
    struct ring *r = ring_create(3);
    CHECK("create", r != NULL);
    int v = -1;
    CHECK("pop empty", r && !ring_pop(r, &v));
    for (int i = 1; i <= 3; i++) {
        if (r) {
            ring_push(r, i * 10);
        }
    }
    CHECK("len", r && ring_len(r) == 3);
    CHECK("push full", r && !ring_push(r, 99));
    CHECK("fifo", r && ring_pop(r, &v) && v == 10);
    CHECK("wraparound", r && ring_push(r, 40) && ring_len(r) == 3);
    int got[3] = {0};
    for (int i = 0; i < 3 && r; i++) {
        ring_pop(r, &got[i]);
    }
    CHECK("order", got[0] == 20 && got[1] == 30 && got[2] == 40);
    ring_destroy(&r);
    CHECK("destroy nulls", r == NULL);
    ring_destroy(&r);
    ring_destroy(NULL);

    CHECK("weekday", strcmp(weekday_name(MON), "Mon") == 0 && strcmp(weekday_name(SUN), "Sun") == 0);
    CHECK("weekday invalid", strcmp(weekday_name((enum weekday)42), "?") == 0);

    struct options o = options_default();
    CHECK("defaults", strcmp(o.name, "default") == 0 && o.retries == 3 && !o.verbose);
    CHECK("set retries", options_set(&o, "retries=5") == 0 && o.retries == 5);
    CHECK("set verbose", options_set(&o, "verbose=1") == 0 && o.verbose);
    CHECK("set name", options_set(&o, "name=job") == 0 && strcmp(o.name, "job") == 0);
    CHECK("bad key", options_set(&o, "color=red") == -1);
    CHECK("bad value", options_set(&o, "retries=abc") == -1);
    CHECK("no equals", options_set(&o, "retries") == -1);
    CHECK("name too long", options_set(&o, "name=abcdefghijklmnopqrstuvwxyz") == -1);
    return failed;
}
```

</details>

Next: [12 — Threads](12-threads.md)
