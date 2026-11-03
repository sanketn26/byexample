# C 16 — Network programming

A TCP socket is the stream from the previous lesson with a peer attached. `read` and `write` are the same calls. `poll` is how you wait with a deadline instead of blocking forever. HTTP/1.1 below is a length-prefixed body with ASCII headers in front, written by hand.

## Example

```c file=example.c
#define _POSIX_C_SOURCE 200809L
#include <arpa/inet.h>
#include <ctype.h>
#include <errno.h>
#include <netinet/in.h>
#include <poll.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static int read_full(int fd, unsigned char *dst, size_t n) {
    size_t got = 0;
    while (got < n) {
        ssize_t k = read(fd, dst + got, n - got);
        if (k == 0) {
            return got == 0 ? 0 : -1;
        }
        if (k < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        got += (size_t)k;
    }
    return 1;
}

static int write_full(int fd, const unsigned char *src, size_t n) {
    size_t off = 0;
    while (off < n) {
        ssize_t k = write(fd, src + off, n - off);
        if (k < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (k == 0) {
            return -1;
        }
        off += (size_t)k;
    }
    return 0;
}

static int listen_loopback(uint16_t *port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        return -1;
    }
    int yes = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof addr);
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = 0;
    if (bind(fd, (struct sockaddr *)&addr, sizeof addr) != 0 || listen(fd, 8) != 0) {
        close(fd);
        return -1;
    }
    socklen_t len = sizeof addr;
    if (getsockname(fd, (struct sockaddr *)&addr, &len) != 0) {
        close(fd);
        return -1;
    }
    *port = ntohs(addr.sin_port);
    return fd;
}

static int connect_loopback(uint16_t port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        return -1;
    }
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof addr);
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = htons(port);
    if (connect(fd, (struct sockaddr *)&addr, sizeof addr) != 0) {
        close(fd);
        return -1;
    }
    return fd;
}

struct serve_arg {
    int ready;
    uint16_t port;
};

static void *serve(void *arg) {
    struct serve_arg *a = arg;
    int ls = listen_loopback(&a->port);
    char go = 1;
    if (ls < 0 || write(a->ready, &go, 1) != 1) {
        return NULL;
    }
    const char *mode[] = {"echo", "silent", "drop"};
    for (int i = 0; i < 3; i++) {
        int conn = accept(ls, NULL, NULL);
        if (conn < 0) {
            break;
        }
        if (strcmp(mode[i], "echo") == 0) {
            unsigned char hdr[4];
            if (read_full(conn, hdr, 4) == 1) {
                uint32_t n = ((uint32_t)hdr[0] << 24) | ((uint32_t)hdr[1] << 16) |
                             ((uint32_t)hdr[2] << 8) | hdr[3];
                unsigned char *body = malloc(n ? n : 1);
                if (body && read_full(conn, body, n) == 1) {
                    for (uint32_t j = 0; j < n; j++) {
                        body[j] = (unsigned char)toupper(body[j]);
                    }
                    unsigned char *out = malloc(4 + n);
                    if (out) {
                        memcpy(out, hdr, 4);
                        memcpy(out + 4, body, n);
                        write_full(conn, out, 4 + n);
                        free(out);
                    }
                }
                free(body);
            }
        } else if (strcmp(mode[i], "silent") == 0) {
            struct pollfd p = {.fd = conn, .events = POLLIN};
            poll(&p, 1, 2000);
        } else {
            unsigned char partial[2] = {0, 0};
            write_full(conn, partial, 2);
        }
        close(conn);
    }
    close(ls);
    return NULL;
}

static int read_frame(int fd, unsigned char *dst, size_t cap, size_t *out) {
    unsigned char hdr[4];
    int rc = read_full(fd, hdr, 4);
    if (rc <= 0) {
        return rc;
    }
    uint32_t n = ((uint32_t)hdr[0] << 24) | ((uint32_t)hdr[1] << 16) |
                 ((uint32_t)hdr[2] << 8) | hdr[3];
    if ((size_t)n > cap) {
        return -1;
    }
    rc = read_full(fd, dst, n);
    if (rc <= 0) {
        return -1;
    }
    *out = n;
    return 1;
}

static void *http_one(void *arg) {
    int ls = *(int *)arg;
    int conn = accept(ls, NULL, NULL);
    if (conn < 0) {
        return NULL;
    }
    char req[512];
    size_t got = 0;
    while (got + 1 < sizeof req) {
        ssize_t k = read(conn, req + got, sizeof req - 1 - got);
        if (k <= 0) {
            break;
        }
        got += (size_t)k;
        req[got] = '\0';
        if (strstr(req, "\r\n\r\n") != NULL) {
            break;
        }
    }
    const char *resp = "HTTP/1.1 200 OK\r\nContent-Length: 7\r\nConnection: close\r\n\r\necho:hi";
    write_full(conn, (const unsigned char *)resp, strlen(resp));
    close(conn);
    return NULL;
}

int main(void) {
    int ready[2];
    if (pipe(ready) != 0) {
        return 1;
    }
    struct serve_arg arg = {.ready = ready[1], .port = 0};
    pthread_t th;
    if (pthread_create(&th, NULL, serve, &arg) != 0) {
        return 1;
    }
    char go = 0;
    if (read(ready[0], &go, 1) != 1) {
        return 1;
    }
    close(ready[0]);
    close(ready[1]);

    int c = connect_loopback(arg.port);
    unsigned char req[8] = {0, 0, 0, 4, 'p', 'i', 'n', 'g'};
    write_full(c, req, sizeof req);
    unsigned char body[16];
    size_t n = 0;
    int rc = read_frame(c, body, sizeof body, &n);
    printf("frame %d %.*s\n", rc, (int)n, body);
    close(c);

    c = connect_loopback(arg.port);
    struct pollfd p = {.fd = c, .events = POLLIN};
    int pr = poll(&p, 1, 150);
    printf("%s\n", pr == 0 ? "timeout" : "unexpected");
    close(c);

    c = connect_loopback(arg.port);
    rc = read_frame(c, body, sizeof body, &n);
    printf("%s\n", rc < 0 ? "truncated" : "unexpected");
    close(c);
    pthread_join(th, NULL);

    uint16_t hp = 0;
    int hs = listen_loopback(&hp);
    if (hs < 0) {
        return 1;
    }
    pthread_t http;
    if (pthread_create(&http, NULL, http_one, &hs) != 0) {
        return 1;
    }
    c = connect_loopback(hp);
    const char *hreq =
        "POST /echo HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: 2\r\n"
        "Connection: close\r\n\r\nhi";
    write_full(c, (const unsigned char *)hreq, strlen(hreq));
    char resp[256];
    size_t rn = 0;
    while (rn + 1 < sizeof resp) {
        ssize_t k = read(c, resp + rn, sizeof resp - 1 - rn);
        if (k <= 0) {
            break;
        }
        rn += (size_t)k;
    }
    resp[rn] = '\0';
    close(c);
    char *split = strstr(resp, "\r\n\r\n");
    printf("http %s\n", split ? split + 4 : "bad");
    pthread_join(http, NULL);
    close(hs);
    return 0;
}
```

