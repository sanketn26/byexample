# C 13 — Testing

C has no standard test framework. What it has is `assert` and `main`. A test harness is about thirty lines: a `CHECK` macro that records a failure and carries on, an array of `{name, function}`, and a loop. Build it once, build it small, and keep the habits that do the real work: table-driven cases, one behaviour per test, and every outside dependency passed in as a function pointer.

## Example

```c file=example.c
#include <assert.h>
#include <ctype.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 1. The code under test: plain functions, no test hooks. */
static void slugify(const char *in, char *out, size_t cap) {
    size_t n = 0;
    int dash = 0;
    for (; *in && n + 1 < cap; in++) {
        if (isalnum((unsigned char)*in)) {
            out[n++] = (char)tolower((unsigned char)*in);
            dash = 0;
        } else if (!dash && n > 0) {
            out[n++] = '-';
            dash = 1;
        }
    }
    while (n > 0 && out[n - 1] == '-') n--;
    out[n] = '\0';
}

/* Returns 0 and sets *out, or -1 with errno = EINVAL / ERANGE. */
static int parse_port(const char *s, int *out) {
    char *end;
    errno = 0;
    long n = strtol(s, &end, 10);
    if (end == s || *end != '\0') { errno = EINVAL; return -1; }
    if (n < 1 || n > 65535)       { errno = ERANGE; return -1; }
    *out = (int)n;
    return 0;
}

/* 2. Inject what the code cannot control (time, output) as a function pointer. */
typedef int (*hour_fn)(void *ctx);

static void greet(hour_fn hour, void *ctx, const char *name, char *out, size_t cap) {
    snprintf(out, cap, "good %s, %s", hour(ctx) < 12 ? "morning" : "evening", name);
}

static int fake_hour(void *ctx) { return *(int *)ctx; }

/* 3. A miniature test harness: CHECK records a failure and carries on. */
static int failures;     /* failed checks in the current test */
static char first_msg[160];

#define CHECK(cond, ...)                                         \
    do {                                                         \
        if (!(cond)) {                                           \
            if (!failures++) snprintf(first_msg, sizeof first_msg, __VA_ARGS__); \
        }                                                        \
    } while (0)

typedef struct { const char *name; void (*fn)(void); } Test;

static int run(const Test *tests, int n) {
    int passed = 0;
    for (int i = 0; i < n; i++) {
        failures = 0;
        tests[i].fn();
        if (failures) {
            printf("FAIL %s: %s\n", tests[i].name, first_msg);
        } else {
            printf("PASS %s\n", tests[i].name);
            passed++;
        }
    }
    printf("%d/%d passed\n", passed, n);
    return passed;
}

/* 4. Table-driven tests: one array of cases, one loop. */
static void test_slugify(void) {
    static const struct { const char *in, *want; } cases[] = {
        {"Hello World", "hello-world"},
        {"  C, is -- fun!  ", "c-is-fun"},
        {"", ""},
        {"Top 10", "top-10"},
    };
    char got[64];
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; i++) {
        slugify(cases[i].in, got, sizeof got);
        CHECK(strcmp(got, cases[i].want) == 0,
              "slugify(\"%s\") = \"%s\", want \"%s\"", cases[i].in, got, cases[i].want);
    }
}

static void test_parse_port(void) {
    int p = 0;
    CHECK(parse_port("8080", &p) == 0 && p == 8080, "8080 gave %d", p);
    CHECK(parse_port("x", &p) == -1 && errno == EINVAL, "x should be EINVAL");
    CHECK(parse_port("70000", &p) == -1 && errno == ERANGE, "70000 should be ERANGE");
}

static void test_greet(void) {
    char out[64];
    int h = 9;
    greet(fake_hour, &h, "Ada", out, sizeof out);
    CHECK(strcmp(out, "good morning, Ada") == 0, "got \"%s\"", out);
    h = 20;
    greet(fake_hour, &h, "Bob", out, sizeof out);
    CHECK(strcmp(out, "good evening, Bob") == 0, "got \"%s\"", out);
}

int main(void) {
    const Test tests[] = {
        {"slugify", test_slugify},
        {"parse_port", test_parse_port},
        {"greet", test_greet},
    };
    run(tests, 3);

    /* A failing check names the input, the result and the expectation. */
    char got[16];
    slugify("A b", got, sizeof got);
    failures = 0;
    CHECK(strcmp(got, "a_b") == 0, "slugify(\"A b\") = \"%s\", want \"a_b\"", got);
    printf("caught: %s\n", first_msg);

    /* assert() is the other tool: it aborts, so it guards invariants, not cases. */
    assert(failures == 1);
    return 0;
}
```

```text output
PASS slugify
PASS parse_port
PASS greet
3/3 passed
caught: slugify("A b") = "a-b", want "a_b"
```

## Details that bite

