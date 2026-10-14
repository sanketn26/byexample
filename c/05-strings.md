# C 05 — Strings

A C string is a `char` array ending in a `'\0'` byte. There is no string
type, no length field, and no bounds checking — every string bug is a
memory bug.

## Example

```c file=example.c
#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int format_id(char *out, size_t cap, const char *name, int id) {
    return snprintf(out, cap, "%s-%d", name, id);
}

int main(void) {
    /* An array you own and may modify */
    char buf[16] = "hello";
    printf("%zu %zu\n", sizeof buf, strlen(buf));
    buf[0] = 'J';

    /* A pointer to a literal: read-only, so keep it const */
    const char *lit = "world";
    printf("%s %s\n", buf, lit);

    /* strcmp returns <0, 0, >0 (only the sign is portable) */
    printf("%d %d %d\n", strcmp("a", "b") < 0, strcmp("b", "b") == 0,
           strcmp("c", "b") > 0);

    /* snprintf never overflows and returns the length it WANTED */
    char out[8];
    int need = format_id(out, sizeof out, "abcdef", 12345);
    printf("%d [%s]\n", need, out);

    /* Searching */
    const char *path = "/usr/local/bin";
    printf("%s %s\n", strrchr(path, '/') + 1, strstr(path, "local"));

    /* strtol: the correct way to parse numbers */
    char *end;
    errno = 0;
    long v = strtol("123abc", &end, 10);
    printf("%ld [%s] %d\n", v, end, errno);
    errno = 0;
    strtol("99999999999999999999", NULL, 10);
    printf("%d\n", errno == ERANGE);

    /* Splitting by hand with strchr (strtok mutates and is not reentrant) */
    const char *csv = "a,bb,ccc";
    const char *start = csv;
    for (;;) {
        const char *comma = strchr(start, ',');
        size_t len = comma ? (size_t)(comma - start) : strlen(start);
        printf("%.*s|", (int)len, start);
        if (!comma) {
            break;
        }
        start = comma + 1;
    }
    printf("\n");

    /* ctype functions take unsigned char values */
    char word[] = "mixed Case";
    for (size_t i = 0; word[i] != '\0'; i++) {
        word[i] = (char)toupper((unsigned char)word[i]);
    }
    printf("%s\n", word);

    /* sscanf returns the number of items converted */
    int h, m;
    int n = sscanf("12:34", "%d:%d", &h, &m);
    printf("%d %d %d\n", n, h, m);

    /* memmove handles overlapping ranges, memcpy does not */
    char s[] = "abcdef";
    memmove(s + 2, s, 4);
    printf("%s\n", s);
    return 0;
}
```

```text output
16 5
Jello world
1 1 1
12 [abcdef-]
bin local/bin
123 [abc] 0
1
a|bb|ccc|
MIXED CASE
2 12 34
ababcd
```

## Details that bite

- Always allocate `strlen(s) + 1` bytes: the terminator needs room.
- **Never** use `gets`, `strcpy`, `strcat` or `sprintf` on data you do not
  fully control. Use `snprintf`, or `memcpy` with explicit lengths.
- `strncpy` does not guarantee a terminator and pads with zeros; it is not
  a "safe strcpy". Terminate manually or avoid it.
- Modifying a string literal (`char *p = "x"; p[0] = 'y';`) is undefined
  behaviour. Declare `const char *` for literals.
- `==` on `char *` compares pointers, not contents; use `strcmp`.
- `atoi` cannot report errors. Use `strtol` and check `end` and `errno`.
- `strlen` is O(n): do not call it in a loop condition on long strings.
- `char` may be signed; pass `(unsigned char)c` to `toupper`, `isalpha`,
  and friends.
- Strings are bytes. UTF-8 text works with `strlen` for *byte* length, but
  "number of characters" needs a decoder.

## Exercises

