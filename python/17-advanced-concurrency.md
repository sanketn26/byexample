# Python 17 — Advanced concurrency

One thread per request, with no ceiling, fails by exhausting memory or file
descriptors. Bound how many calls run at once, bound how many jobs wait,
put a deadline on the whole operation, and make shutdown something the
workers can see. `asyncio` has the same three knobs: a semaphore for the
in-flight cap, `asyncio.timeout` for the deadline, and a bounded queue for
backpressure. Threads are here because the blocking call is the interesting
case.

## The pool's high-water mark stays at the worker count

`max_in` is the number you have to be able to explain. If it climbs past
the worker count, the bound is not real: something started work outside
the pool. The gate below holds every worker inside `fn` at once, so the
overlap is visible.

```python file=n01.py
import queue
import threading


def run_pool(workers, jobs, fn):
    q = queue.Queue()
    for i, job in enumerate(jobs):
        q.put((i, job))
    for _ in range(workers):
        q.put(None)
    results = [None] * len(jobs)
    current = 0
    max_in = 0
    lock = threading.Lock()
    need = min(workers, len(jobs))
    arrived = threading.Semaphore(0)
    gate = threading.Event()
    seen = 0

    def worker():
        nonlocal current, max_in, seen
        while True:
            item = q.get()
            if item is None:
                return
            i, job = item
            with lock:
                current += 1
                max_in = max(max_in, current)
                seen += 1
                hit = seen <= need
            if hit:
                arrived.release()
            gate.wait()
            results[i] = fn(job)
            with lock:
                current -= 1

    threads = [threading.Thread(target=worker) for _ in range(workers)]
    for t in threads:
        t.start()
    for _ in range(need):
        arrived.acquire()
    gate.set()
    for t in threads:
        t.join()
    return results, max_in


results, max_in = run_pool(2, [0, 1, 2, 3], lambda n: n * n)
print("pool", results, max_in)
```

```text output
pool [0, 1, 4, 9] 2
```

## A deadline gives up while the call is still blocked

`Thread.join(timeout)` and `Event.wait(timeout)` bound the wait. A socket
timeout that retries forever is not a deadline for the whole operation.
This thread is a daemon: a non-daemon thread keeps the interpreter alive,
and joining it forever would turn the deadline into a hang. A daemon is
for work you are willing to abandon.

```python file=n02.py
import os
import threading

r, w = os.pipe()
box = {}


def blocked():
    os.read(r, 1)
    box["v"] = "done"


t = threading.Thread(target=blocked, daemon=True)
t.start()
t.join(0.05)
print("deadline" if t.is_alive() else box.get("v"), t.daemon)
os.close(w)
t.join(1)
os.close(r)
```

```text output
deadline True
```

## Closing the fd is what unblocks the thread

Cancellation is cooperative. Setting an `Event` does nothing to a thread
blocked in `os.read`, and nothing to a thread that never checks the flag.
Close the resource, or the thread stays stuck until the process exits.

```python file=n03.py
import os
import threading

r, w = os.pipe()
done = threading.Event()
stop = threading.Event()


def blocked():
    os.read(r, 1)
    done.set()


t = threading.Thread(target=blocked, daemon=True)
t.start()
stop.set()
t.join(0.05)
print("still blocked", t.is_alive())
os.close(w)
t.join(1)
print("unblocked", done.is_set())
os.close(r)
```

```text output
still blocked True
unblocked True
```

## A full queue is backpressure

`Queue(maxsize=n)` and `put_nowait` accept what fits and raise `queue.Full`
after that. `put` with a timeout does the same once the wait expires.
`put` with no timeout blocks the producer and hides the overflow. A full
queue is the signal to slow down or reject.

```python file=n04.py
import queue

q = queue.Queue(maxsize=2)
accepted = 0
for i in range(5):
    try:
        q.put_nowait(i)
        accepted += 1
    except queue.Full:
        break
print("accepted", accepted)
try:
    q.put("more", timeout=0.05)
except queue.Full:
    print("full")
```

```text output
accepted 2
full
```

## Stopping can leave the queued work behind

These workers wait until the event is set and never read the queue.
Dropping queued work is a choice. The other choice is to drain. Pick one
and test it. Do not do neither.

