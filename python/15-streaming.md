# Python 15 — Streaming

A file, a pipe, and a socket are the same kind of object: a stream of bytes
that arrives in pieces. `read(n)` may return fewer than `n` bytes.
`write(buf)` may accept fewer than you offered. Load a whole file only when
you know it is small. Everything else is a loop.

## A short read is normal

The reader below returns at most two bytes, the way a socket does. End of
stream is a zero-length read, not a short one.

```python file=n01.py
class ShortReader:
    def __init__(self, data, limit):
        self.data = data
        self.limit = limit
        self.i = 0

    def read(self, n=-1):
        if self.i >= len(self.data):
            return b""
        if n is None or n < 0:
            n = len(self.data)
        take = min(n, self.limit, len(self.data) - self.i)
        chunk = self.data[self.i:self.i + take]
        self.i += take
        return chunk


src = ShortReader(b"hello", 2)
print(src.read(8), src.read(8), src.read(8), src.read(8))
```

```text output
b'he' b'll' b'o' b''
```

## A short write has to be retried

`write` returns how many bytes it accepted. Continue from the first byte
it did not take. Treating "I called write" as "the bytes are gone" corrupts
the next frame. `BufferedWriter` and `shutil.copyfileobj` are this loop.
Call `flush` and check it: a buffer dropped on the floor hides a full disk.

```python file=n02.py
class ShortReader:
    def __init__(self, data, limit):
        self.data = data
        self.limit = limit
        self.i = 0
        self.reads = 0

    def read(self, n=-1):
        self.reads += 1
        if self.i >= len(self.data):
            return b""
        if n is None or n < 0:
            n = len(self.data)
        take = min(n, self.limit, len(self.data) - self.i)
        chunk = self.data[self.i:self.i + take]
        self.i += take
        return chunk


class ShortWriter:
    def __init__(self, limit):
        self.buf = bytearray()
        self.limit = limit
        self.writes = 0

    def write(self, b):
        self.writes += 1
        n = min(len(b), self.limit)
        self.buf += bytes(b[:n])
        return n


def copy_chunks(src, dst, size):
    total = 0
    while True:
        buf = src.read(size)
        if not buf:
            return total
        view = memoryview(buf)
        off = 0
        while off < len(view):
            n = dst.write(view[off:])
            if not n:
                raise BlockingIOError("writer accepted nothing")
            off += n
            total += n


src = ShortReader(b"hello world", 3)
dst = ShortWriter(2)
print(copy_chunks(src, dst, 8), src.reads, dst.writes, bytes(dst.buf))
```

```text output
11 5 7 b'hello world'
```

## `flush` publishes the buffer

A `BufferedWriter` holds bytes until it is full or you flush. Until then
the underlying stream is still empty.

```python file=n03.py
import io

raw = io.BytesIO()
wrapped = io.BufferedWriter(raw, buffer_size=64)
wrapped.write(b"hello")
print("before", raw.getvalue())
wrapped.flush()
print("after", raw.getvalue())
```

```text output
before b''
after b'hello'
```

## Read exactly `n`, or say the stream ended

`None` means a clean end before any byte of this read. A zero-length read
after some bytes of a fixed header is a truncated value: raise, and do
not return a partial payload.

```python file=n04.py
class ShortReader:
    def __init__(self, data, limit):
        self.data = data
        self.limit = limit
        self.i = 0

    def read(self, n=-1):
        if self.i >= len(self.data):
            return b""
        if n is None or n < 0:
            n = len(self.data)
        take = min(n, self.limit, len(self.data) - self.i)
        chunk = self.data[self.i:self.i + take]
        self.i += take
        return chunk


def read_full(src, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = src.read(n - len(buf))
        if not chunk:
            if not buf:
                return None
            raise EOFError(f"truncated: got {len(buf)} of {n}")
        buf += chunk
    return bytes(buf)


print(read_full(ShortReader(b"abcdef", 2), 5))
print(read_full(ShortReader(b"", 2), 4))
try:
    read_full(ShortReader(b"xy", 2), 4)
except EOFError as e:
    print(e)
```

```text output
b'abcde'
None
truncated: got 2 of 4
```

## A frame is a length, then that many bytes

The length is a big-endian `uint32` of the body, so a writer in another
language can read it. A clean end before the header is `None`. Two header
bytes and then a zero-length read is `EOFError`, not a payload.

