# C 06 — Structs, Unions and Enums

Structs group data; there are no methods. Unions overlap storage, which with
a tag gives you sum types. Enums name integer constants.

## Example

```c file=example.c
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct point {
    double x, y;
};

typedef struct {
    struct point min, max;
} Rect;

static double rect_area(const Rect *r) {
    return (r->max.x - r->min.x) * (r->max.y - r->min.y);
}

/* Pass a pointer to modify; use -> to reach members */
static void scale(struct point *p, double k) {
    p->x *= k;
    p->y *= k;
}

static void print_point(struct point p) { /* passed (copied) by value */
    printf("(%.1f, %.1f)\n", p.x, p.y);
}

/* A tagged union: the enum says which member is valid */
struct value {
    enum { V_INT, V_DOUBLE, V_STR } kind;
    union {
        int i;
        double d;
        const char *s;
    } as;
};

static void print_value(const struct value *v) {
    switch (v->kind) {
    case V_INT:
        printf("int %d\n", v->as.i);
        break;
    case V_DOUBLE:
        printf("double %.1f\n", v->as.d);
        break;
    case V_STR:
        printf("str %s\n", v->as.s);
        break;
    }
}

struct padded {
    char a;
    int b;
    char c;
};

struct reordered {
    int b;
    char a;
    char c;
};

struct perms {
    unsigned read : 1;
    unsigned write : 1;
    unsigned exec : 1;
};

/* Flexible array member: header and data in one allocation */
struct buf {
    size_t len;
    char data[];
};

struct employee {
    const char *name;
    int salary;
};

int main(void) {
    struct point p = {.x = 3, .y = 4}; /* designated initialiser */
    printf("%.1f %.1f\n", p.x, p.y);

    Rect r = {.min = {0, 0}, .max = {4, 3}};
    printf("%.1f\n", rect_area(&r));

    struct point q = p; /* assignment copies every member */
    q.x = 9;
    printf("%.1f %.1f\n", p.x, q.x);

    scale(&p, 2);
    printf("%.1f %.1f\n", p.x, p.y);

    printf("%zu %zu %zu\n", sizeof(struct padded), sizeof(struct reordered),
           offsetof(struct padded, b));

    struct value vals[] = {
        {.kind = V_INT, .as.i = 42},
        {.kind = V_DOUBLE, .as.d = 2.5},
        {.kind = V_STR, .as.s = "hi"},
    };
    for (size_t i = 0; i < sizeof vals / sizeof vals[0]; i++) {
        print_value(&vals[i]);
    }

    struct perms pm = {0};
    pm.write = 1;
    printf("%u %u %u\n", pm.read, pm.write, pm.exec);

    print_point((struct point){1, 2}); /* compound literal */

    struct employee staff[] = {{"a", 10}, {"b", 20}, {"c", 30}};
    int total = 0;
    for (size_t i = 0; i < sizeof staff / sizeof staff[0]; i++) {
        total += staff[i].salary;
    }
    printf("total=%d\n", total);

    struct buf *b = malloc(sizeof *b + 6);
    if (!b) {
        return 1;
    }
    b->len = 5;
    memcpy(b->data, "hello", 6);
    printf("%zu %s\n", b->len, b->data);
    free(b);
    return 0;
}
```

```text output
3.0 4.0
12.0
3.0 9.0
6.0 8.0
12 8 4
int 42
double 2.5
str hi
0 1 0
(1.0, 2.0)
total=60
5 hello
```

## Details that bite

- Members are laid out in order, with **padding** to satisfy alignment.
  Reordering members from largest to smallest alignment shrinks structs
  (compare `sizeof(struct padded)` and `sizeof(struct reordered)`).
- Do not compare structs with `==` (not allowed) or `memcmp` (padding
  bytes are indeterminate). Compare member by member.
- Large structs passed by value are copied; pass `const struct x *` for
  anything non-trivial.
- Reading a union member other than the one last written is only
  well-defined in limited cases; always carry a tag.