```text output
frame 1 PING
timeout
truncated
http echo:hi
```

## Details that bite

- TCP is a stream of bytes, not a stream of messages. One `read` can
  return a single byte of a frame. Loop until the length prefix and the
  body are both complete.
- Bind `127.0.0.1` and port 0. The kernel picks a free port. The port
  changes every run, so the example prints the payload, not the address.
- A timeout and a peer who closes mid-frame are different errors. The
  timeout does not cancel the server: close your side, or the accept
  loop stays stuck in the connection you abandoned.
- On Rust, `set_read_timeout` usually surfaces as `ErrorKind::WouldBlock`,
  not `TimedOut`. Treat both as a timeout.
- HTTP/1.1 is the same loop plus ASCII headers. `Content-Length` tells
  you when the body ends; `Connection: close` is the other signal. Go's
  `net/http` and a hand-written request in C or Rust put the same bytes
  on the socket.
- This is not TLS, HTTP/2, or `epoll`. Those are the next layer down or
  up. Tokio is the async version of this lesson and needs Cargo; the file
  here stays on `std::net` and threads so `rustc` still builds it.

## Exercises

The harness is a small server. `exchange` sends one frame and reads one. `classify` returns 1 on timeout, -1 when the frame is cut off, and 0 when a full frame arrives. `http_body` POSTs `hi` and copies the response body out.

