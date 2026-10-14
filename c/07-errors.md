# C 07 — Error Handling

C has no exceptions. Errors are *values*: return codes, `errno`, `NULL`
pointers, or out-parameters. Discipline is the only thing that keeps them
from being ignored.

## Example

```c file=example.c
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum status { OK = 0, ERR_NULL, ERR_RANGE, ERR_NOMEM };

static const char *status_str(enum status s) {
    switch (s) {
    case OK:
        return "ok";
    case ERR_NULL:
        return "null pointer";
    case ERR_RANGE:
        return "range error";
    case ERR_NOMEM:
        return "out of memory";
    }
    return "unknown";
}

/* Convention: return a status, deliver the value through an out-parameter */
static enum status safe_div(int a, int b, int *out) {
    if (!out) {
        return ERR_NULL;
    }
    if (b == 0) {
        return ERR_RANGE;
    }
    *out = a / b;
    return OK;
}

/* Alternative: a result type carrying either a value or an error */
struct result {
    int ok;
    union {
        int value;
        const char *error;
    };
};

static struct result parse_digit(char c) {
    if (c < '0' || c > '9') {
        return (struct result){.ok = 0, .error = "not a digit"};
    }
    return (struct result){.ok = 1, .value = c - '0'};
}

/* goto cleanup: single exit, resources released in reverse order */
static int build(int fail_at) {
    int rc = -1;
    char *a = NULL, *b = NULL;

    a = malloc(16);
    if (!a) {
        goto out;
    }
    if (fail_at == 1) {
        goto out;
    }
    b = malloc(16);
    if (!b) {
        goto out;
    }
    if (fail_at == 2) {
        goto out;
    }
    rc = 0;
out:
    free(b); /* free(NULL) is a no-op, so unconditional cleanup is fine */
    free(a);
    return rc;
}

static void goodbye(void) {
    puts("bye");
}

int main(void) {
    atexit(goodbye);

    int r = 0;
    enum status st = safe_div(7, 2, &r);
    printf("%s %d\n", status_str(st), r);
    printf("%s\n", status_str(safe_div(1, 0, &r)));
    printf("%s\n", status_str(safe_div(1, 1, NULL)));

    /* errno: set by the failing library call; only read it right after */
    errno = 0;
    FILE *f = fopen("/definitely/not/here", "r");
    if (!f) {
        printf("%d %s\n", errno == ENOENT, strerror(errno));
    }

    printf("%d %d %d\n", build(0), build(1), build(2));

    struct result d = parse_digit('7');
    printf("%s %d\n", d.ok ? "ok" : "error", d.value);
    struct result bad = parse_digit('x');
    printf("error: %s\n", bad.error);

    /* assert documents impossible states; compiled out with -DNDEBUG */
    assert(r == 3);
    return EXIT_SUCCESS;
}
```

```text output
ok 3
range error
null pointer
1 No such file or directory
0 -1 -1
ok 7
error: not a digit
bye
```

## Details that bite

- **Check every return value** that can fail: `malloc`, `fopen`, `fread`,
  `fclose`, `snprintf`, `scanf`. Silent failure becomes corruption later.
- `errno` is only meaningful immediately after a call that reported failure
  (usually by returning `-1`/`NULL`). Successful calls may change it.
  Set `errno = 0` before calls like `strtol` that signal errors only via
  `errno`.
- `perror("fopen")` and `strerror(errno)` turn the number into text.
  `strerror` may not be thread-safe; use `strerror_r` in threaded code.
- Never use `assert` for runtime input validation: with `NDEBUG` it
  vanishes, along with any side effects inside it.
- `exit()` runs `atexit` handlers and flushes stdio; `_Exit()` and
  `abort()` do not.
- Return `0` for success and negative or an enum for failure, consistently
  across your API. Mixing "1 means success" with "0 means success" is a
  bug factory.
- `goto cleanup` is the standard, readable way to avoid duplicated cleanup
  code, and is how the Linux kernel does it.
- There is `setjmp`/`longjmp` for non-local exits, but it skips cleanup and
  is rarely the right tool.

## Exercises