```python file=n05.py
class ShortReader:
    def __init__(self, data, limit):
        self.data = data
        self.limit = limit
        self.i = 0

    def read(self, n=-1):
        if self.i >= len(self.data):
            return b""
        if n is None or n < 0:
            n = len(self.data)
        take = min(n, self.limit, len(self.data) - self.i)
        chunk = self.data[self.i:self.i + take]
        self.i += take
        return chunk


def read_full(src, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = src.read(n - len(buf))
        if not chunk:
            if not buf:
                return None
            raise EOFError(f"truncated: got {len(buf)} of {n}")
        buf += chunk
    return bytes(buf)


def encode_frame(payload):
    return len(payload).to_bytes(4, "big") + payload


def read_frame(src):
    header = read_full(src, 4)
    if header is None:
        return None
    n = int.from_bytes(header, "big")
    body = read_full(src, n)
    if body is None:
        raise EOFError("truncated frame")
    return body


print(read_frame(ShortReader(b"", 3)))
stream = ShortReader(encode_frame(b"hello") + encode_frame(b"world") + b"\x00\x00", 3)
print(read_frame(stream), read_frame(stream))
try:
    read_frame(stream)
except EOFError as e:
    print(type(e).__name__)
```

```text output
None
b'hello' b'world'
EOFError
```

## Refuse a length you will not allocate

The header is a number the peer chose. Check it before you build a buffer
of that size.

```python file=n06.py
def checked_len(header, limit):
    n = int.from_bytes(header, "big")
    if n > limit:
        raise ValueError(f"frame of {n} exceeds {limit}")
    return n


print(checked_len((5).to_bytes(4, "big"), 1024))
try:
    checked_len((5000).to_bytes(4, "big"), 1024)
except ValueError as e:
    print(e)
```

```text output
5
frame of 5000 exceeds 1024
```

## Replace the file in the directory it lives in

`os.replace` is atomic when the temp file is on the same filesystem as
the destination. Create the temp file there. A crash leaves the old file
or the new one.

```python file=n07.py
import os
import tempfile
from pathlib import Path


def atomic_write(path, data):
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "notes.txt"
    atomic_write(p, b"hello\n")
    print(p.name, p.read_bytes(), list(Path(d).iterdir()) == [p])
```

```text output
notes.txt b'hello\n' True
```

## A pipe is the same read

Write a frame, close the write end so the reader sees end of stream, and
decode it with the same function a file would use.

```python file=n08.py
import os


def read_full(src, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = src.read(n - len(buf))
        if not chunk:
            if not buf:
                return None
            raise EOFError(f"truncated: got {len(buf)} of {n}")
        buf += chunk
    return bytes(buf)


def read_frame(src):
    header = read_full(src, 4)
    if header is None:
        return None
    n = int.from_bytes(header, "big")
    body = read_full(src, n)
    if body is None:
        raise EOFError("truncated frame")
    return body


def encode_frame(payload):
    return len(payload).to_bytes(4, "big") + payload


r, w = os.pipe()
os.write(w, encode_frame(b"via-pipe"))
os.close(w)
print(read_frame(os.fdopen(r, "rb")))
```

```text output
b'via-pipe'
```

## A line loop still holds one line

`for line in file` is the line-shaped version of the same idea. The line
can be longer than you hoped, and the whole line is in memory at once.

```python file=n09.py
import io

text = io.StringIO("one\ntwo\n")
print([line.rstrip("\n") for line in text])
```

```text output
['one', 'two']
```

## Exercises

`ShortReader` and `ShortWriter` are the test's stand-in for a socket.
Copy through them, decode length-prefixed frames, and publish a file by
replacing it.

