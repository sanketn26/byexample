# Python 12 — asyncio

`asyncio` runs many I/O-bound tasks on **one thread** by switching at
`await` points. It is cooperative: a task that never awaits starves
everyone else.

## Example

```python file=example.py
import asyncio
import time
from contextlib import asynccontextmanager


async def fetch(name, delay):
    await asyncio.sleep(delay)          # stands in for network I/O
    return f"{name}:{delay}"


async def boom():
    raise ValueError("bad")


async def ticker(n):                    # an async generator
    for i in range(n):
        await asyncio.sleep(0)
        yield i


@asynccontextmanager
async def session():
    print("open")
    try:
        yield "s"
    finally:
        print("close")


async def main():
    # Calling a coroutine function only creates the coroutine; await runs it
    print(await fetch("a", 0.01))

    # gather: run concurrently, results come back in argument order
    print(await asyncio.gather(fetch("a", 0.03), fetch("b", 0.01), fetch("c", 0.02)))

    # Concurrency, not parallelism: three 50 ms sleeps overlap
    start = time.perf_counter()
    await asyncio.gather(*(asyncio.sleep(0.05) for _ in range(3)))
    print(time.perf_counter() - start < 0.12)

    # TaskGroup (3.11+): structured concurrency, cancels siblings on error
    async with asyncio.TaskGroup() as tg:
        t1 = tg.create_task(fetch("x", 0.01))
        t2 = tg.create_task(fetch("y", 0.01))
    print(t1.result(), t2.result())

    # Timeouts
    try:
        async with asyncio.timeout(0.01):
            await asyncio.sleep(1)
    except TimeoutError:
        print("timed out")

    # Producer / consumer over a Queue
    q = asyncio.Queue(maxsize=2)

    async def producer():
        for i in range(1, 4):
            await q.put(i)
        await q.put(None)               # sentinel

    async def consumer():
        total = 0
        while (item := await q.get()) is not None:
            total += item
        return total

    _, total = await asyncio.gather(producer(), consumer())
    print("sum", total)

    # Semaphore bounds concurrency
    sem = asyncio.Semaphore(2)
    running = peak = 0

    async def job():
        nonlocal running, peak
        async with sem:
            running += 1
            peak = max(peak, running)
            await asyncio.sleep(0.01)
            running -= 1

    await asyncio.gather(*(job() for _ in range(6)))
    print("peak", peak)

    # Cancellation is delivered as CancelledError at the next await
    task = asyncio.create_task(asyncio.sleep(10))
    await asyncio.sleep(0)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("cancelled", task.cancelled())

    # Blocking code goes to a thread so the loop keeps running
    print(await asyncio.to_thread(sum, range(1000)))

    # async for, async with
    print([i async for i in ticker(3)])
    async with session() as s:
        print("using", s)

    # Errors: by default gather raises the first; or collect them
    print(await asyncio.gather(fetch("ok", 0), boom(), return_exceptions=True))


asyncio.run(main())
```

```text output
a:0.01
['a:0.03', 'b:0.01', 'c:0.02']
True
x:0.01 y:0.01
timed out
sum 6
peak 2
cancelled True
499500
[0, 1, 2]
open
using s
close
['ok:0', ValueError('bad')]
```

## Details that bite

- Forgetting `await` gives a "coroutine was never awaited" warning and
  silently does nothing.
- **Never block the loop**: `time.sleep`, `requests.get`, heavy CPU work
  and sync file reads freeze every task. Use `asyncio.sleep`, async
  libraries, `asyncio.to_thread`, or a process pool.
- `asyncio.create_task` needs a **strong reference**; a task nobody holds
  can be garbage-collected mid-flight. Keep it in a set or a `TaskGroup`.
- Catching `CancelledError` and swallowing it breaks cancellation and
  timeouts; re-raise it.
- `asyncio.run` can be called once per thread at the top level, not from
  inside a running loop.
- asyncio gives concurrency for I/O only. For CPU-bound work use
  `multiprocessing`/`concurrent.futures.ProcessPoolExecutor`.
- Mixing sync and async code is the main design cost: pick a boundary and
  keep it clean.

## Exercises

