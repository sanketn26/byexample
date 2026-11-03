# C 15 — Streaming

`read` and `write` on a file, a pipe or a socket all return a count that can be shorter than you asked for. A zero `read` is end of stream. `fread` and `fwrite` are the same contract. Copy in a fixed buffer, and treat a frame that stops early as an error.

## Example

```c file=example.c
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

struct mem {
    const unsigned char *data;
    size_t len, i, limit, reads;
};

static int mem_read(struct mem *m, unsigned char *dst, size_t n) {
    m->reads++;
    if (m->i >= m->len) {
        return 0; /* clean EOF */
    }
    if (n > m->limit) {
        n = m->limit;
    }
    if (n > m->len - m->i) {
        n = m->len - m->i;
    }
    memcpy(dst, m->data + m->i, n);
    m->i += n;
    return (int)n;
}

struct sink {
    unsigned char buf[64];
    size_t len, limit, writes;
};

static int sink_write(struct sink *s, const unsigned char *src, size_t n) {
    s->writes++;
    if (n > s->limit) {
        n = s->limit;
    }
    if (s->len + n > sizeof s->buf) {
        return -1;
    }
    memcpy(s->buf + s->len, src, n);
    s->len += n;
    return (int)n;
}

/* Copy until EOF. Retries short writes. Returns byte count, or -1. */
static int copy_chunks(struct mem *src, struct sink *dst, size_t size) {
    unsigned char buf[64];
    if (size > sizeof buf) {
        return -1;
    }
    int total = 0;
    for (;;) {
        int n = mem_read(src, buf, size);
        if (n < 0) {
            return -1;
        }
        if (n == 0) {
            return total;
        }
        int off = 0;
        while (off < n) {
            int w = sink_write(dst, buf + off, (size_t)(n - off));
            if (w <= 0) {
                return -1;
            }
            off += w;
            total += w;
        }
    }
}

/* Exactly n bytes. 1 on success, 0 on clean EOF before any byte, -1 if truncated. */
static int read_full(struct mem *src, unsigned char *dst, size_t n) {
    size_t got = 0;
    while (got < n) {
        int k = mem_read(src, dst + got, n - got);
        if (k < 0) {
            return -1;
        }
        if (k == 0) {
            return got == 0 ? 0 : -1;
        }
        got += (size_t)k;
    }
    return 1;
}

static void put_be32(unsigned char *p, uint32_t n) {
    p[0] = (unsigned char)(n >> 24);
    p[1] = (unsigned char)(n >> 16);
    p[2] = (unsigned char)(n >> 8);
    p[3] = (unsigned char)n;
}

static uint32_t get_be32(const unsigned char *p) {
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}

/* 1 and payload written to dst (capacity cap), 0 on clean EOF, -1 on a short frame. */
static int read_frame(struct mem *src, unsigned char *dst, size_t cap, size_t *out_len) {
    unsigned char hdr[4];
    int rc = read_full(src, hdr, 4);
    if (rc <= 0) {
        return rc;
    }
    uint32_t n = get_be32(hdr);
    if ((size_t)n > cap) {
        return -1;
    }
    rc = read_full(src, dst, n);
    if (rc <= 0) {
        return -1;
    }
    *out_len = n;
    return 1;
}

static int atomic_write(const char *path, const void *data, size_t n) {
    char tmp[320];
    int nw = snprintf(tmp, sizeof tmp, "%s.tmp", path);
    if (nw < 0 || (size_t)nw >= sizeof tmp) {
        return -1;
    }
    FILE *f = fopen(tmp, "wb");
    if (!f) {
        return -1;
    }
    size_t wr = fwrite(data, 1, n, f);
    int flush_err = fflush(f) != 0;
    int close_err = fclose(f) != 0;
    if (wr != n || flush_err || close_err) {
        remove(tmp);
        return -1;
    }
    if (rename(tmp, path) != 0) {
        remove(tmp);
        return -1;
    }
    return 0;
}

int main(void) {
    const unsigned char text[] = "hello world";
    struct mem src = {.data = text, .len = 11, .limit = 3};
    struct sink dst = {.limit = 2};
    int n = copy_chunks(&src, &dst, 8);
    printf("%d %zu %zu %.*s\n", n, src.reads, dst.writes, (int)dst.len, dst.buf);

    unsigned char raw[64];
    size_t len = 0;
    put_be32(raw + len, 5);
    len += 4;
    memcpy(raw + len, "hello", 5);
    len += 5;
    put_be32(raw + len, 5);
    len += 4;
    memcpy(raw + len, "world", 5);
    len += 5;
    raw[len++] = 0;
    raw[len++] = 0;
    struct mem frames = {.data = raw, .len = len, .limit = 3};
    unsigned char body[32];
    size_t blen = 0;
    int rc = read_frame(&frames, body, sizeof body, &blen);
    printf("%d %.*s ", rc, (int)blen, body);
    rc = read_frame(&frames, body, sizeof body, &blen);
    printf("%d %.*s ", rc, (int)blen, body);
    rc = read_frame(&frames, body, sizeof body, &blen);
    printf("%d\n", rc);

    char dir[] = "/tmp/cstreamXXXXXX";
    if (!mkdtemp(dir)) {
        perror("mkdtemp");
        return 1;
    }
    char path[64];
    if ((size_t)snprintf(path, sizeof path, "%s/notes.txt", dir) >= sizeof path) {
        return 1;
    }
    if (atomic_write(path, "hello", 5) != 0) {
        perror("atomic");
        return 1;
    }
    FILE *f = fopen(path, "rb");
    char got[16] = {0};
    if (fread(got, 1, 5, f) != 5) {
        return 1;
    }
    fclose(f);
    /* directory should contain only notes.txt, not the temp name */
    int extras = 0;
    /* cheap check: the temp path is gone */
    char tmp[80];
    if ((size_t)snprintf(tmp, sizeof tmp, "%s.tmp", path) >= sizeof tmp) {
        return 1;
    }
    FILE *left = fopen(tmp, "rb");
    if (left) {
        extras = 1;
        fclose(left);
    }
    printf("notes.txt %s %s\n", got, extras ? "leftover" : "clean");

    int fds[2];
    if (pipe(fds) != 0) {
        return 1;
    }
    unsigned char framed[16];
    put_be32(framed, 8);
    memcpy(framed + 4, "via-pipe", 8);
    if (write(fds[1], framed, 12) != 12) {
        return 1;
    }
    close(fds[1]);
    /* read the pipe with the same full-read loop, via a one-shot buffer */
    unsigned char pipebuf[16];
    size_t pn = 0;
    while (pn < sizeof pipebuf) {
        ssize_t k = read(fds[0], pipebuf + pn, sizeof pipebuf - pn);
        if (k == 0) {
            break;
        }
        if (k < 0) {
            return 1;
        }
        pn += (size_t)k;
    }
    close(fds[0]);
    struct mem piped = {.data = pipebuf, .len = pn, .limit = 5};
    blen = 0;
    rc = read_frame(&piped, body, sizeof body, &blen);
    printf("%d %.*s\n", rc, (int)blen, body);

    remove(path);
    rmdir(dir);
    return 0;
}
```

