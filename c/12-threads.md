# C 12 — Threads (POSIX and C11 atomics)

C11 defines atomics and thread-local storage. The threads themselves, on
Linux and macOS, come from POSIX threads. There is no safety net: a data
race is undefined behaviour. Link with `-pthread`. When you are hunting
races, use `-fsanitize=thread` instead of the address sanitizer; the two
do not combine.

An unsynchronised read and write of the same object from two threads is a
data race. `counter++` without a mutex loses updates. Always `pthread_join`
or detach every thread. Do not let a thread use a stack variable of a
function that has already returned. Pass each thread its own argument:
handing out `&i` from a `for` loop is a classic bug, because the loop
moves on. Take locks in one global order or you can deadlock.

`pthread_create` returns an error code. It does not set `errno`.
`<threads.h>` exists in C11, but pthreads is the widely supported API.
`strtok`, `localtime`, `rand`, and `strerror` may not be thread-safe; look
for the `_r` variants.

## Join before you read the result

Each job is a separate struct, so the thread writes a slot the loop will
not reuse. `pthread_join` waits until that write has happened.

```c file=n01.c
#define _POSIX_C_SOURCE 200809L
#include <pthread.h>
#include <stdio.h>

struct job {
    int id;
    long result;
};

static void *square_job(void *arg) {
    struct job *j = arg;
    j->result = (long)j->id * j->id;
    return NULL;
}

int main(void) {
    pthread_t threads[4];
    struct job jobs[4];
    for (int i = 0; i < 4; i++) {
        jobs[i].id = i;
        int rc = pthread_create(&threads[i], NULL, square_job, &jobs[i]);
        if (rc != 0) {
            return 1;
        }
    }
    for (int i = 0; i < 4; i++) {
        pthread_join(threads[i], NULL);
        printf("%ld ", jobs[i].result);
    }
    printf("\n");
    return 0;
}
```

```text output
0 1 4 9 
```

## A mutex and an atomic both count

The mutex covers the plain `long`. `atomic_fetch_add` covers `hits`.
Atomics are for one variable or a flag. The default order is
`memory_order_seq_cst`, and that is the safe choice. If two variables
must change together, use a lock. Four threads each add 10000.

```c file=n02.c
#define _POSIX_C_SOURCE 200809L
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>

static long counter;
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static atomic_long hits;

static void *incr(void *arg) {
    (void)arg;
    for (int i = 0; i < 10000; i++) {
        pthread_mutex_lock(&lock);
        counter++;
        pthread_mutex_unlock(&lock);
        atomic_fetch_add(&hits, 1);
    }
    return NULL;
}

int main(void) {
    pthread_t threads[4];
    for (int i = 0; i < 4; i++) {
        if (pthread_create(&threads[i], NULL, incr, NULL) != 0) {
            return 1;
        }
    }
    for (int i = 0; i < 4; i++) {
        pthread_join(threads[i], NULL);
    }
    printf("%ld %ld\n", counter, (long)atomic_load(&hits));
    return 0;
}
```

```text output
40000 40000
```

## Wait in a loop; wakeups can be spurious

`pthread_cond_wait` can return when the condition is still false, and
another thread may have taken the item. Re-check in a `while`. The
sentinel `-1` says the producer is finished. A small integer can ride
home in the `void *` return via `intptr_t`; it is not a pointer.