```c file=exercise.c
#include <stddef.h>
#include <stdio.h>
#include <string.h>

/* Length without strlen. */
size_t my_strlen(const char *s) {
    (void)s;
    return 99; /* TODO */
}

/* Reverse in place. */
void str_reverse(char *s) {
    (void)s; /* TODO */
}

/* 1 if s reads the same both ways, ignoring case and non-alphanumerics. */
int is_palindrome(const char *s) {
    (void)s;
    return -1; /* TODO */
}

/* Strict decimal int parser: optional sign then digits, whole string.
   Return 0 and set *out on success; -1 for "", " 5", "12x", or overflow. */
int parse_int(const char *s, int *out) {
    (void)s; (void)out;
    return 0; /* TODO */
}

/* Number of whitespace-separated words. */
size_t count_words(const char *s) {
    (void)s;
    return 99; /* TODO */
}

/* Shift ASCII letters by `shift` (may be negative), keeping case. */
void caesar(char *s, int shift) {
    (void)s; (void)shift; /* TODO */
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
    CHECK("strlen", my_strlen("") == 0 && my_strlen("hello") == 5);
    char r[] = "stressed";
    str_reverse(r);
    CHECK("reverse", strcmp(r, "desserts") == 0);
    char e[] = "";
    str_reverse(e);
    CHECK("reverse empty", strcmp(e, "") == 0);
    CHECK("palindrome", is_palindrome("A man, a plan, a canal: Panama") == 1);
    CHECK("not palindrome", is_palindrome("hello") == 0);
    int v = 0;
    CHECK("parse ok", parse_int("-42", &v) == 0 && v == -42);
    CHECK("parse plus", parse_int("+7", &v) == 0 && v == 7);
    CHECK("parse empty", parse_int("", &v) == -1);
    CHECK("parse space", parse_int(" 5", &v) == -1);
    CHECK("parse junk", parse_int("12x", &v) == -1);
    CHECK("parse overflow", parse_int("99999999999", &v) == -1);
    CHECK("parse int max", parse_int("2147483647", &v) == 0 && v == 2147483647);
    CHECK("words", count_words("  the quick  brown\tfox\n") == 4);
    CHECK("words empty", count_words("   ") == 0);
    char c[] = "Hello, World!";
    caesar(c, 3);
    CHECK("caesar", strcmp(c, "Khoor, Zruog!") == 0);
    caesar(c, -3);
    CHECK("caesar back", strcmp(c, "Hello, World!") == 0);
    return failed;
}
```

<details><summary>Solution</summary>

```c file=solution.c
#include <ctype.h>
#include <errno.h>
#include <limits.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

size_t my_strlen(const char *s) {
    const char *p = s;
    while (*p) {
        p++;
    }
    return (size_t)(p - s);
}

void str_reverse(char *s) {
    size_t n = my_strlen(s);
    for (size_t i = 0; i < n / 2; i++) {
        char t = s[i];
        s[i] = s[n - 1 - i];
        s[n - 1 - i] = t;
    }
}

int is_palindrome(const char *s) {
    size_t i = 0, j = my_strlen(s);
    while (i < j) {
        if (!isalnum((unsigned char)s[i])) {
            i++;
        } else if (!isalnum((unsigned char)s[j - 1])) {
            j--;
        } else {
            if (tolower((unsigned char)s[i]) != tolower((unsigned char)s[j - 1])) {
                return 0;
            }
            i++;
            j--;
        }
    }
    return 1;
}

int parse_int(const char *s, int *out) {
    if (*s == '\0' || isspace((unsigned char)*s)) {
        return -1;
    }
    char *end;
    errno = 0;
    long v = strtol(s, &end, 10);
    if (*end != '\0' || errno == ERANGE || v < INT_MIN || v > INT_MAX) {
        return -1;
    }
    *out = (int)v;
    return 0;
}

size_t count_words(const char *s) {
    size_t n = 0;
    int in_word = 0;
    for (; *s; s++) {
        if (isspace((unsigned char)*s)) {
            in_word = 0;
        } else if (!in_word) {
            in_word = 1;
            n++;
        }
    }
    return n;
}

void caesar(char *s, int shift) {
    shift = ((shift % 26) + 26) % 26;
    for (; *s; s++) {
        if (*s >= 'a' && *s <= 'z') {
            *s = (char)('a' + (*s - 'a' + shift) % 26);
        } else if (*s >= 'A' && *s <= 'Z') {
            *s = (char)('A' + (*s - 'A' + shift) % 26);
        }
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
    CHECK("strlen", my_strlen("") == 0 && my_strlen("hello") == 5);
    char r[] = "stressed";
    str_reverse(r);
    CHECK("reverse", strcmp(r, "desserts") == 0);
    char e[] = "";
    str_reverse(e);
    CHECK("reverse empty", strcmp(e, "") == 0);
    CHECK("palindrome", is_palindrome("A man, a plan, a canal: Panama") == 1);
    CHECK("not palindrome", is_palindrome("hello") == 0);
    int v = 0;
    CHECK("parse ok", parse_int("-42", &v) == 0 && v == -42);
    CHECK("parse plus", parse_int("+7", &v) == 0 && v == 7);
    CHECK("parse empty", parse_int("", &v) == -1);
    CHECK("parse space", parse_int(" 5", &v) == -1);
    CHECK("parse junk", parse_int("12x", &v) == -1);
    CHECK("parse overflow", parse_int("99999999999", &v) == -1);
    CHECK("parse int max", parse_int("2147483647", &v) == 0 && v == 2147483647);
    CHECK("words", count_words("  the quick  brown\tfox\n") == 4);
    CHECK("words empty", count_words("   ") == 0);
    char c[] = "Hello, World!";
    caesar(c, 3);
    CHECK("caesar", strcmp(c, "Khoor, Zruog!") == 0);
    caesar(c, -3);
    CHECK("caesar back", strcmp(c, "Hello, World!") == 0);
    return failed;
}
```

</details>

Next: [06 — Structs](06-structs.md)
