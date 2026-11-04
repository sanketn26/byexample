# C 07 — Error Handling

C has no exceptions. Errors are values: a status code, `errno`, a `NULL`
pointer, or an out-parameter. Check every return that can fail — `malloc`,
`fopen`, `fread`, `fclose`, `snprintf`, `scanf`. A silent failure becomes
corruption later.

Pick one convention and keep it. Returning 0 for success and a negative
value or an enum for failure is the usual one. Mixing "1 means success"
with "0 means success" is a bug factory.

## A status code names the failure

The value comes out through a pointer. A bad argument returns a name, and
does not write the result. `safe_div` refuses a null out-pointer and a
zero divisor.

```c file=n01.c
#include <stdio.h>

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

int main(void) {
    int r = 0;
    enum status st = safe_div(7, 2, &r);
    printf("%s %d\n", status_str(st), r);
    printf("%s\n", status_str(safe_div(1, 0, &r)));
    printf("%s\n", status_str(safe_div(1, 1, NULL)));
    return 0;
}
```

```text output
ok 3
range error
null pointer
```

## errno is meaningful only just after the failure

`fopen` returns `NULL` and sets `errno`. A later successful call may
overwrite it, so read it immediately. Set `errno = 0` before functions
like `strtol` that use `errno` as their only signal. `perror` and
`strerror` turn the number into text. `strerror` may not be thread-safe;
use `strerror_r` when other threads are running.

```c file=n02.c
#include <errno.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    errno = 0;
    FILE *f = fopen("/definitely/not/here", "r");
    if (!f) {
        printf("%d %s\n", errno == ENOENT, strerror(errno));
    }
    return 0;
}
```

```text output
1 No such file or directory
```

## goto cleanup has one exit

Acquire in order, release in reverse, and jump to the same label from
every failure. `free(NULL)` does nothing, so the cleanup can be
unconditional. This is the usual shape in the Linux kernel. `setjmp` /
`longjmp` can leave a function early too, but they skip this cleanup and
are rarely the right tool.

```c file=n03.c
#include <stdio.h>
#include <stdlib.h>

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
    free(b);
    free(a);
    return rc;
}

int main(void) {
    printf("%d %d %d\n", build(0), build(1), build(2));
    return 0;
}
```

```text output
0 -1 -1
```

## A result can carry a value or an error

The `ok` flag says which union member is live. On failure the string is
the error; on success `value` is the digit.

```c file=n04.c
#include <stdio.h>

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

int main(void) {
    struct result d = parse_digit('7');
    printf("%s %d\n", d.ok ? "ok" : "error", d.value);
    struct result bad = parse_digit('x');
    printf("error: %s\n", bad.error);
    return 0;
}
```

```text output
ok 7
error: not a digit
```

## assert documents an impossible state

`assert` aborts when the expression is false. It is not for validating
input: compiling with `-DNDEBUG` removes it, including any side effects
inside the expression.

```c file=n05.c
#include <assert.h>
#include <stdio.h>

int main(void) {
    int r = 3;
    assert(r == 3);
    puts("kept");
    return 0;
}
```

```text output
kept
```

## exit runs atexit handlers; abort does not

`exit` flushes stdio and runs the handlers registered with `atexit`, in
reverse order of registration. `_Exit` and `abort` do neither. The line
below is printed on the way out, after `main` returns.

```c file=n06.c
#include <stdio.h>
#include <stdlib.h>

static void goodbye(void) {
    puts("bye");
}

int main(void) {
    atexit(goodbye);
    return EXIT_SUCCESS;
}
```

```text output
bye
```


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
