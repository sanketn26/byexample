# C 02 — Control Flow

`if`, `for`, `while`, `do`/`while`, `switch`, and `goto` all test integers:
zero is false, anything else is true. The order of evaluation of function
arguments, and of expressions like `a[i] = i++`, is unspecified or
undefined. Do not depend on it.

## The three loops

`for` and `while` test before the body. `do`/`while` runs the body once
even when the condition is already false.

```c file=n01.c
#include <stdio.h>

int main(void) {
    for (int i = 0; i < 3; i++) {
        printf("%d ", i);
    }
    printf("\n");

    int n = 0;
    while (n < 3) {
        n++;
    }
    printf("%d\n", n);

    do {
        n--;
    } while (n > 5);
    printf("%d\n", n);
    return 0;
}
```

```text output
0 1 2 
3
2
```

## switch falls through until break

Cases share a body until you `break`. That is how `0` and `6` both mean
weekend, and how `1` prints two lines. An accidental fall-through is a
classic bug. Mark a deliberate one with a comment (`/* fall through */`);
C23 also has `[[fallthrough]]`. GCC's `-Wextra` includes
`-Wimplicit-fallthrough`, which looks for that comment.

```c file=n02.c
#include <stdio.h>

int main(void) {
    int days[] = {6, 1, 2, 9};
    for (int i = 0; i < 4; i++) {
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
    return 0;
}
```

```text output
weekend
start
weekday
weekday
?
```

## A declaration in a case needs a block

A `case` label cannot sit directly above a declaration: control could
jump to the next label and skip the initializer. Wrap the case in braces.

```c file=n03.c
#include <stdio.h>

int main(void) {
    switch (1) {
    case 1: {
        int t = 7;
        printf("%d\n", t);
        break;
    }
    default:
        break;
    }
    return 0;
}
```

```text output
7
```

## goto leaves nested loops

A `goto` to a label after the loops is the usual way out when a `break`
would only leave the inner one. Do not jump *into* the scope of a
variable-length array, and do not jump over an initializer: that variable
would be uninitialized.

```c file=n04.c
#include <stdio.h>

int main(void) {
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
    return 0;
}
```

```text output
found 2 3
```

## && and || skip the right side

`&&` stops when the left side is false. `||` stops when the left side is
true. The call that would increment `calls` never runs.

```c file=n05.c
#include <stdio.h>

static int calls;

static int side_effect(void) {
    calls++;
    return 1;
}

int main(void) {
    if (0 && side_effect()) {
        puts("never");
    }
    if (1 || side_effect()) {
        /* right side skipped */
    }
    printf("%d\n", calls);
    return 0;
}
```

```text output
0
```

## The conditional operator picks one expression

`cond ? a : b` is an expression, not a statement. Only the chosen side is
evaluated.

```c file=n06.c
#include <stdio.h>

int main(void) {
    int k = 7;
    printf("%s\n", k % 2 ? "odd" : "even");
    return 0;
}
```

```text output
odd
```

## Count down with an unsigned index

`for (size_t i = n - 1; i >= 0; i--)` never ends: an unsigned value is
always `>= 0`, and the decrement wraps. Test `i-- > 0` instead. The body
sees 2, then 1, then 0.

```c file=n07.c
#include <stddef.h>
#include <stdio.h>

int main(void) {
    for (size_t i = 3; i-- > 0;) {
        printf("%zu ", i);
    }
    printf("\n");
    return 0;
}
```

```text output
2 1 0 
```

## continue skips the rest of the body

Even indexes are ignored. The sum is the odds from 1 through 9.

```c file=n08.c
#include <stdio.h>

int main(void) {
    int sum = 0;
    for (int i = 0; i < 10; i++) {
        if (i % 2 == 0) {
            continue;
        }
        sum += i;
    }
    printf("%d\n", sum);
    return 0;
}
```

```text output
25
```

## The comma operator sequences two expressions

In a `for` header, the comma runs the left side, then the right, and
yields the right. `i` climbs while `j` falls.

```c file=n09.c
#include <stdio.h>

int main(void) {
    for (int i = 0, j = 5; i < j; i++, j--) {
        printf("%d-%d ", i, j);
    }
    printf("\n");
    return 0;
}
```

```text output
0-5 1-4 2-3 
```

## An assignment in a condition stores

`if (x = 0)` sets `x` to 0 and then tests it, so the branch is false.
Extra parentheses, `if ((x = 0))`, are how you tell the compiler the
assignment is deliberate. Without them, `-Wall` warns.

```c file=n10.c
#include <stdio.h>

int main(void) {
    int x = 1;
    if ((x = 0)) {
        puts("yes");
    } else {
        puts("no");
    }
    printf("%d\n", x);
    return 0;
}
```

```text output
no
0
```

## A stray semicolon is an empty body

`if (c);` ends the `if`. The next statement always runs. `-Wempty-body`
(part of `-Wextra`) flags the semicolon when it sits on the `if` line;
a semicolon on the next line is the same empty body. Use braces even for
a single statement.

```c file=n11.c
#include <stdio.h>

int main(void) {
    int c = 0;
    if (c)
        ;
    puts("ran");
    return 0;
}
```

```text output
ran
```


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