```c file=exercise.c
#define _POSIX_C_SOURCE 200809L
#include <arpa/inet.h>
#include <ctype.h>
#include <errno.h>
#include <netinet/in.h>
#include <poll.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define static static __attribute__((unused))

static int read_full(int fd, unsigned char *dst, size_t n) {
    size_t got = 0;
    while (got < n) {
        ssize_t k = read(fd, dst + got, n - got);
        if (k == 0) {
            return got == 0 ? 0 : -1;
        }
        if (k < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        got += (size_t)k;
    }
    return 1;
}

static int write_full(int fd, const unsigned char *src, size_t n) {
    size_t off = 0;
    while (off < n) {
        ssize_t k = write(fd, src + off, n - off);
        if (k < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (k == 0) {
            return -1;
        }
        off += (size_t)k;
    }
    return 0;
}

static int listen_loopback(uint16_t *port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        return -1;
    }
    int yes = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof addr);
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = 0;
    if (bind(fd, (struct sockaddr *)&addr, sizeof addr) != 0 || listen(fd, 8) != 0) {
        close(fd);
        return -1;
    }
    socklen_t len = sizeof addr;
    if (getsockname(fd, (struct sockaddr *)&addr, &len) != 0) {
        close(fd);
        return -1;
    }
    *port = ntohs(addr.sin_port);
    return fd;
}

static int connect_loopback(uint16_t port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        return -1;
    }
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof addr);
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = htons(port);
    if (connect(fd, (struct sockaddr *)&addr, sizeof addr) != 0) {
        close(fd);
        return -1;
    }
    return fd;
}

struct serve_arg {
    int ready;
    uint16_t port;
};

static void *serve(void *arg) {
    struct serve_arg *a = arg;
    int ls = listen_loopback(&a->port);
    char go = 1;
    if (ls < 0 || write(a->ready, &go, 1) != 1) {
        return NULL;
    }
    const char *mode[] = {"echo", "silent", "drop"};
    for (int i = 0; i < 3; i++) {
        int conn = accept(ls, NULL, NULL);
        if (conn < 0) {
            break;
        }
        if (strcmp(mode[i], "echo") == 0) {
            unsigned char hdr[4];
            if (read_full(conn, hdr, 4) == 1) {
                uint32_t n = ((uint32_t)hdr[0] << 24) | ((uint32_t)hdr[1] << 16) |
                             ((uint32_t)hdr[2] << 8) | hdr[3];
                unsigned char *body = malloc(n ? n : 1);
                if (body && read_full(conn, body, n) == 1) {
                    for (uint32_t j = 0; j < n; j++) {
                        body[j] = (unsigned char)toupper(body[j]);
                    }
                    unsigned char *out = malloc(4 + n);
                    if (out) {
                        memcpy(out, hdr, 4);
                        memcpy(out + 4, body, n);
                        write_full(conn, out, 4 + n);
                        free(out);
                    }
                }
                free(body);
            }
        } else if (strcmp(mode[i], "silent") == 0) {
            struct pollfd p = {.fd = conn, .events = POLLIN};
            poll(&p, 1, 2000);
        } else {
            unsigned char partial[2] = {0, 0};
            write_full(conn, partial, 2);
        }
        close(conn);
    }
    close(ls);
    return NULL;
}

static int read_frame(int fd, unsigned char *dst, size_t cap, size_t *out) {
    unsigned char hdr[4];
    int rc = read_full(fd, hdr, 4);
    if (rc <= 0) {
        return rc;
    }
    uint32_t n = ((uint32_t)hdr[0] << 24) | ((uint32_t)hdr[1] << 16) |
                 ((uint32_t)hdr[2] << 8) | hdr[3];
    if ((size_t)n > cap) {
        return -1;
    }
    rc = read_full(fd, dst, n);
    if (rc <= 0) {
        return -1;
    }
    *out = n;
    return 1;
}

static void *http_one(void *arg) {
    int ls = *(int *)arg;
    int conn = accept(ls, NULL, NULL);
    if (conn < 0) {
        return NULL;
    }
    char req[512];
    size_t got = 0;
    while (got + 1 < sizeof req) {
        ssize_t k = read(conn, req + got, sizeof req - 1 - got);
        if (k <= 0) {
            break;
        }
        got += (size_t)k;
        req[got] = '\0';
        if (strstr(req, "\r\n\r\n") != NULL) {
            break;
        }
    }
    const char *resp = "HTTP/1.1 200 OK\r\nContent-Length: 7\r\nConnection: close\r\n\r\necho:hi";
    write_full(conn, (const unsigned char *)resp, strlen(resp));
    close(conn);
    return NULL;
}


static int exchange(uint16_t port, const unsigned char *payload, size_t n,
                    unsigned char *out, size_t cap, size_t *outn) {
    (void)port; (void)payload; (void)n; (void)out; (void)cap; (void)outn;
    return -1;
}



/* 1 on timeout, -1 on a truncated frame, 0 if a full frame arrived. */
static int classify(int fd, int timeout_ms) {
    (void)fd; (void)timeout_ms;
    return 99;
}



static int http_body(uint16_t port, char *out, size_t cap) {
    (void)port; (void)out; (void)cap;
    return -1;
}



static int failed;
#define CHECK(label, cond)                         \
    do {                                           \
        if (cond) printf("PASS %s\n", label);      \
        else { failed = 1; printf("FAIL %s\n", label); } \
    } while (0)

int main(void) {
    int ready[2];
    if (pipe(ready) != 0) return 1;
    struct serve_arg arg = {.ready = ready[1], .port = 0};
    pthread_t th;
    if (pthread_create(&th, NULL, serve, &arg) != 0) return 1;
    char go = 0;
    if (read(ready[0], &go, 1) != 1) return 1;
    close(ready[0]);
    close(ready[1]);

    unsigned char body[16];
    size_t n = 0;
    int rc = exchange(arg.port, (const unsigned char *)"ping", 4, body, sizeof body, &n);
    CHECK("exchange", rc == 1 && n == 4 && memcmp(body, "PING", 4) == 0);

    int c = connect_loopback(arg.port);
    CHECK("timeout", classify(c, 150) == 1);
    close(c);
    c = connect_loopback(arg.port);
    CHECK("truncated", classify(c, 500) == -1);
    close(c);
    /* A stub that never connects must not leave the server blocked in accept. */
    int extra = connect_loopback(arg.port);
    if (extra >= 0) {
        close(extra);
    }
    pthread_join(th, NULL);

    uint16_t hp = 0;
    int hs = listen_loopback(&hp);
    pthread_t http;
    if (hs < 0 || pthread_create(&http, NULL, http_one, &hs) != 0) return 1;
    char hbody[32];
    CHECK("http", http_body(hp, hbody, sizeof hbody) == 0 && strcmp(hbody, "echo:hi") == 0);
    /* If http_body never connected, wake the server so join can finish. */
    int extra_http = connect_loopback(hp);
    if (extra_http >= 0) {
        close(extra_http);
    }
    pthread_join(http, NULL);
    close(hs);
    return failed;
}
```

