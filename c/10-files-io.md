# C 10 — Files and I/O

`stdio.h` gives buffered streams: `FILE *`. Text and binary I/O use the
same functions; the mode string and the calls you choose decide which.
Check `fopen`, and check `fclose`: a full disk is often reported only
when the buffer is flushed. `gets` was removed in C11 because it cannot
be bounded. Text mode may translate line endings on Windows; use `"b"`
when the bytes must be exact.

## Read back the lines you wrote

`fgets` keeps the newline when it fits. Strip it before printing. Loop
on `fgets`, not on `feof`: `feof` becomes true only after a read has
already failed at the end.

```c file=n01.c
#include <stdio.h>
#include <string.h>

int main(void) {
    const char *path = "notes.txt";
    FILE *f = fopen(path, "w");
    if (!f) {
        return 1;
    }
    fputs("alpha\n", f);
    fprintf(f, "%s\n%s\n", "beta", "gamma");
    if (fclose(f) != 0) {
        return 1;
    }

    f = fopen(path, "r");
    if (!f) {
        return 1;
    }
    char line[64];
    int lineno = 0;
    while (fgets(line, sizeof line, f)) {
        line[strcspn(line, "\n")] = '\0';
        printf("%d %s\n", ++lineno, line);
    }
    fclose(f);
    remove(path);
    return 0;
}
```

```text output
1 alpha
2 beta
3 gamma
```

## `feof` is false until a read fails

The flag is not a prediction. It stays false after the last successful
line. It becomes true only when a later read hits the end and fails.
A loop written as `while (!feof(f))` runs one extra time.

```c file=n11.c
#include <stdio.h>

int main(void) {
    FILE *f = tmpfile();
    if (!f) {
        return 1;
    }
    fputs("hi\n", f);
    rewind(f);
    char buf[8];
    printf("before %d\n", feof(f) != 0);
    if (!fgets(buf, sizeof buf, f)) {
        return 1;
    }
    printf("after-line %d\n", feof(f) != 0);
    fgets(buf, sizeof buf, f);
    printf("after-end %d\n", feof(f) != 0);
    fclose(f);
    return 0;
}
```

```text output
before 0
after-line 0
after-end 1
```

## fgetc returns an int, not a char

`EOF` is a negative `int`. Stored in a `char`, it can look like the byte
`0xFF`, or the loop never sees the end. Count newlines after an append.
The fourth line is the one added in `"a"` mode.

```c file=n02.c
#include <stdio.h>

int main(void) {
    const char *path = "notes.txt";
    FILE *f = fopen(path, "w");
    if (!f) {
        return 1;
    }
    fputs("alpha\nbeta\ngamma\n", f);
    fclose(f);

    f = fopen(path, "a");
    if (!f) {
        return 1;
    }
    fputs("delta\n", f);
    fclose(f);

    f = fopen(path, "r");
    if (!f) {
        return 1;
    }
    int count = 0;
    int ch;
    while ((ch = fgetc(f)) != EOF) {
        if (ch == '\n') {
            count++;
        }
    }
    fclose(f);
    printf("%d\n", count);
    remove(path);
    return 0;
}
```

```text output
4
```

## Binary length is ftell after SEEK_END

`fwrite` and `fread` count elements, not bytes, unless the element size
is 1. Four `int`s are 16 bytes here. `rewind` is `fseek` back to the
start. A dump of a struct is not a portable file format: it contains
padding, native endianness, and native sizes. For a file or a socket,
write each field in an explicit layout.

```c file=n03.c
#include <stdio.h>

int main(void) {
    int arr[4] = {0, 1, 2, 255};
    FILE *f = fopen("data.bin", "wb");
    if (!f) {
        return 1;
    }
    fwrite(arr, sizeof arr[0], 4, f);
    fclose(f);

    f = fopen("data.bin", "rb");
    if (!f) {
        return 1;
    }
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    rewind(f);
    int back[4];
    size_t got = fread(back, sizeof back[0], 4, f);
    fclose(f);
    printf("%ld %zu %d\n", size, got, back[0] + back[1] + back[2] + back[3]);
    remove("data.bin");
    return 0;
}
```

```text output
16 4 258
```

## A struct round-trip matches only the same ABI

The bytes on disk include whatever padding the compiler inserted. Reading
them back on this machine restores `id` and `score`. Another architecture
may not.

```c file=n04.c
#include <stdio.h>

struct record {
    int id;
    double score;
};

int main(void) {
    struct record rec = {7, 9.5}, rec2 = {0, 0};
    FILE *f = fopen("rec.bin", "wb");
    if (!f) {
        return 1;
    }
    fwrite(&rec, sizeof rec, 1, f);
    fclose(f);
    f = fopen("rec.bin", "rb");
    if (!f) {
        return 1;
    }
    if (fread(&rec2, sizeof rec2, 1, f) != 1) {
        fclose(f);
        return 1;
    }
    fclose(f);
    printf("%d %.1f\n", rec2.id, rec2.score);
    remove("rec.bin");
    return 0;
}
```

