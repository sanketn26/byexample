# C 17 — Advanced concurrency

A thread per connection, with nothing to stop it and no ceiling on the
queue, fails by exhausting memory or file descriptors. Bound how many
workers run, and bound how many jobs sit in the queue. Wait with `poll`
so a silent peer cannot block you forever. Shutdown is a flag the workers
actually look at. Join them before the process exits. An async runtime
puts a scheduler under this shape; it does not remove the bound, the
deadline, or the shutdown.

## The pool's high-water mark is the worker cap

The gate holds the first wave inside the job until `workers` of them
have entered, then releases them. `max` is therefore 2, not whatever the
scheduler happened to run. The four results are the squares, in job
order. One thread per request, with no ceiling, dies by running out of
memory or file descriptors. This pool refuses to start a third worker's
worth of simultaneous work.

```c file=n01.c
#define _POSIX_C_SOURCE 200809L
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct pool {
    pthread_mutex_t mu;
    pthread_cond_t gate_cv;
    pthread_cond_t arrived_cv;
    int *jobs;
    int n;
    int next;
    int *results;
    int cur;
    int max_in;
    int arrived;
    int need;
    int open;
};

static void *worker(void *arg) {
    struct pool *p = arg;
    for (;;) {
        pthread_mutex_lock(&p->mu);
        if (p->next >= p->n) {
            pthread_mutex_unlock(&p->mu);
            return NULL;
        }
        int i = p->next++;
        int job = p->jobs[i];
        p->cur++;
        if (p->cur > p->max_in) {
            p->max_in = p->cur;
        }
        p->arrived++;
        pthread_cond_broadcast(&p->arrived_cv);
        while (!p->open) {
            pthread_cond_wait(&p->gate_cv, &p->mu);
        }
        pthread_mutex_unlock(&p->mu);

        int value = job * job;

        pthread_mutex_lock(&p->mu);
        p->results[i] = value;
        p->cur--;
        pthread_mutex_unlock(&p->mu);
    }
}

static int run_pool(int workers, int *jobs, int n, int *results, int *max_in) {
    struct pool p;
    memset(&p, 0, sizeof p);
    p.jobs = jobs;
    p.n = n;
    p.results = results;
    p.need = workers < n ? workers : n;
    pthread_mutex_init(&p.mu, NULL);
    pthread_cond_init(&p.gate_cv, NULL);
    pthread_cond_init(&p.arrived_cv, NULL);

    pthread_t *ts = calloc((size_t)workers, sizeof *ts);
    if (!ts) {
        return -1;
    }
    for (int i = 0; i < workers; i++) {
        if (pthread_create(&ts[i], NULL, worker, &p) != 0) {
            free(ts);
            return -1;
        }
    }
    pthread_mutex_lock(&p.mu);
    while (p.arrived < p.need) {
        pthread_cond_wait(&p.arrived_cv, &p.mu);
    }
    p.open = 1;
    pthread_cond_broadcast(&p.gate_cv);
    pthread_mutex_unlock(&p.mu);
    for (int i = 0; i < workers; i++) {
        pthread_join(ts[i], NULL);
    }
    free(ts);
    *max_in = p.max_in;
    pthread_mutex_destroy(&p.mu);
    pthread_cond_destroy(&p.gate_cv);
    pthread_cond_destroy(&p.arrived_cv);
    return 0;
}

int main(void) {
    int jobs[] = {0, 1, 2, 3};
    int results[4] = {0};
    int max_in = 0;
    if (run_pool(2, jobs, 4, results, &max_in) != 0) {
        return 1;
    }
    printf("pool %d %d %d %d %d\n", results[0], results[1], results[2], results[3], max_in);
    return 0;
}
```

```text output
pool 0 1 4 9 2
```

## A deadline covers the whole wait

`poll` on a pipe nobody writes returns 0 when the 30 milliseconds are
up. That is the deadline. A 150-millisecond read timeout inside a
transfer that retries forever is not one: the operation as a whole never
ends. Close the descriptor, or give the read its own deadline, if a
worker is blocked in a syscall. Setting a flag does not interrupt that
syscall by itself.

```c file=n02.c
#define _POSIX_C_SOURCE 200809L
#include <poll.h>
#include <stdio.h>
#include <unistd.h>

int main(void) {
    int fds[2];
    if (pipe(fds) != 0) {
        return 1;
    }
    struct pollfd pfd = {.fd = fds[0], .events = POLLIN};
    int pr = poll(&pfd, 1, 30);
    printf("%s\n", pr == 0 ? "deadline" : "unexpected");
    close(fds[0]);
    close(fds[1]);
    return 0;
}
```

```text output
deadline
```

## A full ring refuses the next push

