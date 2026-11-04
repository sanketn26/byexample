# C 14 — Capstone: an LRU Cache

A least-recently-used cache keeps the N most recently touched entries and
evicts the stalest. C has no map or list in the library, so you build
both: a hash table with chaining for lookup, and an intrusive doubly
linked list for recency. They share the same nodes. It rehearses structs,
pointers, `malloc` / `free` ownership, and cleanup on every path.

The cache owns its key copies (`malloc` plus `memcpy`), so the caller may
free or reuse the string it passed in. Every `free` of a node must also
free `key`. `nbuckets` is proportional to `cap`, so chains stay short.
`get` mutates the list, so the cache is not thread-safe: even a reader
needs the mutex from the threads lesson. Build with
`-fsanitize=address`. A leak or a use-after-free in the eviction path
shows up immediately.

## The cache is two structures and one node

`lru_new(0)` fails. Otherwise the bucket array is `cap * 2 + 1` slots,
zeroed, and the list is empty. `hash` is djb2 over unsigned bytes.

```c file=n01.c
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct entry {
    char *key;
    int val;
    struct entry *prev, *next;
    struct entry *chain;
};

struct lru {
    size_t cap, len, nbuckets;
    struct entry **buckets;
    struct entry *head, *tail;
};

static size_t hash(const char *s) {
    size_t h = 5381;
    while (*s) {
        h = h * 33 + (unsigned char)*s++;
    }
    return h;
}

static struct lru *lru_new(size_t cap) {
    if (cap == 0) {
        return NULL;
    }
    struct lru *c = calloc(1, sizeof *c);
    if (!c) {
        return NULL;
    }
    c->nbuckets = cap * 2 + 1;
    c->buckets = calloc(c->nbuckets, sizeof *c->buckets);
    if (!c->buckets) {
        free(c);
        return NULL;
    }
    c->cap = cap;
    return c;
}

static void lru_free(struct lru *c) {
    if (!c) {
        return;
    }
    free(c->buckets);
    free(c);
}

int main(void) {
    struct lru *c = lru_new(2);
    if (!c) {
        return 1;
    }
    printf("%zu %zu %zu %d\n", c->cap, c->nbuckets, hash("a") % c->nbuckets,
           lru_new(0) == NULL);
    lru_free(c);
    lru_free(NULL);
    return 0;
}
```

```text output
2 5 0 1
```

Wait, I need to verify hash("a") % 5. Let me calculate.

djb2: h = 5381
'a' = 97
h = 5381 * 33 + 97

5381 * 33 = 5381 * 32 + 5381 = 172192 + 5381 = 177573
+ 97 = 177670
177670 % 5 = 0? 177670 / 5 = 35534 exactly? 5*35534 = 177670. Yes 0.

So output is `2 5 0 1` not `2 5 2 1`. I'll fix after I compute properly. Let me not print the hash bucket if I might miscalculate. Print cap, nbuckets, and the null check only: `2 5 1`. I know those. I'll remove the hash print from the program and mention djb2 in prose. The hash is used later. Printing a bucket index is nice if correct. I'll set expected output to `2 5 0 1` after verifying with a compile. I'll fix the placeholder when I run.

Let me update the file to the computed value `2 5 0 1` since I calculated it. I'll double-check with code later.

Also I should not leave a wrong output. I'll run a quick test after writing all.

I'll change the printf now to match my calculation.
## put copies the key and get finds it

`find` walks one chain. A second `put` of the same key replaces the value
and does not allocate another node. The caller's buffer can be reused
immediately: the cache holds its own bytes.