```python file=n05.py
import queue
import threading

work = queue.Queue()
for i in range(4):
    work.put(i)
stop = threading.Event()
started = threading.Barrier(3)


def consume():
    started.wait()
    stop.wait()


threads = [threading.Thread(target=consume) for _ in range(2)]
for t in threads:
    t.start()
started.wait()
stop.set()
for t in threads:
    t.join()
print("stopped", work.qsize())
```

```text output
stopped 4
```

## Exercises

Build a pool whose high-water mark stays at the worker count, a
deadline that gives up on a blocked call, and a non-blocking fill of a
bounded queue.

```python file=exercise.py
import os
import queue
import threading


def map_pool(workers, jobs, fn):
    """Run fn on each job with at most `workers` threads.

    Return (results in job order, max number of calls that overlapped).
    """
    raise NotImplementedError


def finishes_before(fn, timeout):
    """Return "ok" if fn returns within timeout seconds, else "deadline".

    The caller must not block past timeout. fn may stay blocked; a daemon
    thread is the right tool.
    """
    raise NotImplementedError


def try_put(limit, n):
    """How many of n items fit in a Queue(maxsize=limit) without blocking."""
    raise NotImplementedError


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


def run():
    state = {"cur": 0, "max": 0}
    lock = threading.Lock()
    release = threading.Event()

    def fn(i):
        with lock:
            state["cur"] += 1
            state["max"] = max(state["max"], state["cur"])
            if state["cur"] >= 2:
                release.set()
        release.wait(1)
        with lock:
            state["cur"] -= 1
        return i * i

    results, max_in = map_pool(2, [0, 1, 2, 3], fn)
    out = [
        check("pool", (results, max_in, state["max"]), ([0, 1, 4, 9], 2, 2)),
        check("fast", finishes_before(lambda: None, 0.5), "ok"),
    ]
    r, w = os.pipe()

    def block():
        os.read(r, 1)

    out.append(check("deadline", finishes_before(block, 0.05), "deadline"))
    os.close(w)
    os.close(r)
    out.append(check("accepted", try_put(2, 5), 2))
    return out


raise SystemExit(0 if all(run()) else 1)
```

<details><summary>Solution</summary>

```python file=solution.py
import os
import queue
import threading


def map_pool(workers, jobs, fn):
    q = queue.Queue()
    for i, job in enumerate(jobs):
        q.put((i, job))
    for _ in range(workers):
        q.put(None)
    results = [None] * len(jobs)
    current = 0
    max_in = 0
    lock = threading.Lock()

    def worker():
        nonlocal current, max_in
        while True:
            item = q.get()
            if item is None:
                return
            i, job = item
            with lock:
                current += 1
                max_in = max(max_in, current)
            try:
                results[i] = fn(job)
            finally:
                with lock:
                    current -= 1

    threads = [threading.Thread(target=worker) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results, max_in


def finishes_before(fn, timeout):
    done = threading.Event()

    def target():
        try:
            fn()
        finally:
            done.set()

    threading.Thread(target=target, daemon=True).start()
    return "ok" if done.wait(timeout) else "deadline"


def try_put(limit, n):
    q = queue.Queue(maxsize=limit)
    accepted = 0
    for i in range(n):
        try:
            q.put_nowait(i)
            accepted += 1
        except queue.Full:
            break
    return accepted


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


def run():
    state = {"cur": 0, "max": 0}
    lock = threading.Lock()
    release = threading.Event()

    def fn(i):
        with lock:
            state["cur"] += 1
            state["max"] = max(state["max"], state["cur"])
            if state["cur"] >= 2:
                release.set()
        release.wait(1)
        with lock:
            state["cur"] -= 1
        return i * i

    results, max_in = map_pool(2, [0, 1, 2, 3], fn)
    out = [
        check("pool", (results, max_in, state["max"]), ([0, 1, 4, 9], 2, 2)),
        check("fast", finishes_before(lambda: None, 0.5), "ok"),
    ]
    r, w = os.pipe()

    def block():
        os.read(r, 1)

    out.append(check("deadline", finishes_before(block, 0.05), "deadline"))
    os.close(w)
    os.close(r)
    out.append(check("accepted", try_put(2, 5), 2))
    return out


raise SystemExit(0 if all(run()) else 1)
```

</details>

Back to the [course index](README.md)