Two slots are the bound. The third item is not stored. That refusal is
backpressure: the producer hears about it now. A blocking send hides the
same problem on a thread you may not have to spare. `try_send` and
`put_nowait` are this check, under a mutex when the ring is shared.

```c file=n03.c
#include <stdio.h>

int main(void) {
    struct ring {
        int slot[2];
        int len;
    } ring = {0};
    int accepted = 0;
    for (int i = 0; i < 5; i++) {
        if (ring.len == 2) {
            break;
        }
        ring.slot[ring.len++] = i;
        accepted++;
    }
    printf("accepted %d\n", accepted);
    return 0;
}
```

```text output
accepted 2
```

## Shutdown leaves the queued work with the caller

The workers block on the flag. The main thread waits until both have
incremented `ready`, so the flag is set only after they are inside that
wait. A `pthread_barrier` is the same rendezvous on platforms that have
one; macOS does not. They return without taking the four
queued jobs. `stopped 4` means those jobs are still the caller's to drop
or drain. Cancellation is cooperative: the flag does nothing until the
worker looks at it.

```c file=n04.c
#define _POSIX_C_SOURCE 200809L
#include <pthread.h>
#include <stdio.h>

struct stop_arg {
    pthread_mutex_t *mu;
    pthread_cond_t *cv;
    int *flag;
    int *ready;
};

static void *stop_worker(void *arg) {
    struct stop_arg *a = arg;
    pthread_mutex_lock(a->mu);
    (*a->ready)++;
    pthread_cond_broadcast(a->cv);
    while (!*a->flag) {
        pthread_cond_wait(a->cv, a->mu);
    }
    pthread_mutex_unlock(a->mu);
    return NULL;
}

int main(void) {
    int flag = 0;
    int ready = 0;
    pthread_mutex_t mu = PTHREAD_MUTEX_INITIALIZER;
    pthread_cond_t cv = PTHREAD_COND_INITIALIZER;
    struct stop_arg sa = {&mu, &cv, &flag, &ready};
    pthread_t a, b;
    if (pthread_create(&a, NULL, stop_worker, &sa) != 0 ||
        pthread_create(&b, NULL, stop_worker, &sa) != 0) {
        return 1;
    }
    pthread_mutex_lock(&mu);
    while (ready < 2) {
        pthread_cond_wait(&cv, &mu);
    }
    int left = 4;
    flag = 1;
    pthread_cond_broadcast(&cv);
    pthread_mutex_unlock(&mu);
    pthread_join(a, NULL);
    pthread_join(b, NULL);
    pthread_mutex_destroy(&mu);
    pthread_cond_destroy(&cv);
    printf("stopped %d\n", left);
    return 0;
}
```

```text output
stopped 4
```


## Exercises

`run_pool` squares each job with at most `workers` threads. Hold the workers in the first jobs until `workers` of them are inside, then release them, and report that high-water mark. `deadline_ms` returns 1 when `poll` times out on a pipe nobody writes. `try_put` reports how many items fit in a ring of `limit` slots.

```c file=exercise.c
#define _POSIX_C_SOURCE 200809L
#include <poll.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define static static __attribute__((unused))

struct pool {
    pthread_mutex_t mu;
    pthread_cond_t gate_cv;
    pthread_cond_t arrived_cv;
    int *jobs;
    int n;
    int next;
    int *results;
    int cur;
    int max_in;
    int arrived;
    int need;
    int open;
    int stop;
};

static void *worker(void *arg) {
    struct pool *p = arg;
    for (;;) {
        pthread_mutex_lock(&p->mu);
        if (p->stop || p->next >= p->n) {
            pthread_mutex_unlock(&p->mu);
            return NULL;
        }
        int i = p->next++;
        int job = p->jobs[i];
        p->cur++;
        if (p->cur > p->max_in) {
            p->max_in = p->cur;
        }
        p->arrived++;
        pthread_cond_broadcast(&p->arrived_cv);
        while (!p->open) {
            pthread_cond_wait(&p->gate_cv, &p->mu);
        }
        pthread_mutex_unlock(&p->mu);

        int value = job * job;

        pthread_mutex_lock(&p->mu);
        p->results[i] = value;
        p->cur--;
        pthread_mutex_unlock(&p->mu);
    }
}

static int run_pool(int workers, int *jobs, int n, int *results, int *max_in) {
    (void)workers; (void)jobs; (void)n; (void)results; (void)max_in;
    return -1;
}




static int deadline_ms(int ms) {
    (void)ms;
    return 0;
}



static int try_put(int limit, int n) {
    (void)limit; (void)n;
    return -1;
}



static int failed;
#define CHECK(label, cond)                         \
    do {                                           \
        if (cond) printf("PASS %s\n", label);      \
        else { failed = 1; printf("FAIL %s\n", label); } \
    } while (0)

int main(void) {
    int jobs[] = {0, 1, 2, 3};
    int results[4] = {0};
    int max_in = -1;
    CHECK("pool run", run_pool(2, jobs, 4, results, &max_in) == 0);
    CHECK("pool", results[0] == 0 && results[1] == 1 && results[2] == 4 && results[3] == 9 && max_in == 2);
    CHECK("deadline", deadline_ms(30) == 1);
    CHECK("accepted", try_put(2, 5) == 2);
    return failed;
}
```