```python file=exercise.py
import asyncio


async def gather_limited(factories, limit):
    """Await every zero-argument coroutine *factory* with at most `limit`
    running at once. Return the results in input order."""
    raise NotImplementedError


async def first_completed(*coros):
    """Return the result of whichever coroutine finishes first and cancel
    the rest."""
    raise NotImplementedError


async def retry(factory, attempts, delay=0):
    """Await factory() until it succeeds; sleep `delay` between attempts.
    Re-raise the last exception after `attempts` failures."""
    raise NotImplementedError


async def with_default(coro, seconds, default):
    """Result of coro, or `default` if it takes longer than `seconds`."""
    raise NotImplementedError


async def pipeline(items):
    """Producer puts items on a queue; a worker doubles each; return the
    doubled values in order. Use an asyncio.Queue and a sentinel."""
    raise NotImplementedError


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


async def main():
    running = peak = 0

    def make(n):
        async def work():
            nonlocal running, peak
            running += 1
            peak = max(peak, running)
            await asyncio.sleep(0.01)
            running -= 1
            return n * n
        return work

    out = await gather_limited([make(i) for i in range(6)], 2)
    results = [check("gather_limited", (out, peak), ([0, 1, 4, 9, 16, 25], 2))]

    async def slow():
        await asyncio.sleep(0.5)
        return "slow"

    async def fast():
        await asyncio.sleep(0.01)
        return "fast"

    results.append(check("first_completed", await first_completed(slow(), fast()), "fast"))

    calls = 0

    async def flaky():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ConnectionError("nope")
        return "ok"

    results.append(check("retry", (await retry(flaky, 5), calls), ("ok", 3)))

    async def always_fails():
        raise KeyError("x")

    try:
        await retry(always_fails, 2)
        results.append(check("retry exhausted", "no error", "KeyError"))
    except KeyError:
        results.append(check("retry exhausted", "KeyError", "KeyError"))

    results.append(check("with_default hit", await with_default(slow(), 0.02, "dflt"), "dflt"))
    results.append(check("with_default ok", await with_default(fast(), 0.5, "dflt"), "fast"))
    results.append(check("pipeline", await pipeline([1, 2, 3]), [2, 4, 6]))
    return results


raise SystemExit(0 if all(asyncio.run(main())) else 1)
```

<details><summary>Solution</summary>

```python file=solution.py
import asyncio


async def gather_limited(factories, limit):
    sem = asyncio.Semaphore(limit)

    async def run(factory):
        async with sem:
            return await factory()

    return await asyncio.gather(*(run(f) for f in factories))


async def first_completed(*coros):
    tasks = [asyncio.ensure_future(c) for c in coros]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for p in pending:
        p.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    return next(iter(done)).result()


async def retry(factory, attempts, delay=0):
    for attempt in range(attempts):
        try:
            return await factory()
        except Exception:
            if attempt == attempts - 1:
                raise
            await asyncio.sleep(delay)


async def with_default(coro, seconds, default):
    try:
        async with asyncio.timeout(seconds):
            return await coro
    except TimeoutError:
        return default


async def pipeline(items):
    inbox, outbox = asyncio.Queue(), asyncio.Queue()

    async def producer():
        for item in items:
            await inbox.put(item)
        await inbox.put(None)

    async def worker():
        while (item := await inbox.get()) is not None:
            await outbox.put(item * 2)
        await outbox.put(None)

    await asyncio.gather(producer(), worker())
    out = []
    while (v := await outbox.get()) is not None:
        out.append(v)
    return out


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


async def main():
    running = peak = 0

    def make(n):
        async def work():
            nonlocal running, peak
            running += 1
            peak = max(peak, running)
            await asyncio.sleep(0.01)
            running -= 1
            return n * n
        return work

    out = await gather_limited([make(i) for i in range(6)], 2)
    results = [check("gather_limited", (out, peak), ([0, 1, 4, 9, 16, 25], 2))]

    async def slow():
        await asyncio.sleep(0.5)
        return "slow"

    async def fast():
        await asyncio.sleep(0.01)
        return "fast"

    results.append(check("first_completed", await first_completed(slow(), fast()), "fast"))

    calls = 0

    async def flaky():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ConnectionError("nope")
        return "ok"

    results.append(check("retry", (await retry(flaky, 5), calls), ("ok", 3)))

    async def always_fails():
        raise KeyError("x")

    try:
        await retry(always_fails, 2)
        results.append(check("retry exhausted", "no error", "KeyError"))
    except KeyError:
        results.append(check("retry exhausted", "KeyError", "KeyError"))

    results.append(check("with_default hit", await with_default(slow(), 0.02, "dflt"), "dflt"))
    results.append(check("with_default ok", await with_default(fast(), 0.5, "dflt"), "fast"))
    results.append(check("pipeline", await pipeline([1, 2, 3]), [2, 4, 6]))
    return results


raise SystemExit(0 if all(asyncio.run(main())) else 1)
```

</details>

Next: [13 — Testing](13-testing.md)