<details><summary>Solution</summary>

```c file=solution.c
#define _POSIX_C_SOURCE 200809L
#include <arpa/inet.h>
#include <ctype.h>
#include <errno.h>
#include <netinet/in.h>
#include <poll.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static int read_full(int fd, unsigned char *dst, size_t n) {
    size_t got = 0;
    while (got < n) {
        ssize_t k = read(fd, dst + got, n - got);
        if (k == 0) {
            return got == 0 ? 0 : -1;
        }
        if (k < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        got += (size_t)k;
    }
    return 1;
}

static int write_full(int fd, const unsigned char *src, size_t n) {
    size_t off = 0;
    while (off < n) {
        ssize_t k = write(fd, src + off, n - off);
        if (k < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (k == 0) {
            return -1;
        }
        off += (size_t)k;
    }
    return 0;
}

static int listen_loopback(uint16_t *port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        return -1;
    }
    int yes = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof addr);
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = 0;
    if (bind(fd, (struct sockaddr *)&addr, sizeof addr) != 0 || listen(fd, 8) != 0) {
        close(fd);
        return -1;
    }
    socklen_t len = sizeof addr;
    if (getsockname(fd, (struct sockaddr *)&addr, &len) != 0) {
        close(fd);
        return -1;
    }
    *port = ntohs(addr.sin_port);
    return fd;
}

static int connect_loopback(uint16_t port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        return -1;
    }
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof addr);
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = htons(port);
    if (connect(fd, (struct sockaddr *)&addr, sizeof addr) != 0) {
        close(fd);
        return -1;
    }
    return fd;
}

struct serve_arg {
    int ready;
    uint16_t port;
};

static void *serve(void *arg) {
    struct serve_arg *a = arg;
    int ls = listen_loopback(&a->port);
    char go = 1;
    if (ls < 0 || write(a->ready, &go, 1) != 1) {
        return NULL;
    }
    const char *mode[] = {"echo", "silent", "drop"};
    for (int i = 0; i < 3; i++) {
        int conn = accept(ls, NULL, NULL);
        if (conn < 0) {
            break;
        }
        if (strcmp(mode[i], "echo") == 0) {
            unsigned char hdr[4];
            if (read_full(conn, hdr, 4) == 1) {
                uint32_t n = ((uint32_t)hdr[0] << 24) | ((uint32_t)hdr[1] << 16) |
                             ((uint32_t)hdr[2] << 8) | hdr[3];
                unsigned char *body = malloc(n ? n : 1);
                if (body && read_full(conn, body, n) == 1) {
                    for (uint32_t j = 0; j < n; j++) {
                        body[j] = (unsigned char)toupper(body[j]);
                    }
                    unsigned char *out = malloc(4 + n);
                    if (out) {
                        memcpy(out, hdr, 4);
                        memcpy(out + 4, body, n);
                        write_full(conn, out, 4 + n);
                        free(out);
                    }
                }
                free(body);
            }
        } else if (strcmp(mode[i], "silent") == 0) {
            struct pollfd p = {.fd = conn, .events = POLLIN};
            poll(&p, 1, 2000);
        } else {
            unsigned char partial[2] = {0, 0};
            write_full(conn, partial, 2);
        }
        close(conn);
    }
    close(ls);
    return NULL;
}

static int read_frame(int fd, unsigned char *dst, size_t cap, size_t *out) {
    unsigned char hdr[4];
    int rc = read_full(fd, hdr, 4);
    if (rc <= 0) {
        return rc;
    }
    uint32_t n = ((uint32_t)hdr[0] << 24) | ((uint32_t)hdr[1] << 16) |
                 ((uint32_t)hdr[2] << 8) | hdr[3];
    if ((size_t)n > cap) {
        return -1;
    }
    rc = read_full(fd, dst, n);
    if (rc <= 0) {
        return -1;
    }
    *out = n;
    return 1;
}

static void *http_one(void *arg) {
    int ls = *(int *)arg;
    int conn = accept(ls, NULL, NULL);
    if (conn < 0) {
        return NULL;
    }
    char req[512];
    size_t got = 0;
    while (got + 1 < sizeof req) {
        ssize_t k = read(conn, req + got, sizeof req - 1 - got);
        if (k <= 0) {
            break;
        }
        got += (size_t)k;
        req[got] = '\0';
        if (strstr(req, "\r\n\r\n") != NULL) {
            break;
        }
    }
    const char *resp = "HTTP/1.1 200 OK\r\nContent-Length: 7\r\nConnection: close\r\n\r\necho:hi";
    write_full(conn, (const unsigned char *)resp, strlen(resp));
    close(conn);
    return NULL;
}


static int exchange(uint16_t port, const unsigned char *payload, size_t n,
                    unsigned char *out, size_t cap, size_t *outn) {
    int fd = connect_loopback(port);
    if (fd < 0) return -1;
    unsigned char hdr[4];
    hdr[0] = (unsigned char)(n >> 24);
    hdr[1] = (unsigned char)(n >> 16);
    hdr[2] = (unsigned char)(n >> 8);
    hdr[3] = (unsigned char)n;
    int rc = -1;
    if (write_full(fd, hdr, 4) == 0 && write_full(fd, payload, n) == 0) {
        rc = read_frame(fd, out, cap, outn);
    }
    close(fd);
    return rc;
}

/* 1 on timeout, -1 on a truncated frame, 0 if a full frame arrived. */
static int classify(int fd, int timeout_ms) {
    struct pollfd p = {.fd = fd, .events = POLLIN};
    int pr = poll(&p, 1, timeout_ms);
    if (pr == 0) return 1;
    if (pr < 0) return -1;
    unsigned char body[32];
    size_t n = 0;
    int rc = read_frame(fd, body, sizeof body, &n);
    return rc == 1 ? 0 : -1;
}

static int http_body(uint16_t port, char *out, size_t cap) {
    int fd = connect_loopback(port);
    if (fd < 0) return -1;
    const char *req =
        "POST /echo HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: 2\r\n"
        "Connection: close\r\n\r\nhi";
    if (write_full(fd, (const unsigned char *)req, strlen(req)) != 0) {
        close(fd);
        return -1;
    }
    char resp[256];
    size_t rn = 0;
    while (rn + 1 < sizeof resp) {
        ssize_t k = read(fd, resp + rn, sizeof resp - 1 - rn);
        if (k < 0 && errno == EINTR) continue;
        if (k <= 0) break;
        rn += (size_t)k;
    }
    resp[rn] = '\0';
    close(fd);
    char *split = strstr(resp, "\r\n\r\n");
    if (!split) return -1;
    split += 4;
    if (strlen(split) + 1 > cap) return -1;
    memcpy(out, split, strlen(split) + 1);
    return 0;
}

static int failed;
#define CHECK(label, cond)                         \
    do {                                           \
        if (cond) printf("PASS %s\n", label);      \
        else { failed = 1; printf("FAIL %s\n", label); } \
    } while (0)

int main(void) {
    int ready[2];
    if (pipe(ready) != 0) return 1;
    struct serve_arg arg = {.ready = ready[1], .port = 0};
    pthread_t th;
    if (pthread_create(&th, NULL, serve, &arg) != 0) return 1;
    char go = 0;
    if (read(ready[0], &go, 1) != 1) return 1;
    close(ready[0]);
    close(ready[1]);

    unsigned char body[16];
    size_t n = 0;
    int rc = exchange(arg.port, (const unsigned char *)"ping", 4, body, sizeof body, &n);
    CHECK("exchange", rc == 1 && n == 4 && memcmp(body, "PING", 4) == 0);

    int c = connect_loopback(arg.port);
    CHECK("timeout", classify(c, 150) == 1);
    close(c);
    c = connect_loopback(arg.port);
    CHECK("truncated", classify(c, 500) == -1);
    close(c);
    /* A stub that never connects must not leave the server blocked in accept. */
    int extra = connect_loopback(arg.port);
    if (extra >= 0) {
        close(extra);
    }
    pthread_join(th, NULL);

    uint16_t hp = 0;
    int hs = listen_loopback(&hp);
    pthread_t http;
    if (hs < 0 || pthread_create(&http, NULL, http_one, &hs) != 0) return 1;
    char hbody[32];
    CHECK("http", http_body(hp, hbody, sizeof hbody) == 0 && strcmp(hbody, "echo:hi") == 0);
    /* If http_body never connected, wake the server so join can finish. */
    int extra_http = connect_loopback(hp);
    if (extra_http >= 0) {
        close(extra_http);
    }
    pthread_join(http, NULL);
    close(hs);
    return failed;
}
```

</details>

Next: [17 — Advanced concurrency](17-advanced-concurrency.md)