- **`assert` is not a test framework.** It aborts at the first failure, prints a location and nothing about which case, and vanishes under `-DNDEBUG`. Use it for invariants in the code under test, and a `CHECK`-style macro for test cases so one run reports every failure.
- **Macros need `do { ... } while (0)`.** It makes `CHECK(...)` behave as one statement, so `if (x) CHECK(...); else ...` parses. The format arguments are passed through `__VA_ARGS__` to `snprintf`.
- **Record the first message, count the rest.** The harness keeps one buffer for the first failure per test. That is enough to find the bug, and a flood of follow-on messages usually is not.
- **Function pointer plus `void *ctx`** is C's version of an interface with state. The fake clock reads an `int` or `double` the test owns, so the test moves time by assigning to a local.
- **Run the tests under the sanitizers.** The verifier builds with `-fsanitize=address,undefined`. A test that passes while reading past a buffer is worse than one that fails, and the sanitizers turn it into a failure.
- **Return codes are testable, `exit` is not.** Code that calls `exit(1)` on bad input cannot be tested in-process. Return an error, as `parse_port` does, and let `main` decide. If you must test an abort, `fork()` and check the child's status.
- **Exit status is the contract.** `main` returns non-zero when anything failed, so `make test` and CI see it without parsing output.

## Exercises

Write `parse_duration` and `rl_allow`. The harness and tests are given. Make every line say `PASS`. A call exactly `window` seconds after an earlier one no longer counts against the limit, and denied calls are not recorded.

```c file=exercise.c
#include <stdio.h>
#include <string.h>

/* parse_duration reads "1h30m", "45s", "2h" into seconds.
   Returns 0 and sets *out, or -1 on "", "10", "5x", "h" and other bad input. */
static int parse_duration(const char *s, long *out) {
    (void)s;
    *out = 0;
    return 0; /* TODO */
}

#define MAX_CALLS 16

typedef double (*clock_fn)(void *ctx);

/* RateLimiter allows `limit` calls per `window` seconds (limit <= MAX_CALLS).
   A call exactly `window` seconds after an earlier one no longer counts.
   Denied calls are not recorded. */
typedef struct {
    int limit;
    double window;
    clock_fn clock;
    void *ctx;
    double calls[MAX_CALLS];
    int n;
} RateLimiter;

static void rl_init(RateLimiter *r, int limit, double window, clock_fn clock, void *ctx) {
    r->limit = limit;
    r->window = window;
    r->clock = clock;
    r->ctx = ctx;
    r->n = 0;
}

static int rl_allow(RateLimiter *r) {
    (void)r;
    return 1; /* TODO */
}

static double fake_now(void *ctx) { return *(double *)ctx; }

static int failures;
static char first_msg[160];

#define CHECK(cond, ...)                                         \
    do {                                                         \
        if (!(cond)) {                                           \
            if (!failures++) snprintf(first_msg, sizeof first_msg, __VA_ARGS__); \
        }                                                        \
    } while (0)

typedef struct { const char *name; void (*fn)(void); } Test;

static int run(const Test *tests, int n) {
    int passed = 0;
    for (int i = 0; i < n; i++) {
        failures = 0;
        tests[i].fn();
        if (failures) {
            printf("FAIL %s: %s\n", tests[i].name, first_msg);
        } else {
            printf("PASS %s\n", tests[i].name);
            passed++;
        }
    }
    return passed;
}

static void test_parse_duration(void) {
    static const struct { const char *in; long want; } cases[] = {
        {"1h30m", 5400}, {"45s", 45}, {"2h", 7200}, {"1m1s", 61},
    };
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; i++) {
        long got = -1;
        int rc = parse_duration(cases[i].in, &got);
        CHECK(rc == 0 && got == cases[i].want, "\"%s\": rc=%d got=%ld, want %ld",
              cases[i].in, rc, got, cases[i].want);
    }
}

static void test_parse_duration_invalid(void) {
    static const char *bad[] = {"", "abc", "10", "5x", "h"};
    for (size_t i = 0; i < sizeof bad / sizeof bad[0]; i++) {
        long got = 0;
        CHECK(parse_duration(bad[i], &got) == -1, "\"%s\" should be rejected", bad[i]);
    }
}

static void test_limit_and_window(void) {
    double now = 0;
    RateLimiter rl;
    rl_init(&rl, 2, 10, fake_now, &now);
    CHECK(rl_allow(&rl) == 1, "first");
    CHECK(rl_allow(&rl) == 1, "second");
    CHECK(rl_allow(&rl) == 0, "third");
    now = 9.9;
    CHECK(rl_allow(&rl) == 0, "just inside the window");
    now = 10;
    CHECK(rl_allow(&rl) == 1, "expired");
}

static void test_denied_do_not_count(void) {
    double now = 0;
    RateLimiter rl;
    rl_init(&rl, 1, 5, fake_now, &now);
    CHECK(rl_allow(&rl) == 1, "first");
    for (int i = 0; i < 10; i++) rl_allow(&rl);
    now = 5;
    CHECK(rl_allow(&rl) == 1, "denied calls were counted");
}

int main(void) {
    const Test tests[] = {
        {"parse_duration", test_parse_duration},
        {"parse_duration_invalid", test_parse_duration_invalid},
        {"limit_and_window", test_limit_and_window},
        {"denied_do_not_count", test_denied_do_not_count},
    };
    int n = (int)(sizeof tests / sizeof tests[0]);
    int passed = run(tests, n);
    printf("%d/%d passed\n", passed, n);
    return passed == n ? 0 : 1;
}
```