```text output
11 5 7 hello world
1 hello 1 world -1
notes.txt hello clean
1 via-pipe
```

## Details that bite

- A short read is normal. End of stream is a zero-length read (or
  `io.EOF` / `Ok(0)`). A header that stops after two of its four bytes is
  a truncated frame: fail the frame, do not return a partial payload.
- A short write must be retried from the first byte the callee did not
  accept. "I called write" is not "those bytes are on the wire".
- The length is a big-endian `uint32` of the **body**, so the other three
  languages in this course can read the same bytes. Cap the length before
  you allocate it.
- Replace a file by writing a temporary in the **same directory** and
  renaming it over the destination. `rename` is atomic on one filesystem.
  Check the error from flush and from close; a buffered writer can fail
  there, after `write` returned success.
- The copy loop is what `io.Copy`, `std::io::copy` and a `fread`/`fwrite`
  pair are. A pipe and a socket use the same loop as the file.

## Exercises

`copy_chunks` copies until EOF and retries short writes. `read_frame` returns 1 and the payload, 0 on a clean EOF, and -1 when a frame is cut off. `atomic_write` leaves exactly the destination file behind.

```c file=exercise.c
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define static static __attribute__((unused))

struct mem {
    const unsigned char *data;
    size_t len, i, limit, reads;
};

static int mem_read(struct mem *m, unsigned char *dst, size_t n) {
    m->reads++;
    if (m->i >= m->len) {
        return 0; /* clean EOF */
    }
    if (n > m->limit) {
        n = m->limit;
    }
    if (n > m->len - m->i) {
        n = m->len - m->i;
    }
    memcpy(dst, m->data + m->i, n);
    m->i += n;
    return (int)n;
}

struct sink {
    unsigned char buf[64];
    size_t len, limit, writes;
};

static int sink_write(struct sink *s, const unsigned char *src, size_t n) {
    s->writes++;
    if (n > s->limit) {
        n = s->limit;
    }
    if (s->len + n > sizeof s->buf) {
        return -1;
    }
    memcpy(s->buf + s->len, src, n);
    s->len += n;
    return (int)n;
}

/* Copy until EOF. Retries short writes. Returns byte count, or -1. */
static int copy_chunks(struct mem *src, struct sink *dst, size_t size) {
    (void)src; (void)dst; (void)size;
    return -1;
}



/* Exactly n bytes. 1 on success, 0 on clean EOF before any byte, -1 if truncated. */
static int read_full(struct mem *src, unsigned char *dst, size_t n) {
    size_t got = 0;
    while (got < n) {
        int k = mem_read(src, dst + got, n - got);
        if (k < 0) {
            return -1;
        }
        if (k == 0) {
            return got == 0 ? 0 : -1;
        }
        got += (size_t)k;
    }
    return 1;
}

static void put_be32(unsigned char *p, uint32_t n) {
    p[0] = (unsigned char)(n >> 24);
    p[1] = (unsigned char)(n >> 16);
    p[2] = (unsigned char)(n >> 8);
    p[3] = (unsigned char)n;
}

static uint32_t get_be32(const unsigned char *p) {
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}

/* 1 and payload written to dst (capacity cap), 0 on clean EOF, -1 on a short frame. */
static int read_frame(struct mem *src, unsigned char *dst, size_t cap, size_t *out_len) {
    (void)src; (void)dst; (void)cap; (void)out_len;
    return 0;
}



static int atomic_write(const char *path, const void *data, size_t n) {
    (void)path; (void)data; (void)n;
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
    const unsigned char text[] = "hello world";
    struct mem src = {.data = text, .len = 11, .limit = 3};
    struct sink dst = {.limit = 2};
    int n = copy_chunks(&src, &dst, 8);
    CHECK("copy", n == 11 && dst.len == 11 && memcmp(dst.buf, "hello world", 11) == 0);

    unsigned char raw[64];
    size_t len = 0;
    put_be32(raw, 5); len = 4; memcpy(raw + len, "hello", 5); len += 5;
    put_be32(raw + len, 5); len += 4; memcpy(raw + len, "world", 5); len += 5;
    struct mem frames = {.data = raw, .len = len, .limit = 3};
    unsigned char body[32];
    size_t blen = 0;
    int rc1 = read_frame(&frames, body, sizeof body, &blen);
    int hello = rc1 == 1 && blen == 5 && memcmp(body, "hello", 5) == 0;
    int rc2 = read_frame(&frames, body, sizeof body, &blen);
    int world = rc2 == 1 && blen == 5 && memcmp(body, "world", 5) == 0;
    int rc3 = read_frame(&frames, body, sizeof body, &blen);
    CHECK("frames", hello && world && rc3 == 0);

    unsigned char badraw[16];
    size_t bl = 0;
    put_be32(badraw, 5); bl = 4; memcpy(badraw + bl, "hello", 5); bl += 5;
    badraw[bl++] = 0; badraw[bl++] = 0;
    struct mem bad = {.data = badraw, .len = bl, .limit = 1};
    read_frame(&bad, body, sizeof body, &blen);
    CHECK("truncated", read_frame(&bad, body, sizeof body, &blen) == -1);

    char dir[] = "/tmp/cstexXXXXXX";
    if (!mkdtemp(dir)) return 1;
    char path[64];
    if ((size_t)snprintf(path, sizeof path, "%s/notes.txt", dir) >= sizeof path) return 1;
    CHECK("atomic write", atomic_write(path, "hello", 5) == 0);
    FILE *f = fopen(path, "rb");
    char got[8] = {0};
    int nread = f ? (int)fread(got, 1, 5, f) : 0;
    if (f) fclose(f);
    char tmp[80];
    int leftover = 0;
    if ((size_t)snprintf(tmp, sizeof tmp, "%s.tmp", path) < sizeof tmp) {
        FILE *t = fopen(tmp, "rb");
        if (t) { leftover = 1; fclose(t); }
    }
    CHECK("atomic", nread == 5 && memcmp(got, "hello", 5) == 0 && !leftover);
    remove(path);
    rmdir(dir);
    return failed;
}
```