- Bit-field layout and signedness are implementation-defined. Do not use
  them for wire formats or hardware registers you must be portable about.
- `typedef struct node Node;` before the definition allows self-referential
  types: `struct node { struct node *next; };`.
- `sizeof` a struct with a flexible array member excludes the array; add
  the space you need when you allocate.
- Designated initialisers zero everything you do not name; `= {0}` is the
  idiom for "all zero".

## Exercises

```c file=exercise.c
#include <math.h>
#include <stddef.h>
#include <stdio.h>

struct vec2 {
    double x, y;
};

struct vec2 vec2_add(struct vec2 a, struct vec2 b) {
    (void)a;
    (void)b;
    return (struct vec2){-1, -1}; /* TODO */
}

double vec2_dot(struct vec2 a, struct vec2 b) {
    (void)a;
    (void)b;
    return -1; /* TODO */
}

double vec2_len(struct vec2 v) {
    (void)v;
    return -1; /* TODO */
}

struct rect {
    struct vec2 min, max;
};

double rect_area(const struct rect *r) {
    (void)r;
    return -1; /* TODO */
}

/* 1 if p lies inside or on the border of r. */
int rect_contains(const struct rect *r, struct vec2 p) {
    (void)r;
    (void)p;
    return -1; /* TODO */
}

/* Fixed-capacity stack of ints. */
struct stack {
    int items[4];
    size_t len;
};

/* 0 on success, -1 if full. */
int stack_push(struct stack *s, int v) {
    (void)s;
    (void)v;
    return 0; /* TODO */
}

/* 0 on success (value in *out), -1 if empty. */
int stack_pop(struct stack *s, int *out) {
    (void)s;
    (void)out;
    return 0; /* TODO */
}

struct shape {
    enum { CIRCLE, RECTANGLE } kind;
    union {
        double radius;
        struct {
            double w, h;
        } rect;
    } u;
};

double shape_area(const struct shape *s) {
    (void)s;
    return -1; /* TODO */
}

struct employee {
    const char *name;
    int salary;
};

/* Pointer to the highest paid employee, NULL if n == 0. */
const struct employee *highest_paid(const struct employee *e, size_t n) {
    (void)e;
    (void)n;
    return (const struct employee *)1; /* TODO */
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

static int near(double a, double b) {
    return fabs(a - b) < 1e-9;
}

int main(void) {
    struct vec2 a = {1, 2}, b = {3, 4};
    struct vec2 s = vec2_add(a, b);
    CHECK("add", near(s.x, 4) && near(s.y, 6));
    CHECK("dot", near(vec2_dot(a, b), 11));
    CHECK("len", near(vec2_len(b), 5));

    struct rect r = {{0, 0}, {4, 3}};
    CHECK("area", near(rect_area(&r), 12));
    CHECK("inside", rect_contains(&r, (struct vec2){4, 3}) == 1);
    CHECK("outside", rect_contains(&r, (struct vec2){5, 1}) == 0);

    struct stack st = {0};
    int ok = 1;
    for (int i = 0; i < 4; i++) {
        ok = ok && stack_push(&st, i * 10) == 0;
    }
    CHECK("push 4", ok);
    CHECK("push full", stack_push(&st, 99) == -1);
    int v = -1;
    CHECK("pop", stack_pop(&st, &v) == 0 && v == 30);
    struct stack empty = {0};
    CHECK("pop empty", stack_pop(&empty, &v) == -1);

    struct shape c = {.kind = CIRCLE, .u.radius = 2};
    struct shape rc = {.kind = RECTANGLE, .u.rect = {3, 5}};
    CHECK("circle", fabs(shape_area(&c) - 12.56636) < 1e-3);
    CHECK("rect", near(shape_area(&rc), 15));

    struct employee staff[] = {{"a", 10}, {"b", 30}, {"c", 20}};
    const struct employee *top = highest_paid(staff, 3);
    CHECK("highest", top == &staff[1]);
    CHECK("highest none", highest_paid(staff, 0) == NULL);
    return failed;
}
```