```c file=n03.c
#define _POSIX_C_SOURCE 200809L
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>

struct queue {
    int items[4];
    int head, count;
    pthread_mutex_t m;
    pthread_cond_t not_empty, not_full;
};

static void q_push(struct queue *q, int v) {
    pthread_mutex_lock(&q->m);
    while (q->count == 4) {
        pthread_cond_wait(&q->not_full, &q->m);
    }
    q->items[(q->head + q->count) % 4] = v;
    q->count++;
    pthread_cond_signal(&q->not_empty);
    pthread_mutex_unlock(&q->m);
}

static int q_pop(struct queue *q) {
    pthread_mutex_lock(&q->m);
    while (q->count == 0) {
        pthread_cond_wait(&q->not_empty, &q->m);
    }
    int v = q->items[q->head];
    q->head = (q->head + 1) % 4;
    q->count--;
    pthread_cond_signal(&q->not_full);
    pthread_mutex_unlock(&q->m);
    return v;
}

static void *producer(void *arg) {
    struct queue *q = arg;
    for (int i = 1; i <= 10; i++) {
        q_push(q, i);
    }
    q_push(q, -1);
    return NULL;
}

static void *consumer(void *arg) {
    struct queue *q = arg;
    long sum = 0;
    int v;
    while ((v = q_pop(q)) != -1) {
        sum += v;
    }
    return (void *)(intptr_t)sum;
}

int main(void) {
    struct queue q = {.m = PTHREAD_MUTEX_INITIALIZER,
                      .not_empty = PTHREAD_COND_INITIALIZER,
                      .not_full = PTHREAD_COND_INITIALIZER};
    pthread_t prod, cons;
    if (pthread_create(&prod, NULL, producer, &q) != 0 ||
        pthread_create(&cons, NULL, consumer, &q) != 0) {
        return 1;
    }
    void *ret = NULL;
    pthread_join(prod, NULL);
    pthread_join(cons, &ret);
    printf("sum=%ld\n", (long)(intptr_t)ret);
    return 0;
}
```

```text output
sum=55
```

## Each thread has its own _Thread_local

The worker stores 99 in its copy and returns that copy. The main thread's
`tl_value` is still 7. Nothing was locked, because nothing was shared.

```c file=n04.c
#define _POSIX_C_SOURCE 200809L
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>

static _Thread_local int tl_value;

static void *tl_job(void *arg) {
    tl_value = (int)(intptr_t)arg;
    return (void *)(intptr_t)tl_value;
}

int main(void) {
    tl_value = 7;
    pthread_t t;
    if (pthread_create(&t, NULL, tl_job, (void *)(intptr_t)99) != 0) {
        return 1;
    }
    void *ret = NULL;
    pthread_join(t, &ret);
    printf("%ld %d\n", (long)(intptr_t)ret, tl_value);
    return 0;
}
```

```text output
99 7
```


## Exercises

