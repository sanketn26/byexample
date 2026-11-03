# C 14 — Capstone: an LRU Cache

A *least-recently-used* cache keeps the N most recently touched entries and
evicts the stalest. In C there is no map or list in the library, so you
build both: a **hash table with chaining** for lookup and an **intrusive
doubly linked list** for recency, sharing the same nodes. It rehearses
structs, pointers, `malloc`/`free` ownership, and cleanup on every path.
(The same capstone is in every language of this course.)

## Example

```c file=example.c
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct entry {
    char *key; /* owned copy */
    int val;
    struct entry *prev, *next; /* recency list: head = most recent */
    struct entry *chain;       /* bucket chain */
};

struct lru {
    size_t cap, len, nbuckets;
    struct entry **buckets;
    struct entry *head, *tail;
};

static size_t hash(const char *s) { /* djb2 */
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
    *pp = e->chain; /* pointer-to-pointer: no special case for the head */
}

/* Returns 1 and stores the value on a hit, 0 on a miss. */
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

/* 0 on success, -1 on allocation failure. */
static int lru_put(struct lru *c, const char *key, int val) {
    struct entry *e = find(c, key);
    if (e) {
        e->val = val;
        list_unlink(c, e);
        list_push_front(c, e);
        return 0;
    }
    if (c->len == c->cap) { /* evict the least recently used */
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
    if (!c) {
        return;
    }
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
    int found = lru_get(c, "a", &v); /* a becomes the newest */
    printf("%d %d\n", found, v);
    lru_put(c, "c", 3); /* evicts b */
    found = lru_get(c, "b", &v);
    printf("%d\n", found);
    printf("keys:");
    for (struct entry *e = c->head; e; e = e->next) {
        printf(" %s", e->key);
    }
    printf("\nlen %zu\n", c->len);
    printf("%d\n", lru_new(0) == NULL);
    lru_free(c);
    return 0;
}
```

```text output
1 1
0
keys: c a
len 2
1
```

## Details that bite

- **Ownership**: the cache owns its key copies (`malloc` + `memcpy`),
  so callers may free or reuse their strings. Every `free` path must also
  free `key`.
- `bucket_remove` uses a pointer-to-pointer so removing the first node of
  a chain needs no special case; this idiom is worth memorising.
- Failure after eviction (the `malloc`s) leaves the cache smaller than
  before. For strict guarantees, allocate the new entry *first*, then evict.
- A fixed bucket count means chains grow if `cap` is huge relative to
  `nbuckets`; here `nbuckets` is proportional to `cap` so chains stay
  short.
- Not thread-safe: `get` mutates the list, so even readers need the
  mutex (lesson 12).
- Test with `-fsanitize=address`: any leak or use-after-free in the
  eviction path shows up immediately.

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
