# C 01 — Values, Types and printf

C gives you small, fixed-size machine types and almost no safety net. You
must know exactly what each operation does to the bits. Sizes below are for
LP64 (64-bit Linux and macOS).

A local with no initializer is indeterminate; reading it is undefined, so
initialize at the declaration. `=` assigns and `==` compares: `if (x = 5)`
is an assignment, and `-Wall` warns about it.

## Sizes come from sizeof

`sizeof` is the portable width. `char` is 1 by definition; the other widths
are not. A pointer here is 8 bytes.

```c file=n01.c
#include <stdio.h>

int main(void) {
    printf("%zu %zu %zu %zu %zu\n", sizeof(char), sizeof(short), sizeof(int),
           sizeof(long), sizeof(long long));
    printf("%zu %zu %zu\n", sizeof(float), sizeof(double), sizeof(void *));
    return 0;
}
```

```text output
1 2 4 8 8
4 8 8
```

## Unsigned overflow wraps

Unsigned arithmetic is modulo 2^N, so `uint8_t` 255 plus one is 0. Signed
overflow is undefined: the compiler may assume it never happens. Check
before you add, or use the `__builtin_add_overflow` family.

```c file=n02.c
#include <limits.h>
#include <stdint.h>
#include <stdio.h>

int main(void) {
    int32_t a = INT32_MAX;
    uint8_t u = 255;
    printf("%d %u\n", a, (unsigned)u);
    u++;
    printf("%u\n", (unsigned)u);
    printf("%d %d\n", INT_MIN, INT_MAX);
    return 0;
}
```

```text output
2147483647 255
0
-2147483648 2147483647
```

## Integer division truncates toward zero

`7 / 2` is 3 and `-7 / 2` is `-3`, not floor division. `%` keeps the
dividend's sign, so `-7 % 3` is `-1`. One floating operand makes `/` a
real division.

```c file=n03.c
#include <stdio.h>

int main(void) {
    printf("%d %d %d %f\n", 7 / 2, -7 / 2, -7 % 3, 7 / 2.0);
    return 0;
}
```

```text output
3 -3 -1 3.500000
```

## Casts truncate toward zero

A cast from `double` to `int` drops the fraction. It does not round.
`(int)-3.99` is `-3`.

```c file=n04.c
#include <stdio.h>

int main(void) {
    double d = 3.99;
    printf("%d %d\n", (int)d, (int)-3.99);
    return 0;
}
```

```text output
3 -3
```

## Signed values convert modulo 2^N

`(unsigned)-1` is `UINT_MAX`, not a negative number. A mixed comparison
such as `-1 < 1u` converts the signed side first, so it is false.
`-Wsign-compare` (part of `-Wextra`) warns; the cast below makes the
conversion obvious.

```c file=n05.c
#include <stdio.h>

int main(void) {
    int neg = -1;
    unsigned pos = 1;
    printf("%u %d\n", (unsigned)neg, (unsigned)neg > pos);
    return 0;
}
```

```text output
4294967295 1
```

## char is a small integer

`'A'` is the code 65. Adding one moves to the next code. `char` may be
signed or unsigned, depending on the platform; store bytes in
`unsigned char` or `uint8_t`.

```c file=n06.c
#include <stdio.h>

int main(void) {
    char c = 'A';
    printf("%c %d %c\n", c, c, c + 1);
    return 0;
}
```

```text output
A 65 B
```

## Any non-zero value is true

`bool` is an integer type that stores 0 or 1. The condition `5 > 3` is
true. `!5` is false, because 5 is not zero.

```c file=n07.c
#include <stdbool.h>
#include <stdio.h>

int main(void) {
    bool ok = 5 > 3;
    printf("%d %d\n", ok, !5);
    return 0;
}
```

```text output
1 0
```

## Enums are ints

An enumerator with no value is one past the previous one. `RED` is 0,
`GREEN` is 5, and `BLUE` is 6.

```c file=n08.c
#include <stdio.h>

enum Color { RED, GREEN = 5, BLUE };

int main(void) {
    printf("%d %d %d\n", RED, GREEN, BLUE);
    return 0;
}
```

```text output
0 5 6
```

## Bits are flags

`|=` sets a bit, `&` tests one, and `& ~mask` clears one. Shift a
`1u`, not a signed `1`, so the bit pattern is unsigned.

```c file=n09.c
#include <stdio.h>

int main(void) {
    unsigned flags = 0;
    flags |= 1u << 3;
    flags |= 1u << 0;
    printf("%u %d %u\n", flags, (flags & (1u << 3)) != 0, flags & ~1u);
    return 0;
}
```

```text output
9 1 8
```

## Floats are binary

`0.1 + 0.2` is not `0.3`. A `float` also runs out of integer precision at
2^24: `16777216.0f + 1.0f` is still `16777216.0f`.

```c file=n10.c
#include <stdio.h>

int main(void) {
    printf("%.17g %d\n", 0.1 + 0.2, 0.1 + 0.2 == 0.3);
    float f = 16777216.0f;
    printf("%.1f\n", f + 1.0f);
    return 0;
}
```

```text output
0.30000000000000004 0
16777216.0
```

## Macros substitute text