```c file=exercise.c
#define _POSIX_C_SOURCE 200809L
#include <pthread.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

/* Sum a[0..n) using `nthreads` pthreads over contiguous chunks. */
long parallel_sum(const int *a, size_t n, int nthreads) {
    (void)a; (void)n; (void)nthreads;
    return -1; /* TODO */
}

/* A counter safe to share between threads. */
struct counter {
    pthread_mutex_t m;
    long value;
};

void counter_init(struct counter *c) {
    (void)c; /* TODO */
}

void counter_add(struct counter *c, long delta) {
    (void)c; (void)delta; /* TODO */
}

long counter_get(struct counter *c) {
    (void)c;
    return -1; /* TODO */
}

void counter_destroy(struct counter *c) {
    (void)c; /* TODO */
}

/* A bounded blocking queue of ints (capacity 4). */
struct bqueue {
    int items[4];
    int head, count;
    pthread_mutex_t m;
    pthread_cond_t not_empty, not_full;
};

void bq_init(struct bqueue *q) {
    (void)q; /* TODO */
}

/* Blocks while the queue is full. */
void bq_push(struct bqueue *q, int v) {
    (void)q; (void)v; /* TODO */
}

/* Blocks while the queue is empty. */
int bq_pop(struct bqueue *q) {
    (void)q;
    return -1; /* TODO */
}

void bq_destroy(struct bqueue *q) {
    (void)q; /* TODO */
}

/* Compute fib(n) (iteratively) on a new thread and return the value
   delivered through pthread_join. Return -1 if the thread cannot start. */
long fib_in_thread(int n) {
    (void)n;
    return -2; /* TODO */
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

static void *adder(void *arg) {
    struct counter *c = arg;
    for (int i = 0; i < 5000; i++) {
        counter_add(c, 1);
    }
    return NULL;
}

static void *producer(void *arg) {
    struct bqueue *q = arg;
    for (int i = 1; i <= 20; i++) {
        bq_push(q, i);
    }
    bq_push(q, -1);
    return NULL;
}

static void *consumer(void *arg) {
    struct bqueue *q = arg;
    long sum = 0;
    int v;
    while ((v = bq_pop(q)) != -1) {
        sum += v;
    }
    return (void *)(intptr_t)sum;
}

int main(void) {
    int data[1000];
    long expect = 0;
    for (int i = 0; i < 1000; i++) {
        data[i] = i;
        expect += i;
    }
    CHECK("parallel_sum 4", parallel_sum(data, 1000, 4) == expect);
    CHECK("parallel_sum 1", parallel_sum(data, 1000, 1) == expect);
    CHECK("parallel_sum uneven", parallel_sum(data, 7, 3) == 21);
    CHECK("parallel_sum empty", parallel_sum(data, 0, 4) == 0);

    struct counter c;
    counter_init(&c);
    pthread_t ts[4];
    for (int i = 0; i < 4; i++) {
        pthread_create(&ts[i], NULL, adder, &c);
    }
    for (int i = 0; i < 4; i++) {
        pthread_join(ts[i], NULL);
    }
    CHECK("counter", counter_get(&c) == 20000);
    counter_destroy(&c);

    struct bqueue q;
    bq_init(&q);
    pthread_t p, k;
    pthread_create(&p, NULL, producer, &q);
    pthread_create(&k, NULL, consumer, &q);
    void *ret = NULL;
    pthread_join(p, NULL);
    pthread_join(k, &ret);
    CHECK("queue", (long)(intptr_t)ret == 210);
    bq_destroy(&q);

    CHECK("fib_in_thread", fib_in_thread(30) == 832040);
    return failed;
}
```

<details><summary>Solution</summary>

