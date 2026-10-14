# C 02 — Control Flow

`if`, `for`, `while`, `do…while`, `switch`, and `goto`. Conditions are
integers: zero is false, anything else is true.

## Example

```c file=example.c
#include <stddef.h>
#include <stdio.h>

static int calls;

static int side_effect(void) {
    calls++;
    return 1;
}

int main(void) {
    /* The three loops */
    for (int i = 0; i < 3; i++) {
        printf("%d ", i);
    }
    printf("\n");

    int n = 0;
    while (n < 3) {
        n++;
    }
    printf("%d\n", n);

    do { /* body always runs once */
        n--;
    } while (n > 5);
    printf("%d\n", n);

    /* switch: falls through unless you break */
    int days[] = {6, 1, 2, 9};
    for (size_t i = 0; i < sizeof days / sizeof days[0]; i++) {
        switch (days[i]) {
        case 0:
        case 6:
            puts("weekend");
            break;
        case 1:
            puts("start");
            /* fall through */
        case 2:
            puts("weekday");
            break;
        default:
            puts("?");
        }
    }

    /* goto is the idiomatic way out of nested loops */
    int fi = 0, fj = 0;
    for (int i = 1; i < 5; i++) {
        for (int j = 1; j < 5; j++) {
            if (i * j == 6) {
                fi = i;
                fj = j;
                goto found;
            }
        }
    }
found:
    printf("found %d %d\n", fi, fj);

    /* && and || short-circuit */
    if (0 && side_effect()) {
        puts("never");
    }
    if (1 || side_effect()) {
        /* right side skipped */
    }
    printf("%d\n", calls);

    /* Conditional operator */
    int k = 7;
    printf("%s\n", k % 2 ? "odd" : "even");

    /* Counting down with an unsigned index: i-- > 0 */
    for (size_t i = 3; i-- > 0;) {
        printf("%zu ", i);
    }
    printf("\n");

    /* continue */
    int sum = 0;
    for (int i = 0; i < 10; i++) {
        if (i % 2 == 0) {
            continue;
        }
        sum += i;
    }
    printf("%d\n", sum);

    /* Two loop variables with the comma operator */
    for (int i = 0, j = 5; i < j; i++, j--) {
        printf("%d-%d ", i, j);
    }
    printf("\n");
    return 0;
}
```

```text output
0 1 2 
3
2
weekend
start
weekday
weekday
?
found 2 3
0
odd
2 1 0 
25
0-5 1-4 2-3 
```

## Details that bite

- A `switch` case that falls through into the next one by accident is a
  classic bug. Mark intentional fall-through with a comment (or
  `[[fallthrough]]` in C23); `-Wextra` enforces it.
- `for (size_t i = n - 1; i >= 0; i--)` is an **infinite loop** because
  unsigned is always `>= 0`. Use `for (size_t i = n; i-- > 0;)`.
- `if (x = 0)` assigns; wrap deliberate assignments in extra parentheses.
- A stray semicolon (`if (c);`) makes an empty body. Always use braces,
  even for one statement.
- Declaring variables inside `case` labels needs a block:
  `case 1: { int t = 0; … break; }`.
- `goto` may not jump *into* the scope of a variable-length array, and
  jumping over initialisers leaves variables uninitialised.
- The order of evaluation of function arguments and of `a[i] = i++` is
  unspecified or undefined; do not depend on it.

## Exercises

```c file=exercise.c
#include <stddef.h>
#include <stdio.h>

/* Steps for Collatz to reach 1 (n/2 if even, 3n+1 if odd). -1 if n < 1. */
int collatz_steps(long n) {
    (void)n;
    return -2; /* TODO */
}

/* Greatest common divisor (Euclid), for non-negative inputs. */
int gcd(int a, int b) {
    (void)a;
    (void)b;
    return -1; /* TODO */
}

/* 1 if n is prime else 0. */
int is_prime(int n) {
    (void)n;
    return -1; /* TODO */
}

/* Find the first value that appears a second time.
   Return 1 and store it in *out, or return 0. n is small (O(n^2) is fine). */
int first_repeat(const int *a, size_t n, int *out) {
    (void)a;
    (void)n;
    (void)out;
    return -1; /* TODO */
}

/* Sum of the decimal digits of |n|. */
int digit_sum(long n) {
    (void)n;
    return -1; /* TODO */
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
    CHECK("collatz 1", collatz_steps(1) == 0);
    CHECK("collatz 27", collatz_steps(27) == 111);
    CHECK("collatz 0", collatz_steps(0) == -1);
    CHECK("gcd", gcd(48, 18) == 6);
    CHECK("gcd 0", gcd(0, 7) == 7);
    CHECK("prime 1", is_prime(1) == 0);
    CHECK("prime 2", is_prime(2) == 1);
    CHECK("prime 97", is_prime(97) == 1);
    CHECK("prime 91", is_prime(91) == 0);
    int xs[] = {3, 1, 4, 1, 5, 3};
    int v = 0;
    CHECK("repeat", first_repeat(xs, 6, &v) == 1 && v == 1);
    int ys[] = {1, 2, 3};
    CHECK("no repeat", first_repeat(ys, 3, &v) == 0);
    CHECK("digit_sum", digit_sum(-1234) == 10);
    return failed;
}
```

<details><summary>Solution</summary>

```c file=solution.c
#include <stddef.h>
#include <stdio.h>

int collatz_steps(long n) {
    if (n < 1) {
        return -1;
    }
    int steps = 0;
    while (n != 1) {
        n = (n % 2 == 0) ? n / 2 : 3 * n + 1;
        steps++;
    }
    return steps;
}

int gcd(int a, int b) {
    while (b != 0) {
        int t = a % b;
        a = b;
        b = t;
    }
    return a;
}

int is_prime(int n) {
    if (n < 2) {
        return 0;
    }
    for (int d = 2; (long)d * d <= n; d++) {
        if (n % d == 0) {
            return 0;
        }
    }
    return 1;
}

int first_repeat(const int *a, size_t n, int *out) {
    for (size_t i = 0; i < n; i++) {
        for (size_t j = 0; j < i; j++) {
            if (a[j] == a[i]) {
                *out = a[i];
                return 1;
            }
        }
    }
    return 0;
}

int digit_sum(long n) {
    if (n < 0) {
        n = -n;
    }
    int s = 0;
    for (; n > 0; n /= 10) {
        s += (int)(n % 10);
    }
    return s;
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
    CHECK("collatz 1", collatz_steps(1) == 0);
    CHECK("collatz 27", collatz_steps(27) == 111);
    CHECK("collatz 0", collatz_steps(0) == -1);
    CHECK("gcd", gcd(48, 18) == 6);
    CHECK("gcd 0", gcd(0, 7) == 7);
    CHECK("prime 1", is_prime(1) == 0);
    CHECK("prime 2", is_prime(2) == 1);
    CHECK("prime 97", is_prime(97) == 1);
    CHECK("prime 91", is_prime(91) == 0);
    int xs[] = {3, 1, 4, 1, 5, 3};
    int v = 0;
    CHECK("repeat", first_repeat(xs, 6, &v) == 1 && v == 1);
    int ys[] = {1, 2, 3};
    CHECK("no repeat", first_repeat(ys, 3, &v) == 0);
    CHECK("digit_sum", digit_sum(-1234) == 10);
    return failed;
}
```

</details>

Next: [03 — Functions](03-functions.md)