`SQUARE(x + 1)` works only because every use of the argument, and the
whole expression, is parenthesized. A macro is not a function: each
argument is evaluated every time it appears, so `SQUARE(i++)` modifies
`i` twice and is undefined.

```c file=n11.c
#include <stdio.h>

#define SQUARE(x) ((x) * (x))

int main(void) {
    int x = 3;
    printf("%d\n", SQUARE(x + 1));
    return 0;
}
```

```text output
16
```

## sizeof counts the terminator

A string literal is a `char` array ending in `'\0'`. `sizeof` includes
that byte. `strlen` does not.

```c file=n12.c
#include <stdio.h>
#include <string.h>

int main(void) {
    printf("%zu %zu\n", sizeof "hello", strlen("hello"));
    return 0;
}
```

```text output
6 5
```

## A wide shift needs a wide literal

`1 << 40` is undefined when `1` is an `int`: the shift count is not
smaller than the width. `1LL` is a `long long`, which can hold bit 40.

```c file=n13.c
#include <stdio.h>

int main(void) {
    long long big = 1LL << 40;
    printf("%lld\n", big);
    return 0;
}
```

```text output
1099511627776
```

## printf pads, aligns, and picks a base

The conversion must match the argument type. `%d` is `int`, `%u`
unsigned, `%ld` long, `%lld` long long, `%zu` `size_t`, `%f` double
(a `float` is promoted), and `%p` a pointer cast to `void *`. A mismatch
is undefined. `%x`, `%X`, and `%o` print unsigned values in hex and octal.

```c file=n14.c
#include <stdio.h>

int main(void) {
    printf("%x %X %o\n", 255, 255, 8);
    printf("%5d|%-5d|%05d|%+d\n", 42, 42, 42, 42);
    printf("%8.3f|%e|%g\n", 3.14159, 1234.5678, 0.0001);
    printf("%c%c %s %10s|%-6s|\n", 'o', 'k', "str", "right", "left");
    return 0;
}
```

```text output
ff FF 10
   42|42   |00042|+42
   3.142|1.234568e+03|0.0001
ok str      right|left  |
```


## Exercises

```c file=exercise.c
#include <stdint.h>
#include <stdio.h>

/* 1 if n is a power of two (n > 0), else 0. Use bit tricks, no loops. */
int is_power_of_two(unsigned n) {
    (void)n;
    return -1; /* TODO */
}

/* Number of set bits in n. */
int count_bits(uint32_t n) {
    (void)n;
    return -1; /* TODO */
}

/* Rotate an 8-bit value left by k (0..7) bits. */
uint8_t rotl8(uint8_t v, unsigned k) {
    (void)v;
    (void)k;
    return 0; /* TODO */
}

/* Floor division for b > 0: floor_div(-7, 2) == -4 (C truncates toward 0). */
int floor_div(int a, int b) {
    (void)a;
    (void)b;
    return 0; /* TODO */
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
    CHECK("pow2 64", is_power_of_two(64) == 1);
    CHECK("pow2 0", is_power_of_two(0) == 0);
    CHECK("pow2 12", is_power_of_two(12) == 0);
    CHECK("bits 0xF0F0", count_bits(0xF0F0u) == 8);
    CHECK("bits all", count_bits(0xFFFFFFFFu) == 32);
    CHECK("rotl8", rotl8(0x81, 1) == 0x03);
    CHECK("rotl8 0", rotl8(0x5A, 0) == 0x5A);
    CHECK("floor_div -7/2", floor_div(-7, 2) == -4);
    CHECK("floor_div 7/2", floor_div(7, 2) == 3);
    CHECK("floor_div -6/3", floor_div(-6, 3) == -2);
    return failed;
}
```

<details><summary>Solution</summary>

```c file=solution.c
#include <stdint.h>
#include <stdio.h>

int is_power_of_two(unsigned n) {
    return n != 0 && (n & (n - 1)) == 0;
}

int count_bits(uint32_t n) {
    int c = 0;
    while (n) {
        n &= n - 1; /* clears the lowest set bit */
        c++;
    }
    return c;
}

uint8_t rotl8(uint8_t v, unsigned k) {
    k &= 7;
    if (k == 0) {
        return v;
    }
    return (uint8_t)((v << k) | (v >> (8 - k)));
}

int floor_div(int a, int b) {
    int q = a / b;
    if (a % b < 0) {
        q--;
    }
    return q;
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
    CHECK("pow2 64", is_power_of_two(64) == 1);
    CHECK("pow2 0", is_power_of_two(0) == 0);
    CHECK("pow2 12", is_power_of_two(12) == 0);
    CHECK("bits 0xF0F0", count_bits(0xF0F0u) == 8);
    CHECK("bits all", count_bits(0xFFFFFFFFu) == 32);
    CHECK("rotl8", rotl8(0x81, 1) == 0x03);
    CHECK("rotl8 0", rotl8(0x5A, 0) == 0x5A);
    CHECK("floor_div -7/2", floor_div(-7, 2) == -4);
    CHECK("floor_div 7/2", floor_div(7, 2) == 3);
    CHECK("floor_div -6/3", floor_div(-6, 3) == -2);
    return failed;
}
```

</details>

Next: [02 — Control flow](02-control-flow.md)
