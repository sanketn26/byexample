# Python 12 — asyncio

`asyncio` runs many I/O-bound tasks on one thread by switching at `await`
points. It is cooperative: a task that never awaits starves everyone else.
It is concurrency for I/O, not for CPU. CPU-bound work belongs in a process
pool. Pick one sync/async boundary and keep it.

## A coroutine does nothing until you await it

Calling the async function only builds the coroutine object. `await` runs
it. Forgetting `await` warns that the coroutine was never awaited, and the
body never runs.

```python file=n01.py
import asyncio
import gc
import warnings


async def fetch(name, delay):
    await asyncio.sleep(delay)
    return f"{name}:{delay}"


async def main():
    print(await fetch("a", 0.01))


with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    fetch("a", 0)
    gc.collect()
print(caught[0].category.__name__)

asyncio.run(main())
```

```text output
RuntimeWarning
a:0.01
```

## `gather` keeps argument order

The tasks run concurrently. The result list follows the arguments, not
the finish order. Three overlapping sleeps take about one delay, not
three. That is one thread switching, not extra cores.

```python file=n02.py
import asyncio
import time


async def fetch(name, delay):
    await asyncio.sleep(delay)
    return f"{name}:{delay}"


async def main():
    print(await asyncio.gather(fetch("a", 0.03), fetch("b", 0.01), fetch("c", 0.02)))
    start = time.perf_counter()
    await asyncio.gather(*(asyncio.sleep(0.05) for _ in range(3)))
    print(time.perf_counter() - start < 0.12)


asyncio.run(main())
```

```text output
['a:0.03', 'b:0.01', 'c:0.02']
True
```

## `TaskGroup` waits, and cancels the siblings

Leaving the `async with` block waits for every task. If one raises, the
group cancels the others. Hold tasks here, or in a set you keep: a task
with no strong reference can be garbage-collected before it finishes.

```python file=n03.py
import asyncio


async def fetch(name, delay):
    await asyncio.sleep(delay)
    return f"{name}:{delay}"


async def main():
    async with asyncio.TaskGroup() as tg:
        t1 = tg.create_task(fetch("x", 0.01))
        t2 = tg.create_task(fetch("y", 0.01))
    print(t1.result(), t2.result())


asyncio.run(main())
```

```text output
x:0.01 y:0.01
```

## `timeout` bounds one wait

The block raises `TimeoutError` when the deadline passes. Catching
`CancelledError` inside the work and swallowing it breaks this, and it
breaks `task.cancel`. Re-raise it.

```python file=n04.py
import asyncio


async def main():
    try:
        async with asyncio.timeout(0.01):
            await asyncio.sleep(1)
    except TimeoutError:
        print("timed out")


asyncio.run(main())
```

```text output
timed out
```

## A queue hands values from producer to consumer

`await put` and `await get` are the handoff. `maxsize` stops the producer
from running arbitrarily far ahead. A sentinel marks the end because the
queue cannot close.

```python file=n05.py
import asyncio


async def main():
    q = asyncio.Queue(maxsize=2)

    async def producer():
        for i in range(1, 4):
            await q.put(i)
        await q.put(None)

    async def consumer():
        total = 0
        while (item := await q.get()) is not None:
            total += item
        return total

    _, total = await asyncio.gather(producer(), consumer())
    print("sum", total)


asyncio.run(main())
```

```text output
sum 6
```

## A semaphore caps how many run

`async with sem` holds one permit. The peak stays at the limit even when
you schedule more jobs than that.

```python file=n06.py
import asyncio


async def main():
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


asyncio.run(main())
```

```text output
peak 2
```

## Cancel arrives at the next `await`

`task.cancel` marks the task. The task sees `CancelledError` when it next
awaits. Re-raise that error so the task actually ends cancelled.

```python file=n07.py
import asyncio


async def work():
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        print("saw cancel")
        raise


async def main():
    task = asyncio.create_task(work())
    await asyncio.sleep(0)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("cancelled", task.cancelled())


asyncio.run(main())
```

```text output
saw cancel
cancelled True
```

## Blocking calls leave the thread

`time.sleep`, a sync HTTP library, heavy CPU, and a sync file read freeze
every task. `asyncio.sleep` is the awaitable delay. `asyncio.to_thread`
runs a blocking call off the loop. A process pool is the tool when the
work is CPU, not I/O.

```python file=n08.py
import asyncio


async def main():
    print(await asyncio.to_thread(sum, range(1000)))


asyncio.run(main())
```

```text output
499500
```

## `async for` and `async with` await inside the protocol

An async generator yields after awaits. `@asynccontextmanager` is the
async form of `with`: setup, `yield`, cleanup.

```python file=n09.py
import asyncio
from contextlib import asynccontextmanager


async def ticker(n):
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
    print([i async for i in ticker(3)])
    async with session() as s:
        print("using", s)


asyncio.run(main())
```

```text output
[0, 1, 2]
open
using s
close
```

## `gather` can return the exceptions

By default the first exception propagates and the other results are lost
to the caller. `return_exceptions=True` puts each exception in the list.

```python file=n10.py
import asyncio


async def fetch(name, delay):
    await asyncio.sleep(delay)
    return f"{name}:{delay}"


async def boom():
    raise ValueError("bad")


async def main():
    print(await asyncio.gather(fetch("ok", 0), boom(), return_exceptions=True))


asyncio.run(main())
```

```text output
['ok:0', ValueError('bad')]
```

## Call `asyncio.run` once, from outside

A second `asyncio.run` inside a running loop raises `RuntimeError`. The
one call at the bottom of the program is the entry point.

```python file=n11.py
import asyncio


async def nested():
    inner = asyncio.sleep(0)
    try:
        asyncio.run(inner)
    except RuntimeError as e:
        print(type(e).__name__)
    finally:
        inner.close()


asyncio.run(nested())
```

```text output
RuntimeError
```

## CPU work needs a process, not a thread

`asyncio.to_thread` still shares the GIL with the loop for Python
bytecode. A `ProcessPoolExecutor` runs the function in another process.
The worker has to be importable, so it is a named function at module
level, and the pool starts under `if __name__ == "__main__"`.

```python file=n12.py
from concurrent.futures import ProcessPoolExecutor


def square(n):
    return n * n


def main():
    with ProcessPoolExecutor(max_workers=2) as pool:
        print(list(pool.map(square, [2, 3, 4])))


if __name__ == "__main__":
    main()
```

```text output
[4, 9, 16]
```

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