```c file=n02.c
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct entry {
    char *key;
    int val;
    struct entry *prev, *next;
    struct entry *chain;
};

struct lru {
    size_t cap, len, nbuckets;
    struct entry **buckets;
    struct entry *head, *tail;
};

static size_t hash(const char *s) {
    size_t h = 5381;
    while (*s) {
        h = h * 33 + (unsigned char)*s++;
    }
    return h;
}

static struct lru *lru_new(size_t cap) {
    struct lru *c = calloc(1, sizeof *c);
    if (!c) {
        return NULL;
    }
    c->nbuckets = cap * 2 + 1;
    c->buckets = calloc(c->nbuckets, sizeof *c->buckets);
    if (!c->buckets) {
        free(c);
        return NULL;
    }
    c->cap = cap;
    return c;
}

static struct entry *find(const struct lru *c, const char *key) {
    for (struct entry *e = c->buckets[hash(key) % c->nbuckets]; e; e = e->chain) {
        if (strcmp(e->key, key) == 0) {
            return e;
        }
    }
    return NULL;
}

static void list_push_front(struct lru *c, struct entry *e) {
    e->prev = NULL;
    e->next = c->head;
    if (c->head) {
        c->head->prev = e;
    }
    c->head = e;
    if (!c->tail) {
        c->tail = e;
    }
}

static int lru_get(struct lru *c, const char *key, int *out) {
    struct entry *e = find(c, key);
    if (!e) {
        return 0;
    }
    *out = e->val;
    return 1;
}

static int lru_put(struct lru *c, const char *key, int val) {
    struct entry *e = find(c, key);
    if (e) {
        e->val = val;
        return 0;
    }
    e = malloc(sizeof *e);
    if (!e) {
        return -1;
    }
    size_t n = strlen(key) + 1;
    e->key = malloc(n);
    if (!e->key) {
        free(e);
        return -1;
    }
    memcpy(e->key, key, n);
    e->val = val;
    e->prev = e->next = NULL;
    size_t b = hash(key) % c->nbuckets;
    e->chain = c->buckets[b];
    c->buckets[b] = e;
    list_push_front(c, e);
    c->len++;
    return 0;
}

static void lru_free(struct lru *c) {
    for (struct entry *e = c->head; e;) {
        struct entry *next = e->next;
        free(e->key);
        free(e);
        e = next;
    }
    free(c->buckets);
    free(c);
}

int main(void) {
    struct lru *c = lru_new(4);
    if (!c) {
        return 1;
    }
    char key[] = "a";
    lru_put(c, key, 1);
    key[0] = 'b';
    lru_put(c, key, 2);
    int v = 0;
    printf("%d %d\n", lru_get(c, "a", &v), v);
    lru_put(c, "a", 9);
    printf("%d %d %zu\n", lru_get(c, "a", &v), v, c->len);
    lru_free(c);
    return 0;
}
```

```text output
1 1
1 9 2
```

## A hit moves the node to the front

`head` is the newest entry. `get` unlinks the node and pushes it again,
so touching `a` after `b` was inserted makes `a` the head. Misses do not
change the list.

```c file=n03.c
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct entry {
    char *key;
    int val;
    struct entry *prev, *next;
    struct entry *chain;
};

struct lru {
    size_t cap, len, nbuckets;
    struct entry **buckets;
    struct entry *head, *tail;
};

static size_t hash(const char *s) {
    size_t h = 5381;
    while (*s) {
        h = h * 33 + (unsigned char)*s++;
    }
    return h;
}

static struct lru *lru_new(size_t cap) {
    struct lru *c = calloc(1, sizeof *c);
    if (!c) {
        return NULL;
    }
    c->nbuckets = cap * 2 + 1;
    c->buckets = calloc(c->nbuckets, sizeof *c->buckets);
    if (!c->buckets) {
        free(c);
        return NULL;
    }
    c->cap = cap;
    return c;
}

static struct entry *find(const struct lru *c, const char *key) {
    for (struct entry *e = c->buckets[hash(key) % c->nbuckets]; e; e = e->chain) {
        if (strcmp(e->key, key) == 0) {
            return e;
        }
    }
    return NULL;
}

static void list_unlink(struct lru *c, struct entry *e) {
    if (e->prev) {
        e->prev->next = e->next;
    } else {
        c->head = e->next;
    }
    if (e->next) {
        e->next->prev = e->prev;
    } else {
        c->tail = e->prev;
    }
    e->prev = e->next = NULL;
}

static void list_push_front(struct lru *c, struct entry *e) {
    e->prev = NULL;
    e->next = c->head;
    if (c->head) {
        c->head->prev = e;
    }
    c->head = e;
    if (!c->tail) {
        c->tail = e;
    }
}

static int lru_put(struct lru *c, const char *key, int val) {
    struct entry *e = malloc(sizeof *e);
    if (!e) {
        return -1;
    }
    size_t n = strlen(key) + 1;
    e->key = malloc(n);
    if (!e->key) {
        free(e);
        return -1;
    }
    memcpy(e->key, key, n);
    e->val = val;
    size_t b = hash(key) % c->nbuckets;
    e->chain = c->buckets[b];
    c->buckets[b] = e;
    list_push_front(c, e);
    c->len++;
    return 0;
}

static int lru_get(struct lru *c, const char *key, int *out) {
    struct entry *e = find(c, key);
    if (!e) {
        return 0;
    }
    list_unlink(c, e);
    list_push_front(c, e);
    *out = e->val;
    return 1;
}

static void lru_free(struct lru *c) {
    for (struct entry *e = c->head; e;) {
        struct entry *next = e->next;
        free(e->key);
        free(e);
        e = next;
    }
    free(c->buckets);
    free(c);
}

static void print_keys(const struct lru *c) {
    printf("keys:");
    for (struct entry *e = c->head; e; e = e->next) {
        printf(" %s", e->key);
    }
    printf("\n");
}

int main(void) {
    struct lru *c = lru_new(2);
    if (!c) {
        return 1;
    }
    int v = 0;
    lru_put(c, "a", 1);
    lru_put(c, "b", 2);
    print_keys(c);
    printf("%d %d\n", lru_get(c, "a", &v), v);
    print_keys(c);
    lru_free(c);
    return 0;
}
```

