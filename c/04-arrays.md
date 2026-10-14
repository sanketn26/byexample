# C 04 — Arrays and Collections

C has fixed-size arrays and pointers. Anything more (vectors, maps, sets) you
build yourself — that is half the point of learning C.

## Example

```c file=example.c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ARRAY_LEN(a) (sizeof(a) / sizeof((a)[0]))

struct person {
    const char *name;
    int age;
};

/* Comparators for qsort take const void * and return <0, 0, >0 */
static int cmp_int(const void *pa, const void *pb) {
    int a = *(const int *)pa, b = *(const int *)pb;
    return (a > b) - (a < b); /* never `a - b`: it can overflow */
}

static int cmp_age(const void *pa, const void *pb) {
    const struct person *a = pa, *b = pb;
    return (a->age > b->age) - (a->age < b->age);
}

/* A growable array, the C way */
struct intvec {
    int *data;
    size_t len, cap;
};

static int intvec_push(struct intvec *v, int x) {
    if (v->len == v->cap) {
        size_t ncap = v->cap ? v->cap * 2 : 4;
        int *p = realloc(v->data, ncap * sizeof *p);
        if (!p) {
            return -1; /* old block is still valid and still owned */
        }
        v->data = p;
        v->cap = ncap;
    }
    v->data[v->len++] = x;
    return 0;
}

int main(void) {
    int a[5] = {1, 2, 3}; /* the rest is zero-filled */
    for (size_t i = 0; i < ARRAY_LEN(a); i++) {
        printf("%d ", a[i]);
    }
    printf("\n");

    int sparse[6] = {[1] = 10, [4] = 40}; /* designated initialisers */
    for (size_t i = 0; i < ARRAY_LEN(sparse); i++) {
        printf("%d ", sparse[i]);
    }
    printf("\n");
    printf("%zu\n", ARRAY_LEN(a));

    /* a[i] is *(a + i) */
    int *p = a;
    printf("%d %d %d\n", *(p + 2), a[2], 2 [a]);
    printf("%td\n", &a[4] - &a[1]); /* pointer difference is in elements */

    /* 2-D arrays are arrays of arrays, stored row-major */
    int m[2][3] = {{1, 2, 3}, {4, 5, 6}};
    int total = 0;
    for (int r = 0; r < 2; r++) {
        for (int c = 0; c < 3; c++) {
            total += m[r][c];
        }
    }
    printf("%d %d %zu\n", total, m[1][2], sizeof m);

    /* qsort and bsearch */
    int nums[] = {5, 2, 9, 1};
    qsort(nums, ARRAY_LEN(nums), sizeof nums[0], cmp_int);
    for (size_t i = 0; i < ARRAY_LEN(nums); i++) {
        printf("%d%c", nums[i], i + 1 < ARRAY_LEN(nums) ? ' ' : '\n');
    }
    int key = 5;
    int *hit = bsearch(&key, nums, ARRAY_LEN(nums), sizeof nums[0], cmp_int);
    printf("found at %td\n", hit - nums);

    struct person people[] = {{"Cy", 35}, {"Al", 30}, {"Bo", 25}};
    qsort(people, ARRAY_LEN(people), sizeof people[0], cmp_age);
    for (size_t i = 0; i < ARRAY_LEN(people); i++) {
        printf("%s:%d ", people[i].name, people[i].age);
    }
    printf("\n");

    /* Arrays cannot be assigned: use memcpy / memset */
    int b[5];
    memcpy(b, a, sizeof b);
    for (size_t i = 0; i < ARRAY_LEN(b); i++) {
        printf("%d ", b[i]);
    }
    printf("\n");
    memset(b, 0, sizeof b);
    for (size_t i = 0; i < ARRAY_LEN(b); i++) {
        printf("%d ", b[i]);
    }
    printf("\n");

    /* Dynamic array */
    struct intvec v = {0};
    for (int i = 0; i < 10; i++) {
        if (intvec_push(&v, i) != 0) {
            return 1;
        }
    }
    printf("len=%zu cap=%zu last=%d\n", v.len, v.cap, v.data[v.len - 1]);
    free(v.data);
    return 0;
}
```

