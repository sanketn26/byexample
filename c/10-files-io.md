# C 10 — Files and I/O

`stdio.h` gives buffered streams: `FILE *`. Text and binary I/O use the same
functions; the mode string and the calls you choose decide which.

## Example

```c file=example.c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct record {
    int id;
    double score;
};

int main(void) {
    const char *path = "notes.txt";

    /* Write text */
    FILE *f = fopen(path, "w");
    if (!f) {
        perror("fopen");
        return 1;
    }
    fputs("alpha\n", f);
    fprintf(f, "%s\n%s\n", "beta", "gamma");
    if (fclose(f) != 0) { /* buffered data may fail at close time */
        perror("fclose");
        return 1;
    }

    /* Read it line by line */
    f = fopen(path, "r");
    if (!f) {
        return 1;
    }
    char line[64];
    int lineno = 0;
    while (fgets(line, sizeof line, f)) {
        line[strcspn(line, "\n")] = '\0'; /* strip the newline */
        printf("%d %s\n", ++lineno, line);
    }
    fclose(f);

    /* Append */
    f = fopen(path, "a");
    fputs("delta\n", f);
    fclose(f);
    f = fopen(path, "r");
    int count = 0;
    int ch;
    while ((ch = fgetc(f)) != EOF) { /* int, not char, so EOF is distinct */
        if (ch == '\n') {
            count++;
        }
    }
    fclose(f);
    printf("%d\n", count);

    /* Binary: fwrite / fread, and the size via fseek + ftell */
    int arr[4] = {0, 1, 2, 255};
    f = fopen("data.bin", "wb");
    fwrite(arr, sizeof arr[0], 4, f);
    fclose(f);

    f = fopen("data.bin", "rb");
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    rewind(f);
    int back[4];
    size_t got = fread(back, sizeof back[0], 4, f);
    fclose(f);
    printf("%ld %zu %d\n", size, got, back[0] + back[1] + back[2] + back[3]);

    /* A struct round trip (same machine/ABI only: not a portable format) */
    struct record rec = {7, 9.5}, rec2 = {0, 0};
    f = fopen("rec.bin", "wb");
    fwrite(&rec, sizeof rec, 1, f);
    fclose(f);
    f = fopen("rec.bin", "rb");
    fread(&rec2, sizeof rec2, 1, f);
    fclose(f);
    printf("%d %.1f\n", rec2.id, rec2.score);

    /* Parsing a formatted line */
    char name[32];
    int age;
    if (sscanf("Ada,36", "%31[^,],%d", name, &age) == 2) {
        printf("%s %d\n", name, age);
    }

    /* A line longer than the buffer arrives in pieces */
    f = fopen("long.txt", "w");
    fputs("0123456789\n", f);
    fclose(f);
    f = fopen("long.txt", "r");
    char small[8];
    fgets(small, sizeof small, f);
    printf("%s %s\n", small, strchr(small, '\n') ? "whole" : "partial");
    fclose(f);

    /* Anonymous temporary file, removed on close */
    f = tmpfile();
    fputs("tmp ok", f);
    rewind(f);
    char tbuf[16] = "";
    if (fgets(tbuf, sizeof tbuf, f)) {
        printf("%s\n", tbuf);
    }
    fclose(f);

    /* Missing file */
    if (!fopen("does-not-exist.txt", "r")) {
        puts("open failed");
    }

    /* Clean up */
    printf("%d\n", remove(path) + remove("data.bin") + remove("rec.bin") + remove("long.txt"));

    fprintf(stderr, "to stderr\n");
    return 0;
}
```

```text output
1 alpha
2 beta
3 gamma
4
16 4 258
7 9.5
Ada 36
0123456 partial
tmp ok
open failed
0
```

## Details that bite

- Check `fopen`'s result and **`fclose`'s** result — write errors (disk
  full) are often reported only at flush/close.
- `fgetc` returns `int`. Storing it in a `char` makes `EOF` indistinguishable
  from a valid byte (`0xFF`) on some platforms or loops forever on others.
- `fgets` keeps the `'\n'`; if the buffer fills first the line is split.
  Detect that by looking for the newline.
- `feof` is true only *after* a read attempt hits the end. Loop on the
  read function's return value, not `while (!feof(f))`.
- `gets` was removed in C11 because it cannot be used safely.
- Never pass user-controlled text as the *format* string: use
  `printf("%s", s)`, not `printf(s)`.
- Binary dumps of structs contain padding, native endianness and native
  sizes. For files or networks, define an explicit byte layout and
  (de)serialise field by field.
- Text mode may translate line endings on Windows; use `"b"` for bytes.
- Output to `stdout` is line-buffered on a terminal and fully buffered when
  piped; call `fflush(stdout)` before crashes or `fork`, or write
  diagnostics to unbuffered `stderr`.

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