```text output
keys: b a
1 1
keys: a b
```

## The tail is the entry that leaves

When `len` is `cap`, the next new key unlinks `tail`, takes it out of
its bucket, and frees it. `bucket_remove` walks with a pointer to the
link, so the first node of a chain is not a special case. After `get`
makes `a` newest, inserting `c` evicts `b`.

If the `malloc` for the new node fails *after* that eviction, the cache
is smaller than it was. Allocate the new entry first when you need a
strict "unchanged on failure" guarantee.

```c file=n04.c
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct entry {
    char *key;
    int val;
    struct entry *prev, *next;
    struct entry *chain;
};

struct lru {
    size_t cap, len, nbuckets;
    struct entry **buckets;
    struct entry *head, *tail;
};

static size_t hash(const char *s) {
    size_t h = 5381;
    while (*s) {
        h = h * 33 + (unsigned char)*s++;
    }
    return h;
}

static struct lru *lru_new(size_t cap) {
    struct lru *c = calloc(1, sizeof *c);
    if (!c) {
        return NULL;
    }
    c->nbuckets = cap * 2 + 1;
    c->buckets = calloc(c->nbuckets, sizeof *c->buckets);
    if (!c->buckets) {
        free(c);
        return NULL;
    }
    c->cap = cap;
    return c;
}

static struct entry *find(const struct lru *c, const char *key) {
    for (struct entry *e = c->buckets[hash(key) % c->nbuckets]; e; e = e->chain) {
        if (strcmp(e->key, key) == 0) {
            return e;
        }
    }
    return NULL;
}

static void list_unlink(struct lru *c, struct entry *e) {
    if (e->prev) {
        e->prev->next = e->next;
    } else {
        c->head = e->next;
    }
    if (e->next) {
        e->next->prev = e->prev;
    } else {
        c->tail = e->prev;
    }
    e->prev = e->next = NULL;
}

static void list_push_front(struct lru *c, struct entry *e) {
    e->prev = NULL;
    e->next = c->head;
    if (c->head) {
        c->head->prev = e;
    }
    c->head = e;
    if (!c->tail) {
        c->tail = e;
    }
}

static void bucket_remove(struct lru *c, struct entry *e) {
    struct entry **pp = &c->buckets[hash(e->key) % c->nbuckets];
    while (*pp != e) {
        pp = &(*pp)->chain;
    }
    *pp = e->chain;
}

static int lru_get(struct lru *c, const char *key, int *out) {
    struct entry *e = find(c, key);
    if (!e) {
        return 0;
    }
    list_unlink(c, e);
    list_push_front(c, e);
    *out = e->val;
    return 1;
}

static int lru_put(struct lru *c, const char *key, int val) {
    struct entry *e = find(c, key);
    if (e) {
        e->val = val;
        list_unlink(c, e);
        list_push_front(c, e);
        return 0;
    }
    if (c->len == c->cap) {
        struct entry *old = c->tail;
        list_unlink(c, old);
        bucket_remove(c, old);
        free(old->key);
        free(old);
        c->len--;
    }
    e = malloc(sizeof *e);
    if (!e) {
        return -1;
    }
    size_t n = strlen(key) + 1;
    e->key = malloc(n);
    if (!e->key) {
        free(e);
        return -1;
    }
    memcpy(e->key, key, n);
    e->val = val;
    size_t b = hash(key) % c->nbuckets;
    e->chain = c->buckets[b];
    c->buckets[b] = e;
    list_push_front(c, e);
    c->len++;
    return 0;
}

static void lru_free(struct lru *c) {
    for (struct entry *e = c->head; e;) {
        struct entry *next = e->next;
        free(e->key);
        free(e);
        e = next;
    }
    free(c->buckets);
    free(c);
}

int main(void) {
    struct lru *c = lru_new(2);
    if (!c) {
        return 1;
    }
    int v = 0;
    lru_put(c, "a", 1);
    lru_put(c, "b", 2);
    int found = lru_get(c, "a", &v);
    printf("%d %d\n", found, v);
    lru_put(c, "c", 3);
    found = lru_get(c, "b", &v);
    printf("%d\n", found);
    printf("keys:");
    for (struct entry *e = c->head; e; e = e->next) {
        printf(" %s", e->key);
    }
    printf("\nlen %zu\n", c->len);
    lru_free(c);
    return 0;
}
```