```python file=exercise.py
import os
import tempfile
from pathlib import Path


class ShortReader:
    """Test double: each read returns at most `limit` bytes."""

    def __init__(self, data, limit):
        self.data = data
        self.limit = limit
        self.i = 0

    def read(self, n=-1):
        if self.i >= len(self.data):
            return b""
        if n is None or n < 0:
            n = len(self.data)
        take = min(n, self.limit, len(self.data) - self.i)
        chunk = self.data[self.i:self.i + take]
        self.i += take
        return chunk


class ShortWriter:
    """Test double: each write accepts at most `limit` bytes."""

    def __init__(self, limit):
        self.buf = bytearray()
        self.limit = limit

    def write(self, b):
        n = min(len(b), self.limit)
        self.buf += bytes(b[:n])
        return n


def copy_chunks(src, dst, size):
    """Copy src to dst, reading at most `size` bytes at a time.

    Retry short writes. Return the number of bytes copied.
    """
    raise NotImplementedError


def read_frame(src):
    """One big-endian uint32 length-prefixed frame.

    Return the payload, None on a clean EOF before the header, and raise
    EOFError if the header or the body is cut short.
    """
    raise NotImplementedError


def atomic_write(path, data):
    """Write data to path by writing a temp file in the same directory and
    replacing the destination. Leave no temp file behind."""
    raise NotImplementedError


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


def frame(payload):
    return len(payload).to_bytes(4, "big") + payload


def run():
    src = ShortReader(b"hello world", 3)
    dst = ShortWriter(2)
    out = [check("copy", (copy_chunks(src, dst, 8), bytes(dst.buf)), (11, b"hello world"))]
    stream = ShortReader(frame(b"hello") + frame(b"world"), 3)
    out.append(check("frames", (read_frame(stream), read_frame(stream), read_frame(stream)), (b"hello", b"world", None)))
    bad = ShortReader(frame(b"hello") + b"\x00\x00", 1)
    read_frame(bad)
    try:
        read_frame(bad)
        out.append(check("truncated", "no error", "EOFError"))
    except EOFError:
        out.append(check("truncated", "EOFError", "EOFError"))
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "notes.txt"
        atomic_write(p, b"hello")
        names = sorted(q.name for q in Path(d).iterdir())
        out.append(check("atomic", (p.read_bytes(), names), (b"hello", ["notes.txt"])))
    return out


raise SystemExit(0 if all(run()) else 1)
```

<details><summary>Solution</summary>

```python file=solution.py
import os
import tempfile
from pathlib import Path


class ShortReader:
    def __init__(self, data, limit):
        self.data = data
        self.limit = limit
        self.i = 0

    def read(self, n=-1):
        if self.i >= len(self.data):
            return b""
        if n is None or n < 0:
            n = len(self.data)
        take = min(n, self.limit, len(self.data) - self.i)
        chunk = self.data[self.i:self.i + take]
        self.i += take
        return chunk


class ShortWriter:
    def __init__(self, limit):
        self.buf = bytearray()
        self.limit = limit

    def write(self, b):
        n = min(len(b), self.limit)
        self.buf += bytes(b[:n])
        return n


def copy_chunks(src, dst, size):
    total = 0
    while True:
        buf = src.read(size)
        if not buf:
            return total
        view = memoryview(buf)
        off = 0
        while off < len(view):
            n = dst.write(view[off:])
            if not n:
                raise BlockingIOError("writer accepted nothing")
            off += n
            total += n


def read_full(src, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = src.read(n - len(buf))
        if not chunk:
            if not buf:
                return None
            raise EOFError(f"truncated: got {len(buf)} of {n}")
        buf += chunk
    return bytes(buf)


def read_frame(src):
    header = read_full(src, 4)
    if header is None:
        return None
    n = int.from_bytes(header, "big")
    body = read_full(src, n)
    if body is None:
        raise EOFError("truncated frame")
    return body


def atomic_write(path, data):
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


def frame(payload):
    return len(payload).to_bytes(4, "big") + payload


def run():
    src = ShortReader(b"hello world", 3)
    dst = ShortWriter(2)
    out = [check("copy", (copy_chunks(src, dst, 8), bytes(dst.buf)), (11, b"hello world"))]
    stream = ShortReader(frame(b"hello") + frame(b"world"), 3)
    out.append(check("frames", (read_frame(stream), read_frame(stream), read_frame(stream)), (b"hello", b"world", None)))
    bad = ShortReader(frame(b"hello") + b"\x00\x00", 1)
    read_frame(bad)
    try:
        read_frame(bad)
        out.append(check("truncated", "no error", "EOFError"))
    except EOFError:
        out.append(check("truncated", "EOFError", "EOFError"))
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "notes.txt"
        atomic_write(p, b"hello")
        names = sorted(q.name for q in Path(d).iterdir())
        out.append(check("atomic", (p.read_bytes(), names), (b"hello", ["notes.txt"])))
    return out


raise SystemExit(0 if all(run()) else 1)
```

</details>

Next: [16 — Network programming](16-network.md)
