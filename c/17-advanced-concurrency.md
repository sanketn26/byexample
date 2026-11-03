# C 17 — Advanced concurrency

A thread per connection, with nothing to stop it and no ceiling on the queue, fails by exhausting memory or file descriptors. Bound the workers, bound the queue, wait with `poll` so a silent peer cannot block you forever, and make shutdown a flag the workers actually look at.

## Example

```c file=example.c
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

struct stop_arg {
    pthread_barrier_t *started;
    pthread_mutex_t *mu;
    pthread_cond_t *cv;
    int *flag;
};

static void *stop_worker(void *arg) {
    struct stop_arg *a = arg;
    pthread_barrier_wait(a->started);
    pthread_mutex_lock(a->mu);
    while (!*a->flag) {
        pthread_cond_wait(a->cv, a->mu);
    }
    pthread_mutex_unlock(a->mu);
    return NULL;
}

int main(void) {
    int jobs[] = {0, 1, 2, 3};
    int results[4] = {0};
    int max_in = 0;
    if (run_pool(2, jobs, 4, results, &max_in) != 0) {
        return 1;
    }
    printf("pool %d %d %d %d %d\n", results[0], results[1], results[2], results[3], max_in);

    /* Deadline: poll a pipe nobody writes. */
    int fds[2];
    if (pipe(fds) != 0) {
        return 1;
    }
    struct pollfd pfd = {.fd = fds[0], .events = POLLIN};
    int pr = poll(&pfd, 1, 30);
    printf("%s\n", pr == 0 ? "deadline" : "unexpected");
    close(fds[0]);
    close(fds[1]);

    /* Bounded queue: try_push fails once two slots are taken. A channel's
       try_send is this check, under the mutex. */
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

    int flag = 0;
    pthread_mutex_t mu = PTHREAD_MUTEX_INITIALIZER;
    pthread_cond_t cv = PTHREAD_COND_INITIALIZER;
    pthread_barrier_t started;
    pthread_barrier_init(&started, NULL, 3);
    struct stop_arg sa = {&started, &mu, &cv, &flag};
    pthread_t a, b;
    pthread_create(&a, NULL, stop_worker, &sa);
    pthread_create(&b, NULL, stop_worker, &sa);
    pthread_barrier_wait(&started);
    int left = 4; /* queued work the workers never take */
    pthread_mutex_lock(&mu);
    flag = 1;
    pthread_cond_broadcast(&cv);
    pthread_mutex_unlock(&mu);
    pthread_join(a, NULL);
    pthread_join(b, NULL);
    pthread_barrier_destroy(&started);
    pthread_mutex_destroy(&mu);
    pthread_cond_destroy(&cv);
    printf("stopped %d\n", left);
    return 0;
}
```

```text output
pool 0 1 4 9 2
deadline
accepted 2
stopped 4
```

## Details that bite

- Bound two numbers: how many workers run, and how many jobs sit in the
  queue. One thread, goroutine or task per request, with no ceiling,
  dies by running out of memory or file descriptors.
- `max` in the pool output is the number you have to be able to explain.
  The example holds the first wave of workers inside the job until that
  many have entered, so the high-water mark is observable instead of
  depending on the scheduler.
- A full bounded channel (`put_nowait`, `select`/`default`, `try_send`,
  a ring that refuses the next push) is backpressure. The producer hears
  about it now. A blocking send hides the problem on a thread you may
  not be able to spare.
- A deadline covers the whole operation. A 150ms read timeout inside a
  transfer that retries forever is not one. `context`, `recv_timeout`
  and `poll` are the same idea.
- Cancellation is cooperative. Cancelling a context or setting a flag
  does nothing to a worker blocked in a syscall until that syscall is
  also interruptible: close the fd, or give the read its own deadline.
  The example's workers are alive, then told to stop, and the four
  queued jobs stay queued (`stopped 4`) for the caller to drop or drain.
- Join the workers before the process exits. Rust async runtimes add a
  scheduler under this shape; they do not remove the bound, the deadline
  or the shutdown.

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