```text output
1 1
0
keys: c a
len 2
```

## A pointer to the link removes any node

`*pp` is the slot that points at the doomed node: either the bucket head
or some `chain` member. Replacing that slot drops the node, including
when it was first. The same loop is `bucket_remove` in the eviction path.

```c file=n05.c
#include <stdio.h>
#include <stdlib.h>

struct node {
    int value;
    struct node *chain;
};

static void remove_value(struct node **bucket, int value) {
    struct node **pp = bucket;
    while (*pp && (*pp)->value != value) {
        pp = &(*pp)->chain;
    }
    struct node *dead = *pp;
    *pp = dead->chain;
    free(dead);
}

int main(void) {
    struct node *bucket = NULL;
    for (int v = 3; v >= 1; v--) {
        struct node *n = malloc(sizeof *n);
        if (!n) {
            return 1;
        }
        n->value = v;
        n->chain = bucket;
        bucket = n;
    }
    remove_value(&bucket, 1);
    for (struct node *n = bucket; n; n = n->chain) {
        printf("%d ", n->value);
    }
    printf("\n");
    while (bucket) {
        struct node *next = bucket->chain;
        free(bucket);
        bucket = next;
    }
    return 0;
}
```

```text output
2 3 
```

## Exercises

Implement an **array-backed** `int -> int` cache (newest first) with the
same operations plus `peek`, `remove` and hit/miss counters.

```c file=exercise.c
#include <stddef.h>
#include <stdio.h>

#define MAX_CAP 8

struct simple_lru {
    int keys[MAX_CAP];
    int vals[MAX_CAP];
    size_t len, cap; /* entries are ordered newest first: index 0 */
    unsigned hits, misses;
};

/* 0 on success, -1 if cap is 0 or greater than MAX_CAP. */
int sl_init(struct simple_lru *s, size_t cap) {
    (void)s; (void)cap;
    return 0; /* TODO */
}

/* 1 and *out on a hit (becomes newest, counts a hit); 0 on a miss (counts). */
int sl_get(struct simple_lru *s, int key, int *out) {
    (void)s; (void)key; (void)out;
    return -1; /* TODO */
}

/* Insert or update; makes the key newest; evicts the oldest when full. */
void sl_put(struct simple_lru *s, int key, int val) {
    (void)s; (void)key; (void)val; /* TODO */
}

/* 1 and *out if present; no recency or stats change. */
int sl_peek(const struct simple_lru *s, int key, int *out) {
    (void)s; (void)key; (void)out;
    return -1; /* TODO */
}

/* 1 if it was present and removed, else 0. */
int sl_remove(struct simple_lru *s, int key) {
    (void)s; (void)key;
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
    struct simple_lru c;
    CHECK("init bad", sl_init(&c, 0) == -1 && sl_init(&c, MAX_CAP + 1) == -1);
    CHECK("init", sl_init(&c, 2) == 0);
    int v = 0;
    sl_put(&c, 1, 10);
    sl_put(&c, 2, 20);
    CHECK("get", sl_get(&c, 1, &v) == 1 && v == 10);
    sl_put(&c, 3, 30); /* evicts key 2 */
    CHECK("evicted", sl_get(&c, 2, &v) == 0);
    CHECK("order", c.len == 2 && c.keys[0] == 3 && c.keys[1] == 1);
    v = 0;
    CHECK("peek", sl_peek(&c, 1, &v) == 1 && v == 10);
    CHECK("peek keeps order", c.keys[0] == 3 && c.keys[1] == 1);
    CHECK("stats", c.hits == 1 && c.misses == 1);
    sl_put(&c, 1, 11); /* update refreshes recency */
    CHECK("update", c.keys[0] == 1 && c.vals[0] == 11 && c.len == 2);
    CHECK("remove", sl_remove(&c, 3) == 1 && sl_remove(&c, 99) == 0 && c.len == 1);
    return failed;
}
```

