# C 09 — Abstraction: Function Pointers, Callbacks and Vtables

C has no classes or interfaces. Function pointers plus structs are the
callbacks, the polymorphism, and the information hiding that other
languages generate for you.

Function-pointer syntax is hostile. Read it inside out, and give it a
`typedef`: `typedef int (*binop)(int, int);`. The types must match
exactly. Casting to an incompatible signature and calling through it is
undefined. Calling a `NULL` function pointer crashes; check a vtable
when you build the object.

## A function pointer is a value

The array holds `add` and `mul`. Calling through the pointer is an
ordinary call.

```c file=n01.c
#include <stdio.h>

typedef int (*binop)(int, int);

static int add(int a, int b) { return a + b; }
static int mul(int a, int b) { return a * b; }

int main(void) {
    binop ops[] = {add, mul};
    printf("%d %d\n", ops[0](3, 4), ops[1](3, 4));
    return 0;
}
```

```text output
7 12
```

## A callback takes a context pointer

There are no closures. Without a `void *ctx`, the only way to carry
state is a global. The accumulator lives in the caller; the callback
adds into it. `void *` erases the type, so document what it points at
and keep the cast in one place.

```c file=n02.c
#include <stdio.h>

static void for_each(const int *a, int n, void (*fn)(int, void *), void *ctx) {
    for (int i = 0; i < n; i++) {
        fn(a[i], ctx);
    }
}

static void accumulate(int v, void *ctx) {
    *(int *)ctx += v;
}

int main(void) {
    int data[] = {1, 2, 3, 4};
    int total = 0;
    for_each(data, 4, accumulate, &total);
    printf("%d\n", total);
    return 0;
}
```

```text output
10
```

## The first member is the base

A `struct circle *` may be cast to `struct shape *` because `base` is
the first member and the object really is a `struct circle`. The ops
table is the vtable: one `area` function and a name, shared by every
circle.

```c file=n03.c
#include <stdio.h>

struct shape;

struct shape_ops {
    double (*area)(const struct shape *);
    const char *name;
};

struct shape {
    const struct shape_ops *ops;
};

struct circle {
    struct shape base;
    double r;
};

struct square {
    struct shape base;
    double side;
};

static double circle_area(const struct shape *s) {
    const struct circle *c = (const struct circle *)s;
    return 3.14159265 * c->r * c->r;
}

static double square_area(const struct shape *s) {
    const struct square *q = (const struct square *)s;
    return q->side * q->side;
}

static const struct shape_ops circle_ops = {circle_area, "circle"};
static const struct shape_ops square_ops = {square_area, "square"};

static void describe(const struct shape *s) {
    printf("%s %.2f\n", s->ops->name, s->ops->area(s));
}

int main(void) {
    struct circle c = {{&circle_ops}, 1.0};
    struct square q = {{&square_ops}, 2.0};
    const struct shape *shapes[] = {&c.base, &q.base};
    describe(shapes[0]);
    describe(shapes[1]);
    return 0;
}
```

```text output
circle 3.14
square 4.00
```

## An opaque type hides the fields

Callers need only the functions. In a real split, the struct body lives
in the `.c` file and the header says `struct counter;`. That is C's
encapsulation. The cost is a heap allocation, or accessor calls, instead
of reading the fields directly.

```c file=n04.c
#include <stdio.h>
#include <stdlib.h>

struct counter {
    int n;
};

static struct counter *counter_new(void) {
    return calloc(1, sizeof(struct counter));
}

static void counter_inc(struct counter *c) { c->n++; }

static int counter_get(const struct counter *c) { return c->n; }

static void counter_free(struct counter *c) { free(c); }

int main(void) {
    struct counter *ctr = counter_new();
    if (!ctr) {
        return 1;
    }
    counter_inc(ctr);
    counter_inc(ctr);
    counter_inc(ctr);
    printf("%d\n", counter_get(ctr));
    counter_free(ctr);
    return 0;
}
```

```text output
3
```

## _Generic selects on the static type

The association is chosen at compile time. It does not look at the
value. A character constant such as `'c'` has type `int` in C, so the
last item matches `int`, not a character type.

```c file=n05.c
#include <stdio.h>

#define TYPE_NAME(x) \
    _Generic((x), int: "int", double: "double", char *: "char*", default: "other")

int main(void) {
    printf("%s %s %s %s\n", TYPE_NAME(1), TYPE_NAME(1.5), TYPE_NAME("s"),
           TYPE_NAME('c'));
    return 0;
}
```

```text output
int double char* int
```

## A size plus void * is a generic stack

The container stores bytes. The caller passes the element size and is
responsible for the real type. Pop copies the bytes back out.

