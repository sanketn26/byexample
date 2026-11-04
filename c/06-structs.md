# C 06 — Structs, Unions and Enums

Structs group data. There are no methods. Unions overlap storage; a tag
turns that overlap into a sum type. Enums name integer constants.
Designated initializers set the members you name and zero the rest, so
`= {0}` means "all zero".

## Designated initializers name the members

`.x = 3` does not depend on declaration order.

```c file=n01.c
#include <stdio.h>

struct point {
    double x, y;
};

int main(void) {
    struct point p = {.x = 3, .y = 4};
    printf("%.1f %.1f\n", p.x, p.y);
    return 0;
}
```

```text output
3.0 4.0
```

## A pointer argument is how you share a struct

`->` reaches a member through that pointer. Pass `const` when the callee
only reads. A large struct passed by value is copied; use a pointer for
anything non-trivial.

```c file=n02.c
#include <stdio.h>

struct point {
    double x, y;
};

typedef struct {
    struct point min, max;
} Rect;

static double rect_area(const Rect *r) {
    return (r->max.x - r->min.x) * (r->max.y - r->min.y);
}

int main(void) {
    Rect r = {.min = {0, 0}, .max = {4, 3}};
    printf("%.1f\n", rect_area(&r));
    return 0;
}
```

```text output
12.0
```

## Assignment copies every member

`q = p` duplicates the values. Changing `q.x` leaves `p` alone. Structs
cannot be compared with `==`. `memcmp` is also wrong: padding bytes are
indeterminate. Compare the members.

```c file=n03.c
#include <stdio.h>

struct point {
    double x, y;
};

int main(void) {
    struct point p = {.x = 3, .y = 4};
    struct point q = p;
    q.x = 9;
    printf("%.1f %.1f\n", p.x, q.x);
    return 0;
}
```

```text output
3.0 9.0
```

## Write members through the pointer

`scale` changes the caller's object. The copy in the previous nugget
could not.

```c file=n04.c
#include <stdio.h>

struct point {
    double x, y;
};

static void scale(struct point *p, double k) {
    p->x *= k;
    p->y *= k;
}

int main(void) {
    struct point p = {.x = 3, .y = 4};
    scale(&p, 2);
    printf("%.1f %.1f\n", p.x, p.y);
    return 0;
}
```

```text output
6.0 8.0
```

## Padding satisfies alignment

Members are laid out in order, then padded so each one is aligned.
`padded` is 12 bytes here; putting the `int` first shrinks `reordered`
to 8. `offsetof` is the byte offset of a member. Order fields from
largest alignment to smallest when size matters.

```c file=n05.c
#include <stddef.h>
#include <stdio.h>

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

int main(void) {
    printf("%zu %zu %zu\n", sizeof(struct padded), sizeof(struct reordered),
           offsetof(struct padded, b));
    return 0;
}
```

```text output
12 8 4
```

## A tag says which union member is live

Only the member you last wrote is safe to read, except for a few
type-punning cases the standard carves out. Carry an enum and switch on
it. Reading the wrong member is how tagged unions go wrong.

```c file=n06.c
#include <stdio.h>

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

int main(void) {
    struct value vals[] = {
        {.kind = V_INT, .as.i = 42},
        {.kind = V_DOUBLE, .as.d = 2.5},
        {.kind = V_STR, .as.s = "hi"},
    };
    for (int i = 0; i < 3; i++) {
        print_value(&vals[i]);
    }
    return 0;
}
```

```text output
int 42
double 2.5
str hi
```

## Bit-fields pack flags into one word

The widths are in bits. Layout, padding, and whether a bit-field is
signed are implementation-defined. Do not use them for a wire format or
for a hardware register you must lay out portably.

```c file=n07.c
#include <stdio.h>

struct perms {
    unsigned read : 1;
    unsigned write : 1;
    unsigned exec : 1;
};

int main(void) {
    struct perms pm = {0};
    pm.write = 1;
    printf("%u %u %u\n", pm.read, pm.write, pm.exec);
    return 0;
}
```

```text output
0 1 0
```

## A compound literal is an unnamed object

`(struct point){1, 2}` creates a temporary you can pass by value. The
parameter is a copy, so the function cannot change a caller it does not
have.

```c file=n08.c
#include <stdio.h>

struct point {
    double x, y;
};

static void print_point(struct point p) {
    printf("(%.1f, %.1f)\n", p.x, p.y);
}

int main(void) {
    print_point((struct point){1, 2});
    return 0;
}
```

```text output
(1.0, 2.0)
```

## An array of structs is a table

Each element is a full struct. The loop sums one member and ignores the
other.

```c file=n09.c
#include <stdio.h>

struct employee {
    const char *name;
    int salary;
};

int main(void) {
    struct employee staff[] = {{"a", 10}, {"b", 20}, {"c", 30}};
    int total = 0;
    for (int i = 0; i < 3; i++) {
        total += staff[i].salary;
    }
    printf("total=%d\n", total);
    return 0;
}
```

```text output
total=60
```

## A struct may point at its own type

The type name has to exist before the member that uses it. `typedef
struct node Node;` before the body lets you write `Node *next` inside
the definition. The form below names the struct in the same declaration.

```c file=n10.c
#include <stdio.h>

struct node {
    int value;
    struct node *next;
};

int main(void) {
    struct node c = {3, NULL};
    struct node b = {2, &c};
    struct node a = {1, &b};
    printf("%d\n", a.next->next->value);
    return 0;
}
```

```text output
3
```

## A flexible array member shares one allocation

`sizeof(struct buf)` does not include `data`. Add the bytes you need
when you call `malloc`. The header and the bytes are one block, freed
once.

```c file=n11.c
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct buf {
    size_t len;
    char data[];
};

int main(void) {
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
5 hello
```


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
