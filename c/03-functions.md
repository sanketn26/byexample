# C 03 — Functions

Everything is passed **by value**. To let a function modify something, pass
its address. There is no overloading, no default arguments, and no nested
functions.

## Example

```c file=example.c
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>

static int add(int a, int b) {
    return a + b;
}

/* Pointer parameters let a function change the caller's variables */
static void swap(int *a, int *b) {
    int t = *a;
    *a = *b;
    *b = t;
}

/* Out-parameter for a second result */
static int divmod(int a, int b, int *rem) {
    *rem = a % b;
    return a / b;
}

/* An array parameter is really a pointer: pass the length separately */
static int sum_array(const int *a, size_t n) {
    int s = 0;
    for (size_t i = 0; i < n; i++) {
        s += a[i];
    }
    return s;
}

static size_t size_via_pointer(const int *p) {
    return sizeof p;
}

/* static local: keeps its value between calls */
static int counter(void) {
    static int c = 0;
    return ++c;
}

/* Variadic: you must know the count and types yourself */
static int sum_ints(int count, ...) {
    va_list ap;
    va_start(ap, count);
    int s = 0;
    for (int i = 0; i < count; i++) {
        s += va_arg(ap, int);
    }
    va_end(ap);
    return s;
}

/* Small structs can be returned by value */
struct pair {
    int lo, hi;
};

static struct pair min_max(const int *a, size_t n) {
    struct pair p = {a[0], a[0]};
    for (size_t i = 1; i < n; i++) {
        if (a[i] < p.lo) {
            p.lo = a[i];
        }
        if (a[i] > p.hi) {
            p.hi = a[i];
        }
    }
    return p;
}

static unsigned long fact(unsigned n) {
    return n <= 1 ? 1UL : n * fact(n - 1);
}

int main(void) {
    printf("%d\n", add(2, 3));

    int x = 1, y = 2;
    swap(&x, &y);
    printf("%d %d\n", x, y);

    int r;
    int q = divmod(17, 5, &r);
    printf("%d %d\n", q, r);

    int arr[10] = {0};
    printf("%zu %zu\n", sizeof arr, size_via_pointer(arr));

    int data[] = {4, 9, 1, 5};
    printf("%d\n", sum_array(data, sizeof data / sizeof data[0]));
    struct pair mm = min_max(data, 4);
    printf("%d %d\n", mm.lo, mm.hi);

    /* Separate statements: argument evaluation order is unspecified, so
       printf("%d %d %d", counter(), counter(), counter()) could print 3 2 1 */
    int c1 = counter();
    int c2 = counter();
    int c3 = counter();
    printf("%d %d %d\n", c1, c2, c3);
    printf("%d\n", sum_ints(4, 1, 2, 3, 4));
    printf("%lu\n", fact(10));
    return 0;
}
```

```text output
5
2 1
3 2
40 8
19
1 9
1 2 3
10
3628800
```

## Details that bite

- `int f()` in C means "unspecified parameters"; write `int f(void)` for
  no parameters.
- An array argument **decays** into a pointer to its first element, so
  `sizeof` inside the callee gives the pointer size. Always pass a length.
- Modifying a parameter changes only the local copy; modifying `*param`
  changes the caller's object.
- Never return a pointer to a local (automatic) variable: it dies when the
  function returns.
- Mark file-private helpers `static`. Without it they have external
  linkage and can clash with other files.
- Use `const` on pointer parameters you only read from; it documents intent
  and lets the compiler catch mistakes.
- `va_arg` with the wrong type, or reading more arguments than were
  passed, is undefined behaviour. Prefer arrays or structs to variadics in
  your own APIs.
- Recursion depth is limited by the stack; deep recursion crashes with a
  stack overflow rather than a clean error.
- Declare functions before use (prototypes in headers). Implicit
  declarations are an error in C99 and later.

## Exercises

