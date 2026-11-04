# C 08 — Memory Management

You allocate, you free. Every `malloc` needs exactly one `free`, on every
path. The compiler will not help; AddressSanitizer and Valgrind will.

A leak is a pointer lost before `free`. A double free frees twice. A
use-after-free touches memory after `free`. An overflow writes past the
end. All four are undefined, and the program may appear to work.
`free` does not have to return the pages to the OS immediately. A leak
report at exit is a bug, not noise.

Decide, for each function, who owns a pointer, and say so. Do not `free`
a stack address, a string literal, or a pointer into the middle of a
block. Never return the address of a local variable.

## malloc does not initialize

`sizeof *p` stays correct if the type of `p` changes. Check for `NULL`.
The block is uninitialized until you write it.

```c file=n01.c
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int *p = malloc(3 * sizeof *p);
    if (!p) {
        return 1;
    }
    p[0] = 1;
    p[1] = 2;
    p[2] = 3;
    printf("%d\n", p[0] + p[1] + p[2]);
    free(p);
    return 0;
}
```

```text output
6
```

## realloc may move; save the old pointer

On failure `realloc` returns `NULL` and the old block is still yours.
`p = realloc(p, n)` drops that pointer. After a successful `free`, set
the variable to `NULL`: `free(NULL)` is defined, and a null pointer
crashes instead of silently corrupting. Every old pointer into a block
is invalid once `realloc` has moved it.

```c file=n02.c
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int *p = malloc(3 * sizeof *p);
    if (!p) {
        return 1;
    }
    int *tmp = realloc(p, 6 * sizeof *p);
    if (!tmp) {
        free(p);
        return 1;
    }
    p = tmp;
    for (int i = 3; i < 6; i++) {
        p[i] = i;
    }
    printf("6 elems last=%d\n", p[5]);
    free(p);
    p = NULL;
    free(p);
    return 0;
}
```

```text output
6 elems last=5
```

## calloc zeroes and checks the product

`malloc(n * sizeof *p)` with an untrusted `n` can wrap the multiplication
and allocate a short block. `calloc` rejects that overflow and fills the
block with zero bytes.

```c file=n03.c
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int *z = calloc(4, sizeof *z);
    if (!z) {
        return 1;
    }
    printf("%d\n", z[0] + z[3]);
    free(z);
    return 0;
}
```

```text output
0
```

## The caller owns the copy

`dup_string` allocates `strlen + 1` and copies the bytes. The caller
frees it. Changing the copy does not change the literal.

```c file=n04.c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char *dup_string(const char *s) {
    size_t n = strlen(s) + 1;
    char *p = malloc(n);
    if (p) {
        memcpy(p, s, n);
    }
    return p;
}

int main(void) {
    char *copy = dup_string("owned");
    if (!copy) {
        return 1;
    }
    copy[0] = 'O';
    printf("%s\n", copy);
    free(copy);
    return 0;
}
```

```text output
Owned
```

## One buffer owns its heap bytes

Growth goes through a temporary, same as `realloc` above. `sb_free`
releases the data and zeroes the struct so a second free would be
`free(NULL)`.

```c file=n05.c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct strbuf {
    char *data;
    size_t len, cap;
};

static int sb_append(struct strbuf *sb, const char *s) {
    size_t n = strlen(s);
    if (sb->len + n + 1 > sb->cap) {
        size_t ncap = sb->cap ? sb->cap : 8;
        while (ncap < sb->len + n + 1) {
            ncap *= 2;
        }
        char *p = realloc(sb->data, ncap);
        if (!p) {
            return -1;
        }
        sb->data = p;
        sb->cap = ncap;
    }
    memcpy(sb->data + sb->len, s, n + 1);
    sb->len += n;
    return 0;
}

static void sb_free(struct strbuf *sb) {
    free(sb->data);
    *sb = (struct strbuf){0};
}

int main(void) {
    struct strbuf sb = {0};
    if (sb_append(&sb, "foo") != 0 || sb_append(&sb, "bar") != 0) {
        return 1;
    }
    printf("%s %zu\n", sb.data, sb.len);
    sb_free(&sb);
    return 0;
}
```

```text output
foobar 6
```

## Free the node only after you have saved next

The link lives in the node. Read `next`, then `free`. Losing `next`
first is a leak of the rest of the list, or a use-after-free if you
follow it anyway.