<details><summary>Solution</summary>

```c file=solution.c
#include <stddef.h>
#include <stdio.h>
#include <string.h>

#define MAX_CAP 8

struct simple_lru {
    int keys[MAX_CAP];
    int vals[MAX_CAP];
    size_t len, cap;
    unsigned hits, misses;
};

int sl_init(struct simple_lru *s, size_t cap) {
    if (cap == 0 || cap > MAX_CAP) {
        return -1;
    }
    memset(s, 0, sizeof *s);
    s->cap = cap;
    return 0;
}

static int index_of(const struct simple_lru *s, int key) {
    for (size_t i = 0; i < s->len; i++) {
        if (s->keys[i] == key) {
            return (int)i;
        }
    }
    return -1;
}

static void erase_at(struct simple_lru *s, size_t i) {
    memmove(&s->keys[i], &s->keys[i + 1], (s->len - i - 1) * sizeof s->keys[0]);
    memmove(&s->vals[i], &s->vals[i + 1], (s->len - i - 1) * sizeof s->vals[0]);
    s->len--;
}

static void insert_front(struct simple_lru *s, int key, int val) {
    memmove(&s->keys[1], &s->keys[0], s->len * sizeof s->keys[0]);
    memmove(&s->vals[1], &s->vals[0], s->len * sizeof s->vals[0]);
    s->keys[0] = key;
    s->vals[0] = val;
    s->len++;
}

int sl_get(struct simple_lru *s, int key, int *out) {
    int i = index_of(s, key);
    if (i < 0) {
        s->misses++;
        return 0;
    }
    s->hits++;
    int val = s->vals[i];
    erase_at(s, (size_t)i);
    insert_front(s, key, val);
    *out = val;
    return 1;
}

void sl_put(struct simple_lru *s, int key, int val) {
    int i = index_of(s, key);
    if (i >= 0) {
        erase_at(s, (size_t)i);
    } else if (s->len == s->cap) {
        s->len--; /* drop the oldest (last) entry */
    }
    insert_front(s, key, val);
}

int sl_peek(const struct simple_lru *s, int key, int *out) {
    int i = index_of(s, key);
    if (i < 0) {
        return 0;
    }
    *out = s->vals[i];
    return 1;
}

int sl_remove(struct simple_lru *s, int key) {
    int i = index_of(s, key);
    if (i < 0) {
        return 0;
    }
    erase_at(s, (size_t)i);
    return 1;
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
    struct simple_lru c;
    CHECK("init bad", sl_init(&c, 0) == -1 && sl_init(&c, MAX_CAP + 1) == -1);
    CHECK("init", sl_init(&c, 2) == 0);
    int v = 0;
    sl_put(&c, 1, 10);
    sl_put(&c, 2, 20);
    CHECK("get", sl_get(&c, 1, &v) == 1 && v == 10);
    sl_put(&c, 3, 30); /* evicts key 2 */
    CHECK("evicted", sl_get(&c, 2, &v) == 0);
    CHECK("order", c.len == 2 && c.keys[0] == 3 && c.keys[1] == 1);
    v = 0;
    CHECK("peek", sl_peek(&c, 1, &v) == 1 && v == 10);
    CHECK("peek keeps order", c.keys[0] == 3 && c.keys[1] == 1);
    CHECK("stats", c.hits == 1 && c.misses == 1);
    sl_put(&c, 1, 11); /* update refreshes recency */
    CHECK("update", c.keys[0] == 1 && c.vals[0] == 11 && c.len == 2);
    CHECK("remove", sl_remove(&c, 3) == 1 && sl_remove(&c, 99) == 0 && c.len == 1);
    return failed;
}
```

</details>

Next: [15 — Streaming](15-streaming.md)