```c file=n06.c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct gstack {
    unsigned char *data;
    size_t elem, len, cap;
};

static int gstack_push(struct gstack *s, const void *item) {
    if (s->len == s->cap) {
        size_t ncap = s->cap ? s->cap * 2 : 4;
        unsigned char *p = realloc(s->data, ncap * s->elem);
        if (!p) {
            return -1;
        }
        s->data = p;
        s->cap = ncap;
    }
    memcpy(s->data + s->len * s->elem, item, s->elem);
    s->len++;
    return 0;
}

static void gstack_pop(struct gstack *s, void *out) {
    s->len--;
    memcpy(out, s->data + s->len * s->elem, s->elem);
}

int main(void) {
    struct gstack st = {.elem = sizeof(double)};
    double vals[] = {1.5, 2.5, 3.5};
    for (int i = 0; i < 3; i++) {
        if (gstack_push(&st, &vals[i]) != 0) {
            return 1;
        }
    }
    double a, b;
    gstack_pop(&st, &a);
    gstack_pop(&st, &b);
    printf("%.1f %.1f\n", a, b);
    free(st.data);
    return 0;
}
```

```text output
3.5 2.5
```


## Exercises

```c file=exercise.c
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Apply f to x, n times: apply_n(double_it, 3, 4) == 48. */
int apply_n(int (*f)(int), int x, int n) {
    (void)f; (void)n;
    return x - 1; /* TODO */
}

/* Count elements for which pred returns non-zero. */
size_t count_if(const int *a, size_t n, int (*pred)(int)) {
    (void)a; (void)n; (void)pred;
    return 99; /* TODO */
}

/* Replace each element by f(element). */
void map_inplace(int *a, size_t n, int (*f)(int)) {
    (void)a; (void)n; (void)f; /* TODO */
}

/* qsort comparator: strings in DESCENDING order. Elements are char *. */
int cmp_str_desc(const void *a, const void *b) {
    (void)a; (void)b;
    return 0; /* TODO */
}

struct animal;
struct animal_ops {
    const char *(*speak)(const struct animal *);
    int legs;
};
struct animal {
    const struct animal_ops *ops;
    const char *name;
};

/* Implement ops tables `dog_ops` (speaks "Woof", 4 legs) and `cat_ops`
   ("Meow", 4 legs) and `bird_ops` ("Tweet", 2 legs). */
static const char *dog_speak(const struct animal *a) { (void)a; return ""; }
static const char *cat_speak(const struct animal *a) { (void)a; return ""; }
static const char *bird_speak(const struct animal *a) { (void)a; return ""; }
static const struct animal_ops dog_ops = {dog_speak, 0};
static const struct animal_ops cat_ops = {cat_speak, 0};
static const struct animal_ops bird_ops = {bird_speak, 0};

/* Sum the legs of the first n animals via their ops. */
int total_legs(const struct animal *const *zoo, size_t n) {
    (void)zoo; (void)n;
    return -1; /* TODO */
}

/* Tiny event emitter: up to 4 handlers, each with a context pointer. */
typedef void (*handler)(int event, void *ctx);
struct emitter {
    handler fns[4];
    void *ctxs[4];
    size_t n;
};

/* 0 on success, -1 if full. */
int emitter_on(struct emitter *e, handler fn, void *ctx) {
    (void)e; (void)fn; (void)ctx;
    return 0; /* TODO */
}

/* Call every handler, in registration order. */
void emitter_emit(const struct emitter *e, int event) {
    (void)e; (void)event; /* TODO */
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

static int twice(int x) { return x * 2; }
static int is_even(int x) { return x % 2 == 0; }
static void add_to(int event, void *ctx) { *(int *)ctx += event; }
static void times_to(int event, void *ctx) { *(int *)ctx *= event; }

int main(void) {
    CHECK("apply_n", apply_n(twice, 3, 4) == 48 && apply_n(twice, 3, 0) == 3);
    int nums[] = {1, 2, 3, 4, 6};
    CHECK("count_if", count_if(nums, 5, is_even) == 3);
    map_inplace(nums, 5, twice);
    CHECK("map", nums[0] == 2 && nums[4] == 12);

    const char *words[] = {"pear", "apple", "zebra", "mango"};
    qsort(words, 4, sizeof words[0], cmp_str_desc);
    CHECK("sort desc", strcmp(words[0], "zebra") == 0 && strcmp(words[3], "apple") == 0);

    struct animal d = {&dog_ops, "rex"}, c = {&cat_ops, "tom"}, b = {&bird_ops, "tweety"};
    CHECK("speak", strcmp(d.ops->speak(&d), "Woof") == 0
                       && strcmp(c.ops->speak(&c), "Meow") == 0
                       && strcmp(b.ops->speak(&b), "Tweet") == 0);
    const struct animal *zoo[] = {&d, &c, &b};
    CHECK("legs", total_legs(zoo, 3) == 10);

    struct emitter e = {0};
    int acc = 1;
    int ok = emitter_on(&e, add_to, &acc) == 0 && emitter_on(&e, times_to, &acc) == 0;
    emitter_emit(&e, 3); /* (1 + 3) * 3 */
    CHECK("emitter", ok && acc == 12);
    for (int i = 0; i < 4; i++) {
        emitter_on(&e, add_to, &acc);
    }
    CHECK("emitter full", emitter_on(&e, add_to, &acc) == -1);
    return failed;
}
```