```text output
1 2 3 0 0 
0 10 0 0 40 0 
5
3 3 3
3
21 6 24
1 2 5 9
found at 2
Bo:25 Al:30 Cy:35 
1 2 3 0 0 
0 0 0 0 0 
len=10 cap=16 last=9
```

## Details that bite

- **No bounds checking.** Reading or writing `a[5]` on a 5-element array is
  undefined behaviour: it may crash, corrupt memory, or seem to work.
  Build with `-fsanitize=address` to catch it.
- `sizeof a / sizeof a[0]` works only where `a` is a real array, not a
  parameter or a `malloc`ed pointer.
- `a == b` on arrays compares *addresses*, not contents; use `memcmp`
  (but beware padding bytes inside structs).
- A comparator that returns `a - b` overflows for large values. Use
  `(a > b) - (a < b)`.
- Always assign `realloc`'s result to a temporary: on failure it returns
  `NULL` and the old block is still yours (and must still be freed).
- A pointer may legally point one past the end of an array but must not be
  dereferenced.
- Avoid variable-length arrays (`int a[n]`) for untrusted sizes: a large
  `n` overflows the stack. Use `malloc`.
- Off-by-one errors: an array of N elements has indexes `0 … N-1`.

## Exercises

```c file=exercise.c
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

/* Reverse a[0..n) in place. */
void reverse(int *a, size_t n) {
    (void)a; (void)n; /* TODO */
}

/* Remove adjacent duplicates from a SORTED array in place.
   Return the new length. */
size_t unique_sorted(int *a, size_t n) {
    (void)a; (void)n;
    return 0; /* TODO */
}

/* Binary search in a sorted array; index of key or -1. */
long binary_search(const int *a, size_t n, int key) {
    (void)a; (void)n; (void)key;
    return -2; /* TODO */
}

/* Rotate left by k positions in place (k may exceed n). */
void rotate_left(int *a, size_t n, size_t k) {
    (void)a; (void)n; (void)k; /* TODO */
}

struct intvec {
    int *data;
    size_t len, cap;
};

/* Append x, growing as needed. Return 0 on success, -1 on failure. */
int intvec_push(struct intvec *v, int x) {
    (void)v; (void)x;
    return -1; /* TODO */
}

/* Remove and return the last element; the vector must not be empty. */
int intvec_pop(struct intvec *v) {
    (void)v;
    return -1; /* TODO */
}

void intvec_free(struct intvec *v) {
    (void)v; /* TODO */
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

static int same(const int *a, const int *b, size_t n) {
    for (size_t i = 0; i < n; i++) {
        if (a[i] != b[i]) {
            return 0;
        }
    }
    return 1;
}

int main(void) {
    int r[] = {1, 2, 3, 4, 5};
    int r_want[] = {5, 4, 3, 2, 1};
    reverse(r, 5);
    CHECK("reverse", same(r, r_want, 5));

    int u[] = {1, 1, 2, 3, 3, 3, 7};
    int u_want[] = {1, 2, 3, 7};
    size_t un = unique_sorted(u, 7);
    CHECK("unique", un == 4 && same(u, u_want, 4));

    int s[] = {1, 3, 5, 7, 9, 11};
    CHECK("bsearch hit", binary_search(s, 6, 7) == 3);
    CHECK("bsearch first", binary_search(s, 6, 1) == 0);
    CHECK("bsearch miss", binary_search(s, 6, 4) == -1);
    CHECK("bsearch empty", binary_search(s, 0, 4) == -1);

    int ro[] = {1, 2, 3, 4, 5};
    int ro_want[] = {3, 4, 5, 1, 2};
    rotate_left(ro, 5, 7);
    CHECK("rotate", same(ro, ro_want, 5));

    struct intvec v = {0};
    int ok = 1;
    for (int i = 0; i < 100; i++) {
        ok = ok && intvec_push(&v, i) == 0;
    }
    CHECK("vec push", ok && v.len == 100 && v.data && v.data[99] == 99);
    CHECK("vec pop", intvec_pop(&v) == 99 && v.len == 99);
    intvec_free(&v);
    CHECK("vec free", v.data == NULL && v.len == 0 && v.cap == 0);
    return failed;
}
```

