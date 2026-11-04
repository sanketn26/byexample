# C 04 — Arrays and Collections

C has fixed-size arrays and pointers. Anything more — a vector, a map, a
set — you build yourself. There is no bounds check: `a[5]` on a 5-element
array is undefined. It may crash, corrupt memory, or seem to work. Build
with `-fsanitize=address` to catch it. Indexes of an N-element array run
from 0 through N-1.

## The rest of a partial initializer is zero

You name the first elements. The ones you omit are zero. A variable-length
array (`int a[n]`) for an untrusted `n` can overflow the stack; allocate
with `malloc` instead.

```c file=n01.c
#include <stdio.h>

int main(void) {
    int a[5] = {1, 2, 3};
    for (int i = 0; i < 5; i++) {
        printf("%d ", a[i]);
    }
    printf("\n");
    return 0;
}
```

```text output
1 2 3 0 0 
```

## Designated initializers pick slots

`[1] = 10` sets index 1 and leaves the rest zero, including the gap before
the next named index.

```c file=n02.c
#include <stdio.h>

int main(void) {
    int sparse[6] = {[1] = 10, [4] = 40};
    for (int i = 0; i < 6; i++) {
        printf("%d ", sparse[i]);
    }
    printf("\n");
    return 0;
}
```

```text output
0 10 0 0 40 0 
```

## sizeof an array is not sizeof a pointer

`sizeof a / sizeof a[0]` works only where `a` is a real array. A parameter,
or any pointer from `malloc`, has the size of a pointer: 8 here, not 20.
Dividing that by `sizeof(int)` yields 2, not 5. `-Wsizeof-pointer-div`
rejects that division, which is why the function prints `sizeof` of the
pointer instead.

```c file=n03.c
#include <stdio.h>

static size_t len_via_pointer(const int *p) {
    return sizeof p;
}

int main(void) {
    int a[5] = {1, 2, 3};
    printf("%zu\n", sizeof a / sizeof a[0]);
    printf("%zu\n", len_via_pointer(a));
    return 0;
}
```

```text output
5
8
```

## a[i] is *(a + i)

`2[a]` is the same addition, written backwards. Subtracting two pointers
into the same array counts elements, not bytes. A pointer may be one past
the end (`a + 5`) but must not be dereferenced.

```c file=n04.c
#include <stdio.h>

int main(void) {
    int a[5] = {1, 2, 3};
    int *p = a;
    printf("%d %d %d\n", *(p + 2), a[2], 2 [a]);
    printf("%td\n", &a[4] - &a[1]);
    printf("%d\n", (a + 5) == &a[5]);
    return 0;
}
```

```text output
3 3 3
3
1
```

## A two-dimensional array is row-major

`int m[2][3]` is an array of two arrays of three ints, stored as one
block. `sizeof m` is 6 ints, 24 bytes here.

```c file=n05.c
#include <stdio.h>

int main(void) {
    int m[2][3] = {{1, 2, 3}, {4, 5, 6}};
    int total = 0;
    for (int r = 0; r < 2; r++) {
        for (int c = 0; c < 3; c++) {
            total += m[r][c];
        }
    }
    printf("%d %d %zu\n", total, m[1][2], sizeof m);
    return 0;
}
```

```text output
21 6 24
```

## qsort needs a three-way comparator

The function receives `const void *` and returns negative, zero, or
positive. Do not return `a - b`: that subtraction overflows for large
ints. `(a > b) - (a < b)` does not.

```c file=n06.c
#include <stdio.h>
#include <stdlib.h>

static int cmp_int(const void *pa, const void *pb) {
    int a = *(const int *)pa, b = *(const int *)pb;
    return (a > b) - (a < b);
}

int main(void) {
    int nums[] = {5, 2, 9, 1};
    qsort(nums, 4, sizeof nums[0], cmp_int);
    for (int i = 0; i < 4; i++) {
        printf("%d%c", nums[i], i + 1 < 4 ? ' ' : '\n');
    }
    return 0;
}
```

```text output
1 2 5 9
```

## bsearch uses the same order

The array must already be sorted with the comparator you pass.
`hit - nums` is the index.

```c file=n07.c
#include <stdio.h>
#include <stdlib.h>

static int cmp_int(const void *pa, const void *pb) {
    int a = *(const int *)pa, b = *(const int *)pb;
    return (a > b) - (a < b);
}

int main(void) {
    int nums[] = {1, 2, 5, 9};
    int key = 5;
    int *hit = bsearch(&key, nums, 4, sizeof nums[0], cmp_int);
    printf("found at %td\n", hit - nums);
    return 0;
}
```

```text output
found at 2
```

## The same comparator sorts structs

Cast the `void *` back to the element type, then compare the field you
care about. Ages differ, so the order does not depend on `qsort` being
stable (it is not).

```c file=n08.c
#include <stdio.h>
#include <stdlib.h>

struct person {
    const char *name;
    int age;
};

static int cmp_age(const void *pa, const void *pb) {
    const struct person *a = pa, *b = pb;
    return (a->age > b->age) - (a->age < b->age);
}

int main(void) {
    struct person people[] = {{"Cy", 35}, {"Al", 30}, {"Bo", 25}};
    qsort(people, 3, sizeof people[0], cmp_age);
    for (int i = 0; i < 3; i++) {
        printf("%s:%d ", people[i].name, people[i].age);
    }
    printf("\n");
    return 0;
}
```

```text output
Bo:25 Al:30 Cy:35 
```

## Arrays cannot be assigned

There is no `b = a`. `memcpy` copies the bytes; `memset` fills them.
`a == b` compares the addresses of the two arrays, not the contents.
`memcmp` compares bytes, but padding inside a struct is indeterminate, so
do not use it on structs.

```c file=n09.c
#include <stdio.h>
#include <string.h>

int main(void) {
    int a[5] = {1, 2, 3};
    int b[5];
    int c[5] = {1, 2, 3, 0, 0};
    const int *pa = a, *pc = c;
    memcpy(b, a, sizeof b);
    for (int i = 0; i < 5; i++) {
        printf("%d ", b[i]);
    }
    printf("\n");
    printf("%d %d\n", pa == pc, memcmp(a, c, sizeof a) == 0);
    memset(b, 0, sizeof b);
    for (int i = 0; i < 5; i++) {
        printf("%d ", b[i]);
    }
    printf("\n");
    return 0;
}
```

```text output
1 2 3 0 0 
0 1
0 0 0 0 0 
```

## realloc may move the block

On growth, assign the result to a temporary. Failure returns `NULL` and
leaves the old block valid; `p = realloc(p, n)` would leak it. This
vector doubles from 4, so ten pushes end at length 10 and capacity 16.

```c file=n10.c
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

struct intvec {
    int *data;
    size_t len, cap;
};

static int intvec_push(struct intvec *v, int x) {
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

int main(void) {
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
len=10 cap=16 last=9
```


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