```c file=n06.c
#include <stdio.h>
#include <stdlib.h>

struct node {
    int value;
    struct node *next;
};

static struct node *push_front(struct node *head, int v) {
    struct node *n = malloc(sizeof *n);
    if (!n) {
        return head;
    }
    n->value = v;
    n->next = head;
    return n;
}

static void list_free(struct node *head) {
    while (head) {
        struct node *next = head->next;
        free(head);
        head = next;
    }
}

int main(void) {
    struct node *head = NULL;
    for (int i = 3; i >= 1; i--) {
        head = push_front(head, i);
    }
    for (struct node *n = head; n; n = n->next) {
        printf("%d ", n->value);
    }
    printf("\n");
    list_free(head);
    return 0;
}
```

```text output
1 2 3 
```

## An arena frees many allocations at once

Bump the cursor, aligned, and hand out pointers into one array. Nothing
is freed individually. `align` must be a power of two. The second block
starts at offset 8, and 4 more bytes make `used` 12.

```c file=n07.c
#include <stdio.h>

struct arena {
    unsigned char *base;
    size_t cap, used;
};

static void *arena_alloc(struct arena *a, size_t size, size_t align) {
    size_t off = (a->used + align - 1) & ~(align - 1);
    if (off + size > a->cap) {
        return NULL;
    }
    a->used = off + size;
    return a->base + off;
}

int main(void) {
    unsigned char storage[64];
    struct arena a = {storage, sizeof storage, 0};
    unsigned char *p1 = arena_alloc(&a, 5, 1);
    unsigned char *p2 = arena_alloc(&a, 4, 8);
    if (!p1 || !p2) {
        return 1;
    }
    printf("%td %td used=%zu\n", p1 - storage, p2 - storage, a.used);
    return 0;
}
```

```text output
0 8 used=12
```

## Every type has an alignment

`_Alignof(double)` is 8 here, and `_Alignof(char)` is 1. An address that
is not a multiple of the alignment is not a valid pointer to that type.
The arena above rounds up so the second block is aligned for a wider type.

```c file=n08.c
#include <stdio.h>

int main(void) {
    printf("%zu %zu\n", _Alignof(double), _Alignof(char));
    return 0;
}
```

```text output
8 1
```


## Exercises

```c file=exercise.c
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Heap copy of s (caller frees). NULL on failure. */
char *str_dup(const char *s) {
    (void)s;
    return NULL; /* TODO */
}

/* New heap string a followed by b (caller frees). */
char *str_concat(const char *a, const char *b) {
    (void)a; (void)b;
    return NULL; /* TODO */
}

/* Array [0, 1, ..., n-1] on the heap; NULL when n <= 0. */
int *make_range(int n) {
    (void)n;
    return NULL; /* TODO */
}

struct node {
    int value;
    struct node *next;
};

/* Add at the front, return the new head (old head on allocation failure). */
struct node *list_push_front(struct node *head, int v) {
    (void)v;
    return head; /* TODO */
}

/* Reverse the list in place, return the new head. */
struct node *list_reverse(struct node *head) {
    return head; /* TODO */
}

size_t list_length(const struct node *head) {
    (void)head;
    return 99; /* TODO */
}

/* Free every node. */
void list_free(struct node *head) {
    (void)head; /* TODO */
}

struct matrix {
    int rows, cols;
    double *data; /* rows * cols, row-major, zero-initialised */
};

/* NULL on failure or non-positive dimensions. */
struct matrix *matrix_new(int rows, int cols) {
    (void)rows; (void)cols;
    return NULL; /* TODO */
}

void matrix_set(struct matrix *m, int r, int c, double v) {
    (void)m; (void)r; (void)c; (void)v; /* TODO */
}

double matrix_get(const struct matrix *m, int r, int c) {
    (void)m; (void)r; (void)c;
    return -1; /* TODO */
}

void matrix_free(struct matrix *m) {
    (void)m; /* TODO */
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
    char local[] = "abc";
    char *d = str_dup(local);
    local[0] = 'X';
    CHECK("dup", d && strcmp(d, "abc") == 0);
    free(d);

    char *c = str_concat("foo", "bar");
    CHECK("concat", c && strcmp(c, "foobar") == 0);
    free(c);

    int *r = make_range(5);
    CHECK("range", r && r[0] == 0 && r[4] == 4);
    free(r);
    CHECK("range none", make_range(0) == NULL);

    struct node *l = NULL;
    for (int i = 1; i <= 3; i++) {
        l = list_push_front(l, i);
    }
    CHECK("push order", l && l->value == 3 && l->next->value == 2);
    CHECK("length", list_length(l) == 3);
    l = list_reverse(l);
    CHECK("reverse", l && l->value == 1 && l->next->next->value == 3);
    list_free(l);
    CHECK("length empty", list_length(NULL) == 0);

    struct matrix *m = matrix_new(2, 3);
    CHECK("matrix new", m && matrix_get(m, 1, 2) == 0.0);
    if (m) {
        matrix_set(m, 1, 2, 7.5);
        matrix_set(m, 0, 0, 1.5);
        CHECK("matrix set", matrix_get(m, 1, 2) == 7.5 && matrix_get(m, 0, 0) == 1.5);
    }
    matrix_free(m);
    CHECK("matrix bad", matrix_new(0, 3) == NULL);
    return failed;
}
```