```c file=exercise.c
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>

int max3(int a, int b, int c) {
    (void)a; (void)b; (void)c;
    return 0; /* TODO */
}

/* Exchange the two values. */
void swap_ints(int *a, int *b) {
    (void)a; (void)b; /* TODO */
}

/* Return 1 and fill *lo and *hi; return 0 (leaving them alone) if n == 0. */
int min_max_of(const int *a, size_t n, int *lo, int *hi) {
    (void)a; (void)n; (void)lo; (void)hi;
    return -1; /* TODO */
}

/* Iterative Fibonacci: fib(0)=0, fib(1)=1. */
unsigned long fib(unsigned n) {
    (void)n;
    return 0; /* TODO */
}

/* Returns 1 on the first call, 2 on the second, ... */
int next_id(void) {
    return -1; /* TODO */
}

/* Average of `count` int arguments; 0.0 when count is 0. */
double average(int count, ...) {
    (void)count;
    return -1.0; /* TODO */
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
    CHECK("max3", max3(3, 9, 5) == 9 && max3(-1, -2, -3) == -1);
    int a = 1, b = 2;
    swap_ints(&a, &b);
    CHECK("swap", a == 2 && b == 1);
    int d[] = {4, -2, 9, 0};
    int lo = 100, hi = -100;
    CHECK("min_max", min_max_of(d, 4, &lo, &hi) == 1 && lo == -2 && hi == 9);
    lo = 7;
    CHECK("min_max empty", min_max_of(d, 0, &lo, &hi) == 0 && lo == 7);
    CHECK("fib", fib(0) == 0 && fib(1) == 1 && fib(50) == 12586269025UL);
    int i1 = next_id(), i2 = next_id(), i3 = next_id();
    CHECK("next_id", i1 == 1 && i2 == 2 && i3 == 3);
    CHECK("average", average(4, 1, 2, 3, 4) == 2.5 && average(0) == 0.0);
    return failed;
}
```

<details><summary>Solution</summary>

```c file=solution.c
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>

int max3(int a, int b, int c) {
    int m = a;
    if (b > m) {
        m = b;
    }
    if (c > m) {
        m = c;
    }
    return m;
}

void swap_ints(int *a, int *b) {
    int t = *a;
    *a = *b;
    *b = t;
}

int min_max_of(const int *a, size_t n, int *lo, int *hi) {
    if (n == 0) {
        return 0;
    }
    *lo = *hi = a[0];
    for (size_t i = 1; i < n; i++) {
        if (a[i] < *lo) {
            *lo = a[i];
        }
        if (a[i] > *hi) {
            *hi = a[i];
        }
    }
    return 1;
}

unsigned long fib(unsigned n) {
    unsigned long a = 0, b = 1;
    for (unsigned i = 0; i < n; i++) {
        unsigned long t = a + b;
        a = b;
        b = t;
    }
    return a;
}

int next_id(void) {
    static int id = 0;
    return ++id;
}

double average(int count, ...) {
    if (count == 0) {
        return 0.0;
    }
    va_list ap;
    va_start(ap, count);
    double total = 0;
    for (int i = 0; i < count; i++) {
        total += va_arg(ap, int);
    }
    va_end(ap);
    return total / count;
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
    CHECK("max3", max3(3, 9, 5) == 9 && max3(-1, -2, -3) == -1);
    int a = 1, b = 2;
    swap_ints(&a, &b);
    CHECK("swap", a == 2 && b == 1);
    int d[] = {4, -2, 9, 0};
    int lo = 100, hi = -100;
    CHECK("min_max", min_max_of(d, 4, &lo, &hi) == 1 && lo == -2 && hi == 9);
    lo = 7;
    CHECK("min_max empty", min_max_of(d, 0, &lo, &hi) == 0 && lo == 7);
    CHECK("fib", fib(0) == 0 && fib(1) == 1 && fib(50) == 12586269025UL);
    int i1 = next_id(), i2 = next_id(), i3 = next_id();
    CHECK("next_id", i1 == 1 && i2 == 2 && i3 == 3);
    CHECK("average", average(4, 1, 2, 3, 4) == 2.5 && average(0) == 0.0);
    return failed;
}
```

</details>

Next: [04 — Arrays and collections](04-arrays.md)