<details><summary>Solution</summary>

```c file=solution.c
#define _POSIX_C_SOURCE 200809L
#include <poll.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

struct pool {
    pthread_mutex_t mu;
    pthread_cond_t gate_cv;
    pthread_cond_t arrived_cv;
    int *jobs;
    int n;
    int next;
    int *results;
    int cur;
    int max_in;
    int arrived;
    int need;
    int open;
    int stop;
};

static void *worker(void *arg) {
    struct pool *p = arg;
    for (;;) {
        pthread_mutex_lock(&p->mu);
        if (p->stop || p->next >= p->n) {
            pthread_mutex_unlock(&p->mu);
            return NULL;
        }
        int i = p->next++;
        int job = p->jobs[i];
        p->cur++;
        if (p->cur > p->max_in) {
            p->max_in = p->cur;
        }
        p->arrived++;
        pthread_cond_broadcast(&p->arrived_cv);
        while (!p->open) {
            pthread_cond_wait(&p->gate_cv, &p->mu);
        }
        pthread_mutex_unlock(&p->mu);

        int value = job * job;

        pthread_mutex_lock(&p->mu);
        p->results[i] = value;
        p->cur--;
        pthread_mutex_unlock(&p->mu);
    }
}

static int run_pool(int workers, int *jobs, int n, int *results, int *max_in) {
    struct pool p;
    memset(&p, 0, sizeof p);
    p.jobs = jobs;
    p.n = n;
    p.results = results;
    p.need = workers < n ? workers : n;
    pthread_mutex_init(&p.mu, NULL);
    pthread_cond_init(&p.gate_cv, NULL);
    pthread_cond_init(&p.arrived_cv, NULL);

    pthread_t *ts = calloc((size_t)workers, sizeof *ts);
    if (!ts) {
        return -1;
    }
    for (int i = 0; i < workers; i++) {
        if (pthread_create(&ts[i], NULL, worker, &p) != 0) {
            return -1;
        }
    }
    pthread_mutex_lock(&p.mu);
    while (p.arrived < p.need) {
        pthread_cond_wait(&p.arrived_cv, &p.mu);
    }
    p.open = 1;
    pthread_cond_broadcast(&p.gate_cv);
    pthread_mutex_unlock(&p.mu);
    for (int i = 0; i < workers; i++) {
        pthread_join(ts[i], NULL);
    }
    free(ts);
    *max_in = p.max_in;
    pthread_mutex_destroy(&p.mu);
    pthread_cond_destroy(&p.gate_cv);
    pthread_cond_destroy(&p.arrived_cv);
    return 0;
}


static int deadline_ms(int ms) {
    int fds[2];
    if (pipe(fds) != 0) return -1;
    struct pollfd p = {.fd = fds[0], .events = POLLIN};
    int pr = poll(&p, 1, ms);
    close(fds[0]);
    close(fds[1]);
    return pr == 0 ? 1 : -1;
}

static int try_put(int limit, int n) {
    int slot[8];
    int sink = 0;
    if (limit < 0 || limit > 8) return -1;
    int len = 0, accepted = 0;
    for (int i = 0; i < n; i++) {
        if (len == limit) break;
        slot[len++] = i;
        sink += slot[len - 1];
        accepted++;
    }
    (void)sink;
    return accepted;
}

static int failed;
#define CHECK(label, cond)                         \
    do {                                           \
        if (cond) printf("PASS %s\n", label);      \
        else { failed = 1; printf("FAIL %s\n", label); } \
    } while (0)

int main(void) {
    int jobs[] = {0, 1, 2, 3};
    int results[4] = {0};
    int max_in = -1;
    CHECK("pool run", run_pool(2, jobs, 4, results, &max_in) == 0);
    CHECK("pool", results[0] == 0 && results[1] == 1 && results[2] == 4 && results[3] == 9 && max_in == 2);
    CHECK("deadline", deadline_ms(30) == 1);
    CHECK("accepted", try_put(2, 5) == 2);
    return failed;
}
```

</details>

Back to the [course index](README.md)