<details><summary>Solution</summary>

```c file=solution.c
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

struct mem {
    const unsigned char *data;
    size_t len, i, limit, reads;
};

static int mem_read(struct mem *m, unsigned char *dst, size_t n) {
    m->reads++;
    if (m->i >= m->len) {
        return 0; /* clean EOF */
    }
    if (n > m->limit) {
        n = m->limit;
    }
    if (n > m->len - m->i) {
        n = m->len - m->i;
    }
    memcpy(dst, m->data + m->i, n);
    m->i += n;
    return (int)n;
}

struct sink {
    unsigned char buf[64];
    size_t len, limit, writes;
};

static int sink_write(struct sink *s, const unsigned char *src, size_t n) {
    s->writes++;
    if (n > s->limit) {
        n = s->limit;
    }
    if (s->len + n > sizeof s->buf) {
        return -1;
    }
    memcpy(s->buf + s->len, src, n);
    s->len += n;
    return (int)n;
}

/* Copy until EOF. Retries short writes. Returns byte count, or -1. */
static int copy_chunks(struct mem *src, struct sink *dst, size_t size) {
    unsigned char buf[64];
    if (size > sizeof buf) {
        return -1;
    }
    int total = 0;
    for (;;) {
        int n = mem_read(src, buf, size);
        if (n < 0) {
            return -1;
        }
        if (n == 0) {
            return total;
        }
        int off = 0;
        while (off < n) {
            int w = sink_write(dst, buf + off, (size_t)(n - off));
            if (w <= 0) {
                return -1;
            }
            off += w;
            total += w;
        }
    }
}

/* Exactly n bytes. 1 on success, 0 on clean EOF before any byte, -1 if truncated. */
static int read_full(struct mem *src, unsigned char *dst, size_t n) {
    size_t got = 0;
    while (got < n) {
        int k = mem_read(src, dst + got, n - got);
        if (k < 0) {
            return -1;
        }
        if (k == 0) {
            return got == 0 ? 0 : -1;
        }
        got += (size_t)k;
    }
    return 1;
}

static void put_be32(unsigned char *p, uint32_t n) {
    p[0] = (unsigned char)(n >> 24);
    p[1] = (unsigned char)(n >> 16);
    p[2] = (unsigned char)(n >> 8);
    p[3] = (unsigned char)n;
}

static uint32_t get_be32(const unsigned char *p) {
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}

/* 1 and payload written to dst (capacity cap), 0 on clean EOF, -1 on a short frame. */
static int read_frame(struct mem *src, unsigned char *dst, size_t cap, size_t *out_len) {
    unsigned char hdr[4];
    int rc = read_full(src, hdr, 4);
    if (rc <= 0) {
        return rc;
    }
    uint32_t n = get_be32(hdr);
    if ((size_t)n > cap) {
        return -1;
    }
    rc = read_full(src, dst, n);
    if (rc <= 0) {
        return -1;
    }
    *out_len = n;
    return 1;
}

static int atomic_write(const char *path, const void *data, size_t n) {
    char tmp[320];
    int nw = snprintf(tmp, sizeof tmp, "%s.tmp", path);
    if (nw < 0 || (size_t)nw >= sizeof tmp) {
        return -1;
    }
    FILE *f = fopen(tmp, "wb");
    if (!f) {
        return -1;
    }
    size_t wr = fwrite(data, 1, n, f);
    int flush_err = fflush(f) != 0;
    int close_err = fclose(f) != 0;
    if (wr != n || flush_err || close_err) {
        remove(tmp);
        return -1;
    }
    if (rename(tmp, path) != 0) {
        remove(tmp);
        return -1;
    }
    return 0;
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
    const unsigned char text[] = "hello world";
    struct mem src = {.data = text, .len = 11, .limit = 3};
    struct sink dst = {.limit = 2};
    int n = copy_chunks(&src, &dst, 8);
    CHECK("copy", n == 11 && dst.len == 11 && memcmp(dst.buf, "hello world", 11) == 0);

    unsigned char raw[64];
    size_t len = 0;
    put_be32(raw, 5); len = 4; memcpy(raw + len, "hello", 5); len += 5;
    put_be32(raw + len, 5); len += 4; memcpy(raw + len, "world", 5); len += 5;
    struct mem frames = {.data = raw, .len = len, .limit = 3};
    unsigned char body[32];
    size_t blen = 0;
    int rc1 = read_frame(&frames, body, sizeof body, &blen);
    int hello = rc1 == 1 && blen == 5 && memcmp(body, "hello", 5) == 0;
    int rc2 = read_frame(&frames, body, sizeof body, &blen);
    int world = rc2 == 1 && blen == 5 && memcmp(body, "world", 5) == 0;
    int rc3 = read_frame(&frames, body, sizeof body, &blen);
    CHECK("frames", hello && world && rc3 == 0);

    unsigned char badraw[16];
    size_t bl = 0;
    put_be32(badraw, 5); bl = 4; memcpy(badraw + bl, "hello", 5); bl += 5;
    badraw[bl++] = 0; badraw[bl++] = 0;
    struct mem bad = {.data = badraw, .len = bl, .limit = 1};
    read_frame(&bad, body, sizeof body, &blen);
    CHECK("truncated", read_frame(&bad, body, sizeof body, &blen) == -1);

    char dir[] = "/tmp/cstexXXXXXX";
    if (!mkdtemp(dir)) return 1;
    char path[64];
    if ((size_t)snprintf(path, sizeof path, "%s/notes.txt", dir) >= sizeof path) return 1;
    CHECK("atomic write", atomic_write(path, "hello", 5) == 0);
    FILE *f = fopen(path, "rb");
    char got[8] = {0};
    int nread = f ? (int)fread(got, 1, 5, f) : 0;
    if (f) fclose(f);
    char tmp[80];
    int leftover = 0;
    if ((size_t)snprintf(tmp, sizeof tmp, "%s.tmp", path) < sizeof tmp) {
        FILE *t = fopen(tmp, "rb");
        if (t) { leftover = 1; fclose(t); }
    }
    CHECK("atomic", nread == 5 && memcmp(got, "hello", 5) == 0 && !leftover);
    remove(path);
    rmdir(dir);
    return failed;
}
```

</details>

Next: [16 — Network programming](16-network.md)