<details><summary>Solution</summary>

```c file=solution.c
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int apply_n(int (*f)(int), int x, int n) {
    for (int i = 0; i < n; i++) {
        x = f(x);
    }
    return x;
}

size_t count_if(const int *a, size_t n, int (*pred)(int)) {
    size_t c = 0;
    for (size_t i = 0; i < n; i++) {
        if (pred(a[i])) {
            c++;
        }
    }
    return c;
}

void map_inplace(int *a, size_t n, int (*f)(int)) {
    for (size_t i = 0; i < n; i++) {
        a[i] = f(a[i]);
    }
}

int cmp_str_desc(const void *a, const void *b) {
    const char *const *sa = a;
    const char *const *sb = b;
    return strcmp(*sb, *sa);
}

struct animal;
struct animal_ops {
    const char *(*speak)(const struct animal *);
    int legs;
};
struct animal {
    const struct animal_ops *ops;
    const char *name;
};

static const char *dog_speak(const struct animal *a) { (void)a; return "Woof"; }
static const char *cat_speak(const struct animal *a) { (void)a; return "Meow"; }
static const char *bird_speak(const struct animal *a) { (void)a; return "Tweet"; }
static const struct animal_ops dog_ops = {dog_speak, 4};
static const struct animal_ops cat_ops = {cat_speak, 4};
static const struct animal_ops bird_ops = {bird_speak, 2};

int total_legs(const struct animal *const *zoo, size_t n) {
    int t = 0;
    for (size_t i = 0; i < n; i++) {
        t += zoo[i]->ops->legs;
    }
    return t;
}

typedef void (*handler)(int event, void *ctx);
struct emitter {
    handler fns[4];
    void *ctxs[4];
    size_t n;
};

int emitter_on(struct emitter *e, handler fn, void *ctx) {
    if (e->n == 4) {
        return -1;
    }
    e->fns[e->n] = fn;
    e->ctxs[e->n] = ctx;
    e->n++;
    return 0;
}

void emitter_emit(const struct emitter *e, int event) {
    for (size_t i = 0; i < e->n; i++) {
        e->fns[i](event, e->ctxs[i]);
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

static int twice(int x) { return x * 2; }
static int is_even(int x) { return x % 2 == 0; }
static void add_to(int event, void *ctx) { *(int *)ctx += event; }
static void times_to(int event, void *ctx) { *(int *)ctx *= event; }

int main(void) {
    CHECK("apply_n", apply_n(twice, 3, 4) == 48 && apply_n(twice, 3, 0) == 3);
    int nums[] = {1, 2, 3, 4, 6};
    CHECK("count_if", count_if(nums, 5, is_even) == 3);
    map_inplace(nums, 5, twice);
    CHECK("map", nums[0] == 2 && nums[4] == 12);

    const char *words[] = {"pear", "apple", "zebra", "mango"};
    qsort(words, 4, sizeof words[0], cmp_str_desc);
    CHECK("sort desc", strcmp(words[0], "zebra") == 0 && strcmp(words[3], "apple") == 0);

    struct animal d = {&dog_ops, "rex"}, c = {&cat_ops, "tom"}, b = {&bird_ops, "tweety"};
    CHECK("speak", strcmp(d.ops->speak(&d), "Woof") == 0
                       && strcmp(c.ops->speak(&c), "Meow") == 0
                       && strcmp(b.ops->speak(&b), "Tweet") == 0);
    const struct animal *zoo[] = {&d, &c, &b};
    CHECK("legs", total_legs(zoo, 3) == 10);

    struct emitter e = {0};
    int acc = 1;
    int ok = emitter_on(&e, add_to, &acc) == 0 && emitter_on(&e, times_to, &acc) == 0;
    emitter_emit(&e, 3); /* (1 + 3) * 3 */
    CHECK("emitter", ok && acc == 12);
    for (int i = 0; i < 4; i++) {
        emitter_on(&e, add_to, &acc);
    }
    CHECK("emitter full", emitter_on(&e, add_to, &acc) == -1);
    return failed;
}
```

</details>

Next: [10 — Files and I/O](10-files-io.md)