<details><summary>Solution</summary>

```c file=solution.c
#include <math.h>
#include <stddef.h>
#include <stdio.h>

struct vec2 {
    double x, y;
};

struct vec2 vec2_add(struct vec2 a, struct vec2 b) {
    return (struct vec2){a.x + b.x, a.y + b.y};
}

double vec2_dot(struct vec2 a, struct vec2 b) {
    return a.x * b.x + a.y * b.y;
}

double vec2_len(struct vec2 v) {
    return sqrt(vec2_dot(v, v));
}

struct rect {
    struct vec2 min, max;
};

double rect_area(const struct rect *r) {
    return (r->max.x - r->min.x) * (r->max.y - r->min.y);
}

int rect_contains(const struct rect *r, struct vec2 p) {
    return p.x >= r->min.x && p.x <= r->max.x && p.y >= r->min.y && p.y <= r->max.y;
}

struct stack {
    int items[4];
    size_t len;
};

int stack_push(struct stack *s, int v) {
    if (s->len == sizeof s->items / sizeof s->items[0]) {
        return -1;
    }
    s->items[s->len++] = v;
    return 0;
}

int stack_pop(struct stack *s, int *out) {
    if (s->len == 0) {
        return -1;
    }
    *out = s->items[--s->len];
    return 0;
}

struct shape {
    enum { CIRCLE, RECTANGLE } kind;
    union {
        double radius;
        struct {
            double w, h;
        } rect;
    } u;
};

double shape_area(const struct shape *s) {
    switch (s->kind) {
    case CIRCLE:
        return 3.14159265358979 * s->u.radius * s->u.radius;
    case RECTANGLE:
        return s->u.rect.w * s->u.rect.h;
    }
    return 0;
}

struct employee {
    const char *name;
    int salary;
};

const struct employee *highest_paid(const struct employee *e, size_t n) {
    const struct employee *best = NULL;
    for (size_t i = 0; i < n; i++) {
        if (!best || e[i].salary > best->salary) {
            best = &e[i];
        }
    }
    return best;
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

static int near(double a, double b) {
    return fabs(a - b) < 1e-9;
}

int main(void) {
    struct vec2 a = {1, 2}, b = {3, 4};
    struct vec2 s = vec2_add(a, b);
    CHECK("add", near(s.x, 4) && near(s.y, 6));
    CHECK("dot", near(vec2_dot(a, b), 11));
    CHECK("len", near(vec2_len(b), 5));

    struct rect r = {{0, 0}, {4, 3}};
    CHECK("area", near(rect_area(&r), 12));
    CHECK("inside", rect_contains(&r, (struct vec2){4, 3}) == 1);
    CHECK("outside", rect_contains(&r, (struct vec2){5, 1}) == 0);

    struct stack st = {0};
    int ok = 1;
    for (int i = 0; i < 4; i++) {
        ok = ok && stack_push(&st, i * 10) == 0;
    }
    CHECK("push 4", ok);
    CHECK("push full", stack_push(&st, 99) == -1);
    int v = -1;
    CHECK("pop", stack_pop(&st, &v) == 0 && v == 30);
    struct stack empty = {0};
    CHECK("pop empty", stack_pop(&empty, &v) == -1);

    struct shape c = {.kind = CIRCLE, .u.radius = 2};
    struct shape rc = {.kind = RECTANGLE, .u.rect = {3, 5}};
    CHECK("circle", fabs(shape_area(&c) - 12.56636) < 1e-3);
    CHECK("rect", near(shape_area(&rc), 15));

    struct employee staff[] = {{"a", 10}, {"b", 30}, {"c", 20}};
    const struct employee *top = highest_paid(staff, 3);
    CHECK("highest", top == &staff[1]);
    CHECK("highest none", highest_paid(staff, 0) == NULL);
    return failed;
}
```

</details>

Next: [07 — Errors](07-errors.md)