<details><summary>Solution</summary>

```c file=solution.c
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

char *str_dup(const char *s) {
    size_t n = strlen(s) + 1;
    char *p = malloc(n);
    if (p) {
        memcpy(p, s, n);
    }
    return p;
}

char *str_concat(const char *a, const char *b) {
    size_t la = strlen(a), lb = strlen(b);
    char *p = malloc(la + lb + 1);
    if (!p) {
        return NULL;
    }
    memcpy(p, a, la);
    memcpy(p + la, b, lb + 1);
    return p;
}

int *make_range(int n) {
    if (n <= 0) {
        return NULL;
    }
    int *p = malloc((size_t)n * sizeof *p);
    if (!p) {
        return NULL;
    }
    for (int i = 0; i < n; i++) {
        p[i] = i;
    }
    return p;
}

struct node {
    int value;
    struct node *next;
};

struct node *list_push_front(struct node *head, int v) {
    struct node *n = malloc(sizeof *n);
    if (!n) {
        return head;
    }
    n->value = v;
    n->next = head;
    return n;
}

struct node *list_reverse(struct node *head) {
    struct node *prev = NULL;
    while (head) {
        struct node *next = head->next;
        head->next = prev;
        prev = head;
        head = next;
    }
    return prev;
}

size_t list_length(const struct node *head) {
    size_t n = 0;
    for (; head; head = head->next) {
        n++;
    }
    return n;
}

void list_free(struct node *head) {
    while (head) {
        struct node *next = head->next;
        free(head);
        head = next;
    }
}

struct matrix {
    int rows, cols;
    double *data;
};

struct matrix *matrix_new(int rows, int cols) {
    if (rows <= 0 || cols <= 0) {
        return NULL;
    }
    struct matrix *m = malloc(sizeof *m);
    if (!m) {
        return NULL;
    }
    m->data = calloc((size_t)rows * (size_t)cols, sizeof *m->data);
    if (!m->data) {
        free(m);
        return NULL;
    }
    m->rows = rows;
    m->cols = cols;
    return m;
}

void matrix_set(struct matrix *m, int r, int c, double v) {
    m->data[(size_t)r * (size_t)m->cols + (size_t)c] = v;
}

double matrix_get(const struct matrix *m, int r, int c) {
    return m->data[(size_t)r * (size_t)m->cols + (size_t)c];
}

void matrix_free(struct matrix *m) {
    if (m) {
        free(m->data);
        free(m);
    }
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
    char local[] = "abc";
    char *d = str_dup(local);
    local[0] = 'X';
    CHECK("dup", d && strcmp(d, "abc") == 0);
    free(d);

    char *c = str_concat("foo", "bar");
    CHECK("concat", c && strcmp(c, "foobar") == 0);
    free(c);

    int *r = make_range(5);
    CHECK("range", r && r[0] == 0 && r[4] == 4);
    free(r);
    CHECK("range none", make_range(0) == NULL);

    struct node *l = NULL;
    for (int i = 1; i <= 3; i++) {
        l = list_push_front(l, i);
    }
    CHECK("push order", l && l->value == 3 && l->next->value == 2);
    CHECK("length", list_length(l) == 3);
    l = list_reverse(l);
    CHECK("reverse", l && l->value == 1 && l->next->next->value == 3);
    list_free(l);
    CHECK("length empty", list_length(NULL) == 0);

    struct matrix *m = matrix_new(2, 3);
    CHECK("matrix new", m && matrix_get(m, 1, 2) == 0.0);
    if (m) {
        matrix_set(m, 1, 2, 7.5);
        matrix_set(m, 0, 0, 1.5);
        CHECK("matrix set", matrix_get(m, 1, 2) == 7.5 && matrix_get(m, 0, 0) == 1.5);
    }
    matrix_free(m);
    CHECK("matrix bad", matrix_new(0, 3) == NULL);
    return failed;
}
```

</details>

Next: [09 — Abstraction](09-abstraction.md)