```c file=solution.c
#define _POSIX_C_SOURCE 200809L
#include <pthread.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

struct chunk {
    const int *a;
    size_t n;
    long sum;
};

static void *sum_chunk(void *arg) {
    struct chunk *c = arg;
    long s = 0;
    for (size_t i = 0; i < c->n; i++) {
        s += c->a[i];
    }
    c->sum = s;
    return NULL;
}

long parallel_sum(const int *a, size_t n, int nthreads) {
    if (n == 0 || nthreads < 1) {
        return 0;
    }
    if ((size_t)nthreads > n) {
        nthreads = (int)n;
    }
    pthread_t *ts = malloc((size_t)nthreads * sizeof *ts);
    struct chunk *cs = malloc((size_t)nthreads * sizeof *cs);
    if (!ts || !cs) {
        free(ts);
        free(cs);
        return -1;
    }
    size_t per = (n + (size_t)nthreads - 1) / (size_t)nthreads;
    int started = 0;
    for (int i = 0; i < nthreads; i++) {
        size_t start = (size_t)i * per;
        size_t len = start >= n ? 0 : (n - start < per ? n - start : per);
        cs[i] = (struct chunk){a + start, len, 0};
        if (pthread_create(&ts[i], NULL, sum_chunk, &cs[i]) != 0) {
            break;
        }
        started++;
    }
    long total = 0;
    for (int i = 0; i < started; i++) {
        pthread_join(ts[i], NULL);
        total += cs[i].sum;
    }
    free(ts);
    free(cs);
    return total;
}

struct counter {
    pthread_mutex_t m;
    long value;
};

void counter_init(struct counter *c) {
    pthread_mutex_init(&c->m, NULL);
    c->value = 0;
}

void counter_add(struct counter *c, long delta) {
    pthread_mutex_lock(&c->m);
    c->value += delta;
    pthread_mutex_unlock(&c->m);
}

long counter_get(struct counter *c) {
    pthread_mutex_lock(&c->m);
    long v = c->value;
    pthread_mutex_unlock(&c->m);
    return v;
}

void counter_destroy(struct counter *c) {
    pthread_mutex_destroy(&c->m);
}

struct bqueue {
    int items[4];
    int head, count;
    pthread_mutex_t m;
    pthread_cond_t not_empty, not_full;
};

void bq_init(struct bqueue *q) {
    q->head = q->count = 0;
    pthread_mutex_init(&q->m, NULL);
    pthread_cond_init(&q->not_empty, NULL);
    pthread_cond_init(&q->not_full, NULL);
}

void bq_push(struct bqueue *q, int v) {
    pthread_mutex_lock(&q->m);
    while (q->count == 4) {
        pthread_cond_wait(&q->not_full, &q->m);
    }
    q->items[(q->head + q->count) % 4] = v;
    q->count++;
    pthread_cond_signal(&q->not_empty);
    pthread_mutex_unlock(&q->m);
}

int bq_pop(struct bqueue *q) {
    pthread_mutex_lock(&q->m);
    while (q->count == 0) {
        pthread_cond_wait(&q->not_empty, &q->m);
    }
    int v = q->items[q->head];
    q->head = (q->head + 1) % 4;
    q->count--;
    pthread_cond_signal(&q->not_full);
    pthread_mutex_unlock(&q->m);
    return v;
}

void bq_destroy(struct bqueue *q) {
    pthread_cond_destroy(&q->not_empty);
    pthread_cond_destroy(&q->not_full);
    pthread_mutex_destroy(&q->m);
}

static void *fib_worker(void *arg) {
    int n = (int)(intptr_t)arg;
    long a = 0, b = 1;
    for (int i = 0; i < n; i++) {
        long t = a + b;
        a = b;
        b = t;
    }
    return (void *)(intptr_t)a;
}

long fib_in_thread(int n) {
    pthread_t t;
    if (pthread_create(&t, NULL, fib_worker, (void *)(intptr_t)n) != 0) {
        return -1;
    }
    void *ret;
    pthread_join(t, &ret);
    return (long)(intptr_t)ret;
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

static void *adder(void *arg) {
    struct counter *c = arg;
    for (int i = 0; i < 5000; i++) {
        counter_add(c, 1);
    }
    return NULL;
}

static void *producer(void *arg) {
    struct bqueue *q = arg;
    for (int i = 1; i <= 20; i++) {
        bq_push(q, i);
    }
    bq_push(q, -1);
    return NULL;
}

static void *consumer(void *arg) {
    struct bqueue *q = arg;
    long sum = 0;
    int v;
    while ((v = bq_pop(q)) != -1) {
        sum += v;
    }
    return (void *)(intptr_t)sum;
}

int main(void) {
    int data[1000];
    long expect = 0;
    for (int i = 0; i < 1000; i++) {
        data[i] = i;
        expect += i;
    }
    CHECK("parallel_sum 4", parallel_sum(data, 1000, 4) == expect);
    CHECK("parallel_sum 1", parallel_sum(data, 1000, 1) == expect);
    CHECK("parallel_sum uneven", parallel_sum(data, 7, 3) == 21);
    CHECK("parallel_sum empty", parallel_sum(data, 0, 4) == 0);

    struct counter c;
    counter_init(&c);
    pthread_t ts[4];
    for (int i = 0; i < 4; i++) {
        pthread_create(&ts[i], NULL, adder, &c);
    }
    for (int i = 0; i < 4; i++) {
        pthread_join(ts[i], NULL);
    }
    CHECK("counter", counter_get(&c) == 20000);
    counter_destroy(&c);

    struct bqueue q;
    bq_init(&q);
    pthread_t p, k;
    pthread_create(&p, NULL, producer, &q);
    pthread_create(&k, NULL, consumer, &q);
    void *ret = NULL;
    pthread_join(p, NULL);
    pthread_join(k, &ret);
    CHECK("queue", (long)(intptr_t)ret == 210);
    bq_destroy(&q);

    CHECK("fib_in_thread", fib_in_thread(30) == 832040);
    return failed;
}
```

</details>

Next: [13 — Testing](13-testing.md)