<details><summary>Solution</summary>

```c file=solution.c
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

void reverse(int *a, size_t n) {
    for (size_t i = 0; i < n / 2; i++) {
        int t = a[i];
        a[i] = a[n - 1 - i];
        a[n - 1 - i] = t;
    }
}

size_t unique_sorted(int *a, size_t n) {
    if (n == 0) {
        return 0;
    }
    size_t w = 1;
    for (size_t r = 1; r < n; r++) {
        if (a[r] != a[w - 1]) {
            a[w++] = a[r];
        }
    }
    return w;
}

long binary_search(const int *a, size_t n, int key) {
    size_t lo = 0, hi = n; /* [lo, hi) */
    while (lo < hi) {
        size_t mid = lo + (hi - lo) / 2;
        if (a[mid] == key) {
            return (long)mid;
        }
        if (a[mid] < key) {
            lo = mid + 1;
        } else {
            hi = mid;
        }
    }
    return -1;
}

static void reverse_range(int *a, size_t n) {
    reverse(a, n);
}

void rotate_left(int *a, size_t n, size_t k) {
    if (n == 0) {
        return;
    }
    k %= n;
    reverse_range(a, k);
    reverse_range(a + k, n - k);
    reverse_range(a, n);
}

struct intvec {
    int *data;
    size_t len, cap;
};

int intvec_push(struct intvec *v, int x) {
    if (v->len == v->cap) {
        size_t ncap = v->cap ? v->cap * 2 : 4;
        int *p = realloc(v->data, ncap * sizeof *p);
        if (!p) {
            return -1;
        }
        v->data = p;
        v->cap = ncap;
    }
    v->data[v->len++] = x;
    return 0;
}

int intvec_pop(struct intvec *v) {
    return v->data[--v->len];
}

void intvec_free(struct intvec *v) {
    free(v->data);
    v->data = NULL;
    v->len = v->cap = 0;
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

static int same(const int *a, const int *b, size_t n) {
    for (size_t i = 0; i < n; i++) {
        if (a[i] != b[i]) {
            return 0;
        }
    }
    return 1;
}

int main(void) {
    int r[] = {1, 2, 3, 4, 5};
    int r_want[] = {5, 4, 3, 2, 1};
    reverse(r, 5);
    CHECK("reverse", same(r, r_want, 5));

    int u[] = {1, 1, 2, 3, 3, 3, 7};
    int u_want[] = {1, 2, 3, 7};
    size_t un = unique_sorted(u, 7);
    CHECK("unique", un == 4 && same(u, u_want, 4));

    int s[] = {1, 3, 5, 7, 9, 11};
    CHECK("bsearch hit", binary_search(s, 6, 7) == 3);
    CHECK("bsearch first", binary_search(s, 6, 1) == 0);
    CHECK("bsearch miss", binary_search(s, 6, 4) == -1);
    CHECK("bsearch empty", binary_search(s, 0, 4) == -1);

    int ro[] = {1, 2, 3, 4, 5};
    int ro_want[] = {3, 4, 5, 1, 2};
    rotate_left(ro, 5, 7);
    CHECK("rotate", same(ro, ro_want, 5));

    struct intvec v = {0};
    int ok = 1;
    for (int i = 0; i < 100; i++) {
        ok = ok && intvec_push(&v, i) == 0;
    }
    CHECK("vec push", ok && v.len == 100 && v.data && v.data[99] == 99);
    CHECK("vec pop", intvec_pop(&v) == 99 && v.len == 99);
    intvec_free(&v);
    CHECK("vec free", v.data == NULL && v.len == 0 && v.cap == 0);
    return failed;
}
```

</details>

Next: [05 — Strings](05-strings.md)