<details><summary>Solution</summary>

```c file=solution.c
#include <stdio.h>
#include <string.h>

/* parse_duration reads "1h30m", "45s", "2h" into seconds.
   Returns 0 and sets *out, or -1 on bad input. */
static int parse_duration(const char *s, long *out) {
    long total = 0, n = 0;
    int seen = 0;
    if (*s == '\0') return -1;
    for (; *s; s++) {
        if (*s >= '0' && *s <= '9') {
            n = n * 10 + (*s - '0');
            seen = 1;
        } else if (seen && (*s == 'h' || *s == 'm' || *s == 's')) {
            total += n * (*s == 'h' ? 3600 : *s == 'm' ? 60 : 1);
            n = 0;
            seen = 0;
        } else {
            return -1;
        }
    }
    if (seen) return -1;
    *out = total;
    return 0;
}

#define MAX_CALLS 16

typedef double (*clock_fn)(void *ctx);

/* RateLimiter allows `limit` calls per `window` seconds (limit <= MAX_CALLS). */
typedef struct {
    int limit;
    double window;
    clock_fn clock;
    void *ctx;
    double calls[MAX_CALLS];
    int n;
} RateLimiter;

static void rl_init(RateLimiter *r, int limit, double window, clock_fn clock, void *ctx) {
    r->limit = limit;
    r->window = window;
    r->clock = clock;
    r->ctx = ctx;
    r->n = 0;
}

static int rl_allow(RateLimiter *r) {
    double now = r->clock(r->ctx);
    int drop = 0;
    while (drop < r->n && now - r->calls[drop] >= r->window) drop++;
    memmove(r->calls, r->calls + drop, (size_t)(r->n - drop) * sizeof r->calls[0]);
    r->n -= drop;
    if (r->n >= r->limit) return 0;
    r->calls[r->n++] = now;
    return 1;
}

static double fake_now(void *ctx) { return *(double *)ctx; }

static int failures;
static char first_msg[160];

#define CHECK(cond, ...)                                         \
    do {                                                         \
        if (!(cond)) {                                           \
            if (!failures++) snprintf(first_msg, sizeof first_msg, __VA_ARGS__); \
        }                                                        \
    } while (0)

typedef struct { const char *name; void (*fn)(void); } Test;

static int run(const Test *tests, int n) {
    int passed = 0;
    for (int i = 0; i < n; i++) {
        failures = 0;
        tests[i].fn();
        if (failures) {
            printf("FAIL %s: %s\n", tests[i].name, first_msg);
        } else {
            printf("PASS %s\n", tests[i].name);
            passed++;
        }
    }
    return passed;
}

static void test_parse_duration(void) {
    static const struct { const char *in; long want; } cases[] = {
        {"1h30m", 5400}, {"45s", 45}, {"2h", 7200}, {"1m1s", 61},
    };
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; i++) {
        long got = -1;
        int rc = parse_duration(cases[i].in, &got);
        CHECK(rc == 0 && got == cases[i].want, "\"%s\": rc=%d got=%ld, want %ld",
              cases[i].in, rc, got, cases[i].want);
    }
}

static void test_parse_duration_invalid(void) {
    static const char *bad[] = {"", "abc", "10", "5x", "h"};
    for (size_t i = 0; i < sizeof bad / sizeof bad[0]; i++) {
        long got = 0;
        CHECK(parse_duration(bad[i], &got) == -1, "\"%s\" should be rejected", bad[i]);
    }
}

static void test_limit_and_window(void) {
    double now = 0;
    RateLimiter rl;
    rl_init(&rl, 2, 10, fake_now, &now);
    CHECK(rl_allow(&rl) == 1, "first");
    CHECK(rl_allow(&rl) == 1, "second");
    CHECK(rl_allow(&rl) == 0, "third");
    now = 9.9;
    CHECK(rl_allow(&rl) == 0, "just inside the window");
    now = 10;
    CHECK(rl_allow(&rl) == 1, "expired");
}

static void test_denied_do_not_count(void) {
    double now = 0;
    RateLimiter rl;
    rl_init(&rl, 1, 5, fake_now, &now);
    CHECK(rl_allow(&rl) == 1, "first");
    for (int i = 0; i < 10; i++) rl_allow(&rl);
    now = 5;
    CHECK(rl_allow(&rl) == 1, "denied calls were counted");
}

int main(void) {
    const Test tests[] = {
        {"parse_duration", test_parse_duration},
        {"parse_duration_invalid", test_parse_duration_invalid},
        {"limit_and_window", test_limit_and_window},
        {"denied_do_not_count", test_denied_do_not_count},
    };
    int n = (int)(sizeof tests / sizeof tests[0]);
    int passed = run(tests, n);
    printf("%d/%d passed\n", passed, n);
    return passed == n ? 0 : 1;
}
```

</details>

Next: [14 — Capstone: an LRU cache](14-capstone-lru.md)