```text output
7 9.5
```

## sscanf parses one formatted line

`%31[^,]` reads up to 31 characters that are not commas, and leaves room
for the terminator. The result is 2 when both items convert. Do not pass
user text as a format string: `printf("%s", s)`, never `printf(s)`.

```c file=n05.c
#include <stdio.h>

int main(void) {
    char name[32];
    int age;
    if (sscanf("Ada,36", "%31[^,],%d", name, &age) == 2) {
        printf("%s %d\n", name, age);
    }
    return 0;
}
```

```text output
Ada 36
```

## A short buffer splits the line

`fgets` stops after `size - 1` characters. If the newline was not copied,
the rest of the line is still in the stream. Look for `'\n'` to tell a
whole line from a piece.

```c file=n06.c
#include <stdio.h>
#include <string.h>

int main(void) {
    FILE *f = fopen("long.txt", "w");
    if (!f) {
        return 1;
    }
    fputs("0123456789\n", f);
    fclose(f);
    f = fopen("long.txt", "r");
    if (!f) {
        return 1;
    }
    char small[8];
    if (!fgets(small, sizeof small, f)) {
        fclose(f);
        return 1;
    }
    printf("%s %s\n", small, strchr(small, '\n') ? "whole" : "partial");
    fclose(f);
    remove("long.txt");
    return 0;
}
```

```text output
0123456 partial
```

## tmpfile is removed when you close it

The stream has no name you can reopen. `rewind` then `fgets` reads what
you just wrote. Closing deletes it.

```c file=n07.c
#include <stdio.h>

int main(void) {
    FILE *f = tmpfile();
    if (!f) {
        return 1;
    }
    fputs("tmp ok", f);
    rewind(f);
    char tbuf[16] = "";
    if (!fgets(tbuf, sizeof tbuf, f)) {
        fclose(f);
        return 1;
    }
    printf("%s\n", tbuf);
    fclose(f);
    return 0;
}
```

```text output
tmp ok
```

## A missing path is a NULL stream

`fopen` for reading fails when the file is not there. The `NULL` check
is the error handling; there is no exception.

```c file=n08.c
#include <stdio.h>

int main(void) {
    if (!fopen("does-not-exist.txt", "r")) {
        puts("open failed");
    }
    return 0;
}
```

```text output
open failed
```

## remove returns zero on success

The return is 0 when the directory entry is gone, and nonzero when it is
not. Add the codes if you want one check for several paths.

```c file=n09.c
#include <stdio.h>

int main(void) {
    FILE *f = fopen("gone.txt", "w");
    if (!f) {
        return 1;
    }
    fputs("x\n", f);
    if (fclose(f) != 0) {
        return 1;
    }
    printf("%d\n", remove("gone.txt"));
    return 0;
}
```

```text output
0
```

## stderr is not stdout

`fprintf(stderr, ...)` does not appear in the block below: the verifier
records standard output only. `stdout` is line-buffered on a terminal and
fully buffered when piped, so call `fflush(stdout)` before a crash or
`fork`. `stderr` is unbuffered, which is why diagnostics belong there.

```c file=n10.c
#include <stdio.h>

int main(void) {
    fprintf(stderr, "to stderr\n");
    puts("stdout");
    return 0;
}
```

```text output
stdout
```


## Exercises

```c file=exercise.c
#include <stddef.h>
#include <stdio.h>
#include <string.h>

/* Number of lines in the file (a last line without '\n' counts).
   -1 if it cannot be opened. */
long count_lines(const char *path) {
    (void)path;
    return -2; /* TODO */
}

/* Write n ints in binary to path. 0 on success, -1 on failure. */
int write_ints(const char *path, const int *a, size_t n) {
    (void)path; (void)a; (void)n;
    return 0; /* TODO */
}

/* Read up to cap ints from a binary file written by write_ints.
   Returns the number read, or -1 on failure. */
long read_ints(const char *path, int *out, size_t cap) {
    (void)path; (void)out; (void)cap;
    return -2; /* TODO */
}

/* Copy src to dst byte for byte using a buffer. 0 / -1. */
int copy_file(const char *src, const char *dst) {
    (void)src; (void)dst;
    return 0; /* TODO */
}

/* 1 if any line contains needle, 0 if none, -1 on open failure.
   Lines are at most 255 characters. */
int file_contains(const char *path, const char *needle) {
    (void)path; (void)needle;
    return -2; /* TODO */
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

static void put(const char *path, const char *text) {
    FILE *f = fopen(path, "w");
    if (f) {
        fputs(text, f);
        fclose(f);
    }
}

int main(void) {
    put("a.txt", "one\ntwo\nthree");
    put("empty.txt", "");
    CHECK("lines", count_lines("a.txt") == 3);
    CHECK("lines empty", count_lines("empty.txt") == 0);
    CHECK("lines missing", count_lines("nope.txt") == -1);

    int xs[] = {10, -20, 30, 0, 255};
    int ys[8] = {0};
    CHECK("write ints", write_ints("ints.bin", xs, 5) == 0);
    CHECK("read ints", read_ints("ints.bin", ys, 8) == 5 && ys[1] == -20 && ys[4] == 255);
    CHECK("read cap", read_ints("ints.bin", ys, 2) == 2);
    CHECK("read missing", read_ints("nope.bin", ys, 8) == -1);

    CHECK("copy", copy_file("a.txt", "b.txt") == 0 && count_lines("b.txt") == 3);
    CHECK("copy missing", copy_file("nope.txt", "c.txt") == -1);

    CHECK("contains", file_contains("a.txt", "wo") == 1);
    CHECK("not contains", file_contains("a.txt", "zzz") == 0);
    CHECK("contains missing", file_contains("nope.txt", "a") == -1);

    remove("a.txt");
    remove("empty.txt");
    remove("ints.bin");
    remove("b.txt");
    remove("c.txt");
    return failed;
}
```

