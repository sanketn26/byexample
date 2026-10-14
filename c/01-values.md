# C 01 — Values, Types and printf

C gives you small, fixed-size machine types and almost no safety net. You
must know exactly what each operation does to the bits.

All examples build with
`gcc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined`
(this is what `tools/verify.py` uses). Sizes shown are for 64-bit
Linux/macOS (LP64).

## Example

```c file=example.c
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum Color { RED, GREEN = 5, BLUE }; /* BLUE is 6 */

#define SQUARE(x) ((x) * (x))

int main(void) {
    /* Sizes are platform dependent: always use sizeof */
    printf("%zu %zu %zu %zu %zu\n", sizeof(char), sizeof(short), sizeof(int),
           sizeof(long), sizeof(long long));
    printf("%zu %zu %zu\n", sizeof(float), sizeof(double), sizeof(void *));

    /* Fixed-width types from <stdint.h> */
    int32_t a = INT32_MAX;
    uint8_t u = 255;
    printf("%d %u\n", a, (unsigned)u);
    u++; /* unsigned overflow wraps: well defined */
    printf("%u\n", (unsigned)u);
    printf("%d %d\n", INT_MIN, INT_MAX);

    /* Integer division truncates toward zero; % keeps the dividend's sign */
    printf("%d %d %d %f\n", 7 / 2, -7 / 2, -7 % 3, 7 / 2.0);

    /* Casts truncate; they do not round */
    double d = 3.99;
    printf("%d %d\n", (int)d, (int)-3.99);

    /* Signed -> unsigned conversion reinterprets modulo 2^N */
    int neg = -1;
    unsigned pos = 1;
    printf("%u %d\n", (unsigned)neg, (unsigned)neg > pos);

    /* char is a small integer */
    char c = 'A';
    printf("%c %d %c\n", c, c, c + 1);

    /* bool, and anything non-zero is true */
    bool ok = 5 > 3;
    printf("%d %d\n", ok, !5);

    /* enums are ints */
    printf("%d %d %d\n", RED, GREEN, BLUE);

    /* Bit manipulation */
    unsigned flags = 0;
    flags |= 1u << 3;
    flags |= 1u << 0;
    printf("%u %d %u\n", flags, (flags & (1u << 3)) != 0, flags & ~1u);
    printf("%x %X %o\n", 255, 255, 8);

    /* Floating point is binary */
    printf("%.17g %d\n", 0.1 + 0.2, 0.1 + 0.2 == 0.3);
    float f = 16777216.0f; /* 2^24: float runs out of integer precision */
    printf("%.1f\n", f + 1.0f);

    /* Macros substitute text; parenthesise everything */
    int x = 3;
    printf("%d\n", SQUARE(x + 1));

    /* sizeof counts the terminating '\0' of a string literal */
    printf("%zu %zu\n", sizeof "hello", strlen("hello"));

    long long big = 1LL << 40;
    printf("%lld\n", big);

    /* printf formatting */
    printf("%5d|%-5d|%05d|%+d\n", 42, 42, 42, 42);
    printf("%8.3f|%e|%g\n", 3.14159, 1234.5678, 0.0001);
    printf("%c%c %s %10s|%-6s|\n", 'o', 'k', "str", "right", "left");
    return 0;
}
```

```text output
1 2 4 8 8
4 8 8
2147483647 255
0
-2147483648 2147483647
3 -3 -1 3.500000
3 -3
4294967295 1
A 65 B
1 0
0 5 6
9 1 8
ff FF 10
0.30000000000000004 0
16777216.0
16
6 5
1099511627776
   42|42   |00042|+42
   3.142|1.234568e+03|0.0001
ok str      right|left  |
```

## Details that bite

- **Signed overflow is undefined behaviour**, not wraparound. The compiler
  may assume it never happens. Unsigned overflow *is* defined (modulo 2^N).
  Check before you add, or use the `__builtin_add_overflow` family.
- `char` may be signed or unsigned depending on the platform; use
  `unsigned char` / `uint8_t` for bytes.
- Mixed signed/unsigned comparisons convert the signed side to unsigned:
  `-1 < 1u` is **false**. `-Wextra` warns (`-Wsign-compare`).
- Local variables are **uninitialised**; reading them is undefined.
  Initialise at declaration.
- A `printf` conversion that does not match the argument type is undefined
  behaviour. `%d` int, `%u` unsigned, `%ld` long, `%lld` long long,
  `%zu` size_t, `%f` double, `%p` pointer (cast to `void *`).
- `=` assigns, `==` compares; `if (x = 5)` compiles. `-Wall` catches it.
- Macros are not functions: arguments are evaluated each time they appear
  (`SQUARE(i++)` is a bug).

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
