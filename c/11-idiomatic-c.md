# C 11 — Idiomatic C

Idiomatic C is *defensive and explicit*: make illegal states hard to
express, make ownership obvious, make the compiler and sanitizers do the
checking, and keep the surface area small. Good C reads like a contract.

## Example

```c file=example.c
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 1. X-macros: one list, many expansions (enum, names, tables) */
#define COLORS(X) \
    X(RED, "red")   \
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
    return (unsigned)c < COLOR_COUNT ? names[c] : "invalid"; /* bounds check */
}

/* 2. Compile-time assertions document and enforce assumptions */
_Static_assert(COLOR_COUNT == 3, "update the docs when adding a colour");
_Static_assert(sizeof(int32_t) == 4, "int32_t must be 4 bytes");

/* 3. Options structs + designated initialisers: no 7-argument functions */
struct options {
    const char *name;
    int retries;
    bool verbose;
};

static void show(const struct options *o) { /* const: read-only */
    printf("%s %d %d\n", o->name, o->retries, o->verbose);
}

/* 4. restrict promises the compiler the pointers do not alias */
static void add_arrays(size_t n, int *restrict out, const int *restrict a,
                       const int *restrict b) {
    for (size_t i = 0; i < n; i++) {
        out[i] = a[i] + b[i];
    }
}

/* 5. Constructor / destructor pair around an encapsulated type.
      The destroy function takes ptr-to-ptr so it can NULL the caller's. */
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
    printf("%s %s %s\n", color_name(COLOR_RED), color_name(COLOR_BLUE),
           color_name((enum color)9));

    struct options o = {.name = "job", .retries = 3}; /* the rest is zero */
    show(&o);

    int a[] = {1, 2, 3}, b[] = {10, 20, 30}, out[3];
    add_arrays(3, out, a, b);
    printf("%d %d %d\n", out[0], out[1], out[2]);

    ring *r = ring_create(3);
    if (!r) {
        return 1;
    }
    for (int i = 1; i <= 3; i++) {
        ring_push(r, i);
    }
    int v;
    bool pushed = ring_push(r, 4); /* full */
    ring_pop(r, &v);
    printf("push4=%d pop=%d\n", pushed, v);
    ring_push(r, 4);
    while (ring_pop(r, &v)) {
        printf("%d ", v);
    }
    printf("\n");
    ring_destroy(&r);
    printf("destroyed=%d\n", r == NULL);
    return 0;
}
```

```text output
red blue invalid
job 3 0
11 22 33
push4=0 pop=1
2 3 4 
destroyed=1
```

## The checklist

| Do | Avoid |
|----|-------|
| `-std=c11 -Wall -Wextra -Wpedantic -Werror` always | silencing warnings with casts |
| `-fsanitize=address,undefined` in dev and CI | "it works on my machine" |
| `size_t` for sizes and indexes | `int` indexes into big arrays |
| `sizeof *p` in `malloc(n * sizeof *p)` | `malloc(n * sizeof(int))` repeated |
| `const` on every pointer you only read | mutable-by-default parameters |
| `static` for file-private functions and data | accidental external linkage |
| `snprintf`, `memcpy` with explicit lengths | `strcpy`, `strcat`, `sprintf`, `gets` |
| Init at declaration, `= {0}` for structs | reading uninitialised locals |
| One exit via `goto cleanup` when owning resources | duplicated cleanup in every branch |
| Opaque types + `_create` / `_destroy` pairs | public structs with invariants |
| `enum` + `switch` without `default` (so `-Wswitch` warns) | `#define` integer constants |
| `bool` from `<stdbool.h>`, `uint8_t` etc. from `<stdint.h>` | `int` flags, `unsigned char` mystery |
| Designated initialisers and compound literals | positional init of big structs |
| Header guards (`#ifndef FOO_H`) and minimal includes | defining variables in headers |
| Document ownership: "caller frees", "borrowed" | ambiguous returned pointers |
| `static inline` functions | function-like macros with side effects |

## Details that bite

- Idioms vary by community (kernel, embedded, POSIX, game dev). The common
  core is above; follow your project's style guide first.
- Undefined behaviour is not an error you will see: it is a contract the
  optimiser assumes you kept. Sanitizers and static analysers
  (`clang-tidy`, `cppcheck`, `gcc -fanalyzer`) are your only reliable
  detectors.
- Prefer returning a status and writing results through a pointer over
  encoding errors in the result (`-1` that can be a valid value).
- Hide the struct body in the `.c` file whenever callers have no business
  touching the fields; it lets you change the layout without breaking
  anyone.
- Macros: parenthesise arguments and the whole expression, evaluate each
  argument once, wrap multi-statement macros in `do { … } while (0)`, and
  prefer `static inline` functions when types are known.
- Keep functions short with one level of abstraction. A 300-line function
  with six `goto`s is not idiomatic; it is a code smell with a label.
- `main` should mostly parse arguments and call into testable functions.

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