```c file=exercise.c
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum status { OK = 0, ERR_NULL, ERR_OVERFLOW, ERR_FORMAT, ERR_IO, ERR_TOO_LONG };

/* a + b into *out; ERR_NULL if out is NULL; ERR_OVERFLOW on int overflow
   (without relying on signed overflow, which is undefined). */
enum status checked_add(int a, int b, int *out) {
    (void)a; (void)b; (void)out;
    return ERR_IO; /* TODO */
}

/* Strictly parse a whole string as a double: ERR_FORMAT for "", "1.5x",
   leading spaces, and ERR_NULL for NULL arguments. */
enum status parse_double(const char *s, double *out) {
    (void)s; (void)out;
    return ERR_IO; /* TODO */
}

/* Size of a file in bytes. ERR_IO if it cannot be opened/read; errno must
   still describe the failure (do not clobber it with later calls). */
enum status file_size(const char *path, long *size) {
    (void)path; (void)size;
    return OK; /* TODO */
}

/* Copy src into dst (capacity cap, including the terminator).
   ERR_TOO_LONG if it does not fit; dst is left unmodified in that case. */
enum status safe_copy(char *dst, size_t cap, const char *src) {
    (void)dst; (void)cap; (void)src;
    return OK; /* TODO */
}

/* Open `path` for reading, and read its first line into buf (cap bytes,
   newline stripped). Always release the FILE. ERR_IO on any failure. */
enum status first_line(const char *path, char *buf, size_t cap) {
    (void)path; (void)buf; (void)cap;
    return OK; /* TODO */
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
    int v = 0;
    CHECK("add ok", checked_add(2, 3, &v) == OK && v == 5);
    CHECK("add overflow", checked_add(INT_MAX, 1, &v) == ERR_OVERFLOW);
    CHECK("add underflow", checked_add(INT_MIN, -1, &v) == ERR_OVERFLOW);
    CHECK("add null", checked_add(1, 1, NULL) == ERR_NULL);

    double d = 0;
    CHECK("double ok", parse_double("3.25", &d) == OK && d == 3.25);
    CHECK("double junk", parse_double("1.5x", &d) == ERR_FORMAT);
    CHECK("double empty", parse_double("", &d) == ERR_FORMAT);
    CHECK("double space", parse_double(" 1", &d) == ERR_FORMAT);
    CHECK("double null", parse_double(NULL, &d) == ERR_NULL);

    FILE *f = fopen("sample.txt", "w");
    if (!f) {
        return 2;
    }
    fputs("hello\nworld\n", f);
    fclose(f);
    long sz = 0;
    CHECK("size", file_size("sample.txt", &sz) == OK && sz == 12);
    errno = 0;
    CHECK("size missing", file_size("no-such-file", &sz) == ERR_IO && errno == ENOENT);

    char small[4] = "abc";
    CHECK("copy too long", safe_copy(small, sizeof small, "abcdef") == ERR_TOO_LONG
                               && strcmp(small, "abc") == 0);
    char big[16];
    CHECK("copy ok", safe_copy(big, sizeof big, "abcdef") == OK && strcmp(big, "abcdef") == 0);

    char line[32] = "";
    CHECK("first_line", first_line("sample.txt", line, sizeof line) == OK
                            && strcmp(line, "hello") == 0);
    CHECK("first_line missing", first_line("no-such-file", line, sizeof line) == ERR_IO);
    remove("sample.txt");
    return failed;
}
```

<details><summary>Solution</summary>

```c file=solution.c
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum status { OK = 0, ERR_NULL, ERR_OVERFLOW, ERR_FORMAT, ERR_IO, ERR_TOO_LONG };

enum status checked_add(int a, int b, int *out) {
    if (!out) {
        return ERR_NULL;
    }
    if ((b > 0 && a > INT_MAX - b) || (b < 0 && a < INT_MIN - b)) {
        return ERR_OVERFLOW;
    }
    *out = a + b;
    return OK;
}

enum status parse_double(const char *s, double *out) {
    if (!s || !out) {
        return ERR_NULL;
    }
    if (*s == '\0' || *s == ' ' || *s == '\t' || *s == '\n') {
        return ERR_FORMAT;
    }
    char *end;
    double v = strtod(s, &end);
    if (*end != '\0') {
        return ERR_FORMAT;
    }
    *out = v;
    return OK;
}

enum status file_size(const char *path, long *size) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        return ERR_IO; /* errno still holds the fopen failure */
    }
    enum status st = ERR_IO;
    if (fseek(f, 0, SEEK_END) == 0) {
        long n = ftell(f);
        if (n >= 0) {
            *size = n;
            st = OK;
        }
    }
    fclose(f);
    return st;
}

enum status safe_copy(char *dst, size_t cap, const char *src) {
    size_t n = strlen(src);
    if (n + 1 > cap) {
        return ERR_TOO_LONG;
    }
    memcpy(dst, src, n + 1);
    return OK;
}

enum status first_line(const char *path, char *buf, size_t cap) {
    FILE *f = fopen(path, "r");
    if (!f) {
        return ERR_IO;
    }
    enum status st = OK;
    if (!fgets(buf, (int)cap, f)) {
        st = ERR_IO;
    } else {
        buf[strcspn(buf, "\n")] = '\0';
    }
    fclose(f);
    return st;
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
    int v = 0;
    CHECK("add ok", checked_add(2, 3, &v) == OK && v == 5);
    CHECK("add overflow", checked_add(INT_MAX, 1, &v) == ERR_OVERFLOW);
    CHECK("add underflow", checked_add(INT_MIN, -1, &v) == ERR_OVERFLOW);
    CHECK("add null", checked_add(1, 1, NULL) == ERR_NULL);

    double d = 0;
    CHECK("double ok", parse_double("3.25", &d) == OK && d == 3.25);
    CHECK("double junk", parse_double("1.5x", &d) == ERR_FORMAT);
    CHECK("double empty", parse_double("", &d) == ERR_FORMAT);
    CHECK("double space", parse_double(" 1", &d) == ERR_FORMAT);
    CHECK("double null", parse_double(NULL, &d) == ERR_NULL);

    FILE *f = fopen("sample.txt", "w");
    if (!f) {
        return 2;
    }
    fputs("hello\nworld\n", f);
    fclose(f);
    long sz = 0;
    CHECK("size", file_size("sample.txt", &sz) == OK && sz == 12);
    errno = 0;
    CHECK("size missing", file_size("no-such-file", &sz) == ERR_IO && errno == ENOENT);

    char small[4] = "abc";
    CHECK("copy too long", safe_copy(small, sizeof small, "abcdef") == ERR_TOO_LONG
                               && strcmp(small, "abc") == 0);
    char big[16];
    CHECK("copy ok", safe_copy(big, sizeof big, "abcdef") == OK && strcmp(big, "abcdef") == 0);

    char line[32] = "";
    CHECK("first_line", first_line("sample.txt", line, sizeof line) == OK
                            && strcmp(line, "hello") == 0);
    CHECK("first_line missing", first_line("no-such-file", line, sizeof line) == ERR_IO);
    remove("sample.txt");
    return failed;
}
```

</details>

Next: [08 — Memory](08-memory.md)
