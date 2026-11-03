# Python 15 — Streaming

A file, a pipe and a socket are the same kind of object: a stream of
bytes that arrives in pieces. `read(n)` may return fewer than `n` bytes.
`write(buf)` may accept fewer than you offered. Load a whole file only when
you know it is small. Everything else is a loop.

## Example

```python file=example.py
import io
import os
import tempfile
from pathlib import Path


class ShortReader(io.RawIOBase):
    """Each read returns at most `limit` bytes, the way a socket does."""

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


class ShortWriter(io.RawIOBase):
    """Each write accepts at most `limit` bytes and reports the short count."""

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
    """Copy until EOF. A short write must be retried; a short read is normal."""
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
    """Exactly n bytes, or None on a clean EOF before any byte, else EOFError."""
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


def atomic_write(path, data):
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)  # same directory: atomic on POSIX


src = ShortReader(b"hello world", 3)
dst = ShortWriter(2)
print(copy_chunks(src, dst, 8), src.reads, dst.writes, bytes(dst.buf))

stream = ShortReader(encode_frame(b"hello") + encode_frame(b"world") + b"\x00\x00", 3)
print(read_frame(stream), read_frame(stream))
try:
    read_frame(stream)
except EOFError as e:
    print(type(e).__name__)

with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "notes.txt"
    atomic_write(p, b"hello\n")
    print(p.name, p.read_bytes(), list(Path(d).iterdir()) == [p])

r, w = os.pipe()
os.write(w, encode_frame(b"via-pipe"))
os.close(w)
print(read_frame(os.fdopen(r, "rb")))
```

```text output
11 5 7 b'hello world'
b'hello' b'world'
EOFError
notes.txt b'hello\n' True
b'via-pipe'
```

## Details that bite

- A short read is normal. End of stream is a **zero-length** read. Two
  bytes of a 4-byte header, then a zero-length read, is a truncated frame:
  raise, do not return a partial payload.
- A short write must be retried from the first byte the writer did not
  accept. Treating "I called write" as "the bytes are gone" corrupts the
  next frame.
- The length prefix is a big-endian `uint32` of the **body**, so a writer
  in another language can read it. Refuse a length you are not willing to
  allocate.
- `os.replace` (and `rename`) is atomic when the temp file is on the same
  filesystem as the destination. Create the temp file in the destination's
  directory, then replace. A crash leaves either the old file or the new
  one, not a half-written destination.
- `BufferedWriter` and `shutil.copyfileobj` are this loop. Call `flush`
  and check it; a buffer dropped on the floor hides a full disk.
- `for line in file` is the line-shaped version of the same idea. It still
  holds one line in memory, which is why lesson 10's `fgets` note exists
  in C: a line can be longer than you hoped.

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