<details><summary>Solution</summary>

```c file=solution.c
#include <stddef.h>
#include <stdio.h>
#include <string.h>

long count_lines(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) {
        return -1;
    }
    long n = 0;
    int ch, last = '\n';
    while ((ch = fgetc(f)) != EOF) {
        if (ch == '\n') {
            n++;
        }
        last = ch;
    }
    if (last != '\n') {
        n++; /* final line without newline */
    }
    fclose(f);
    return n;
}

int write_ints(const char *path, const int *a, size_t n) {
    FILE *f = fopen(path, "wb");
    if (!f) {
        return -1;
    }
    size_t w = fwrite(a, sizeof a[0], n, f);
    int rc = (fclose(f) == 0 && w == n) ? 0 : -1;
    return rc;
}

long read_ints(const char *path, int *out, size_t cap) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        return -1;
    }
    size_t n = fread(out, sizeof out[0], cap, f);
    int bad = ferror(f);
    fclose(f);
    return bad ? -1 : (long)n;
}

int copy_file(const char *src, const char *dst) {
    FILE *in = fopen(src, "rb");
    if (!in) {
        return -1;
    }
    FILE *out = fopen(dst, "wb");
    if (!out) {
        fclose(in);
        return -1;
    }
    char buf[4096];
    size_t n;
    int rc = 0;
    while ((n = fread(buf, 1, sizeof buf, in)) > 0) {
        if (fwrite(buf, 1, n, out) != n) {
            rc = -1;
            break;
        }
    }
    if (ferror(in)) {
        rc = -1;
    }
    fclose(in);
    if (fclose(out) != 0) {
        rc = -1;
    }
    return rc;
}

int file_contains(const char *path, const char *needle) {
    FILE *f = fopen(path, "r");
    if (!f) {
        return -1;
    }
    char line[256];
    int found = 0;
    while (!found && fgets(line, sizeof line, f)) {
        found = strstr(line, needle) != NULL;
    }
    fclose(f);
    return found;
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

static void put(const char *path, const char *text) {
    FILE *f = fopen(path, "w");
    if (f) {
        fputs(text, f);
        fclose(f);
    }
}

int main(void) {
    put("a.txt", "one\ntwo\nthree");
    put("empty.txt", "");
    CHECK("lines", count_lines("a.txt") == 3);
    CHECK("lines empty", count_lines("empty.txt") == 0);
    CHECK("lines missing", count_lines("nope.txt") == -1);

    int xs[] = {10, -20, 30, 0, 255};
    int ys[8] = {0};
    CHECK("write ints", write_ints("ints.bin", xs, 5) == 0);
    CHECK("read ints", read_ints("ints.bin", ys, 8) == 5 && ys[1] == -20 && ys[4] == 255);
    CHECK("read cap", read_ints("ints.bin", ys, 2) == 2);
    CHECK("read missing", read_ints("nope.bin", ys, 8) == -1);

    CHECK("copy", copy_file("a.txt", "b.txt") == 0 && count_lines("b.txt") == 3);
    CHECK("copy missing", copy_file("nope.txt", "c.txt") == -1);

    CHECK("contains", file_contains("a.txt", "wo") == 1);
    CHECK("not contains", file_contains("a.txt", "zzz") == 0);
    CHECK("contains missing", file_contains("nope.txt", "a") == -1);

    remove("a.txt");
    remove("empty.txt");
    remove("ints.bin");
    remove("b.txt");
    remove("c.txt");
    return failed;
}
```

</details>

Next: [11 — Idiomatic C](11-idiomatic-c.md)
