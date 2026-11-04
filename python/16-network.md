# Python 16 — Network programming

TCP gives you a stream of bytes, with a peer on the other end. Bind
`127.0.0.1` and port `0` and the kernel picks a free port. A length-prefixed
frame is the smallest protocol that survives a short read. HTTP/1.1 is that
idea plus text headers. `asyncio` streams are the same reads, scheduled on
one thread. Nothing here is TLS, HTTP/2, or a public address. Those sit on
this loop. `requests` is a third-party wrapper around it, and it blocks the
asyncio loop.

## One byte is a successful read

`recv` returns what has arrived. Ask for one byte and you get one byte
even when more is already queued. `b""` means the peer closed. That is a
clean end only when you have not already started a frame.

```python file=n01.py
import socket

a, b = socket.socketpair()
b.sendall(b"xy")
print(a.recv(1), a.recv(8))
b.close()
print(repr(a.recv(8)))
a.close()
```

```text output
b'x' b'y'
b''
```

## Loop until the frame is complete

The header is a big-endian `uint32` length of the body. `read_full` keeps
calling `recv` until it has that many bytes. A split send still decodes
as one payload.

```python file=n02.py
import socket
import struct


def frame(payload):
    return struct.pack(">I", len(payload)) + payload


def read_full(sock, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            if not buf:
                return None
            raise EOFError(f"got {len(buf)} of {n}")
        buf += chunk
    return bytes(buf)


def read_frame(sock):
    header = read_full(sock, 4)
    if header is None:
        return None
    (n,) = struct.unpack(">I", header)
    body = read_full(sock, n)
    if body is None:
        raise EOFError("truncated frame")
    return body


a, b = socket.socketpair()
raw = frame(b"hello")
b.sendall(raw[:1])
b.sendall(raw[1:])
print(read_frame(a))
b.close()
print(read_frame(a))
a.close()
```

```text output
b'hello'
None
```

## Bind port 0 and echo one frame

The kernel chooses the port. The server reads one frame and writes it
back in upper case. The client speaks the same framing.

```python file=n03.py
import socket
import struct
import threading


def frame(payload):
    return struct.pack(">I", len(payload)) + payload


def read_full(sock, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            if not buf:
                return None
            raise EOFError(f"got {len(buf)} of {n}")
        buf += chunk
    return bytes(buf)


def read_frame(sock):
    header = read_full(sock, 4)
    if header is None:
        return None
    (n,) = struct.unpack(">I", header)
    body = read_full(sock, n)
    if body is None:
        raise EOFError("truncated frame")
    return body


def serve(port_out):
    ls = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ls.bind(("127.0.0.1", 0))
    ls.listen()
    port_out.append(ls.getsockname()[1])
    conn, _ = ls.accept()
    try:
        conn.sendall(frame(read_frame(conn).upper()))
    finally:
        conn.close()
        ls.close()


port_out = []
thread = threading.Thread(target=serve, args=(port_out,))
thread.start()
while not port_out:
    pass
sock = socket.create_connection(("127.0.0.1", port_out[0]), timeout=2)
sock.sendall(frame(b"ping"))
print("frame", read_frame(sock).decode())
sock.close()
thread.join()
```

```text output
frame PING
```

## A timeout does not cancel the server

`settimeout` raises `TimeoutError`, which is an `OSError`. The server is
still blocked in the connection you abandoned until you close your
socket. The next client can then be served.

```python file=n04.py
import socket
import struct
import threading


def frame(payload):
    return struct.pack(">I", len(payload)) + payload


def read_full(sock, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            if not buf:
                return None
            raise EOFError(f"got {len(buf)} of {n}")
        buf += chunk
    return bytes(buf)


def read_frame(sock):
    header = read_full(sock, 4)
    if header is None:
        return None
    (n,) = struct.unpack(">I", header)
    return read_full(sock, n)


def serve(port_out):
    ls = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ls.bind(("127.0.0.1", 0))
    ls.listen()
    port_out.append(ls.getsockname()[1])
    for mode in ("silent", "echo"):
        conn, _ = ls.accept()
        try:
            if mode == "silent":
                conn.settimeout(2)
                try:
                    conn.recv(1)
                except OSError:
                    pass
            else:
                conn.sendall(frame(read_frame(conn).upper()))
        finally:
            conn.close()
    ls.close()


port_out = []
thread = threading.Thread(target=serve, args=(port_out,))
thread.start()
while not port_out:
    pass
port = port_out[0]
sock = socket.create_connection(("127.0.0.1", port), timeout=2)
sock.settimeout(0.15)
try:
    print(read_frame(sock))
except TimeoutError:
    print("timeout", issubclass(TimeoutError, OSError))
sock.close()
sock = socket.create_connection(("127.0.0.1", port), timeout=2)
sock.sendall(frame(b"ping"))
print("still", read_frame(sock).decode())
sock.close()
thread.join()
```

```text output
timeout True
still PING
```

## A short header is not a timeout and not a clean end

The peer closed after two bytes of a four-byte header. `read_full` raises
`EOFError`. A close before any byte of the next frame is the `None` that
means "no more frames".

```python file=n05.py
import socket
import struct
import threading


def read_full(sock, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            if not buf:
                return None
            raise EOFError(f"got {len(buf)} of {n}")
        buf += chunk
    return bytes(buf)


def read_frame(sock):
    header = read_full(sock, 4)
    if header is None:
        return None
    (n,) = struct.unpack(">I", header)
    body = read_full(sock, n)
    if body is None:
        raise EOFError("truncated frame")
    return body


def serve(port_out):
    ls = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ls.bind(("127.0.0.1", 0))
    ls.listen()
    port_out.append(ls.getsockname()[1])
    for mode in ("drop", "close"):
        conn, _ = ls.accept()
        try:
            if mode == "drop":
                conn.sendall(b"\x00\x00")
        finally:
            conn.close()
    ls.close()


port_out = []
thread = threading.Thread(target=serve, args=(port_out,))
thread.start()
while not port_out:
    pass
port = port_out[0]
sock = socket.create_connection(("127.0.0.1", port), timeout=2)
try:
    print(read_frame(sock))
except EOFError as e:
    print("truncated", e)
sock.close()
sock = socket.create_connection(("127.0.0.1", port), timeout=2)
print("clean", read_frame(sock))
sock.close()
thread.join()
```

```text output
truncated got 2 of 4
clean None
```

## HTTP is a frame with text headers

`ThreadingHTTPServer` and `urllib` write the bytes. The handler reads
`Content-Length` bytes and answers with its own length. `log_message`
prints to stderr by default; silence it when stdout is the result.

```python file=n06.py
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(n)
        out = b"echo:" + body
        self.send_response(200)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, fmt, *args):
        return


httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
http_thread = threading.Thread(target=httpd.serve_forever)
http_thread.start()
req = urllib.request.Request(
    f"http://127.0.0.1:{httpd.server_address[1]}/echo",
    data=b"hi",
    method="POST",
)
with urllib.request.urlopen(req, timeout=2) as resp:
    print("http", resp.status, resp.read().decode())
httpd.shutdown()
httpd.server_close()
http_thread.join()
```

```text output
http 200 echo:hi
```

## `readexactly` is `read_full` on an asyncio stream

The server and the client use the same length prefix. `StreamReader` and
`StreamWriter` are the socket, scheduled instead of blocked.

```python file=n07.py
import asyncio
import struct


def frame(payload):
    return struct.pack(">I", len(payload)) + payload


async def handle(reader, writer):
    n = int.from_bytes(await reader.readexactly(4), "big")
    body = await reader.readexactly(n)
    writer.write(frame(body.upper()))
    await writer.drain()
    writer.close()
    await writer.wait_closed()


async def main():
    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(frame(b"async"))
    await writer.drain()
    n = int.from_bytes(await reader.readexactly(4), "big")
    body = await reader.readexactly(n)
    print("async", body.decode())
    writer.close()
    await writer.wait_closed()
    server.close()
    await server.wait_closed()


asyncio.run(main())
```

```text output
async ASYNC
```

## Exercises

The harness is a small server. You write the client: one framed
exchange, a frame reader that surfaces timeout and truncation, and an
HTTP POST whose body you return.

```python file=exercise.py
import socket
import struct
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def frame(payload):
    return struct.pack(">I", len(payload)) + payload


def read_full(sock, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            if not buf:
                return None
            raise EOFError(f"got {len(buf)} of {n}")
        buf += chunk
    return bytes(buf)


def recv_frame(sock):
    """One length-prefixed frame. Raise EOFError if the peer closes early.
    A socket timeout propagates as TimeoutError."""
    raise NotImplementedError


def exchange(host, port, payload):
    """Connect to host:port, send one frame, return the response frame, close."""
    raise NotImplementedError


def post_body(host, port, payload):
    """HTTP/1.1 POST payload to http://host:port/echo. Return (status, body)."""
    raise NotImplementedError


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(n)
        out = b"echo:" + body
        self.send_response(200)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, fmt, *args):
        return


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


def serve_frames(modes):
    ls = socket.socket()
    ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ls.bind(("127.0.0.1", 0))
    ls.listen()
    ls.settimeout(2)

    def loop():
        for mode in modes:
            try:
                conn, _ = ls.accept()
            except OSError:
                return
            try:
                if mode == "echo":
                    msg = recv_frame(conn)
                    conn.sendall(frame(msg.upper()))
                elif mode == "drop":
                    conn.sendall(b"\x00\x00")
                else:
                    conn.settimeout(2)
                    try:
                        conn.recv(1)
                    except OSError:
                        pass
            finally:
                conn.close()

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return ls, t


def run():
    out = []
    ls, thread = serve_frames(["echo", "silent", "drop"])
    port = ls.getsockname()[1]
    try:
        out.append(check("exchange", exchange("127.0.0.1", port, b"ping"), b"PING"))
        sock = socket.create_connection(("127.0.0.1", port), timeout=2)
        sock.settimeout(0.15)
        try:
            recv_frame(sock)
            out.append(check("timeout", "no error", "TimeoutError"))
        except TimeoutError:
            out.append(check("timeout", "TimeoutError", "TimeoutError"))
        finally:
            sock.close()
        sock = socket.create_connection(("127.0.0.1", port), timeout=2)
        try:
            recv_frame(sock)
            out.append(check("truncated", "no error", "EOFError"))
        except EOFError:
            out.append(check("truncated", "EOFError", "EOFError"))
        finally:
            sock.close()
    finally:
        ls.close()
        thread.join(timeout=2)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    ht = threading.Thread(target=httpd.serve_forever, daemon=True)
    ht.start()
    try:
        status, body = post_body("127.0.0.1", httpd.server_address[1], b"hi")
        out.append(check("http", (status, body), (200, b"echo:hi")))
    finally:
        httpd.shutdown()
        httpd.server_close()
        ht.join(timeout=2)
    return out


raise SystemExit(0 if all(run()) else 1)
```

<details><summary>Solution</summary>

```python file=solution.py
import socket
import struct
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def frame(payload):
    return struct.pack(">I", len(payload)) + payload


def read_full(sock, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            if not buf:
                return None
            raise EOFError(f"got {len(buf)} of {n}")
        buf += chunk
    return bytes(buf)


def recv_frame(sock):
    header = read_full(sock, 4)
    if header is None:
        raise EOFError("closed before frame")
    (n,) = struct.unpack(">I", header)
    body = read_full(sock, n)
    if body is None:
        raise EOFError("truncated frame")
    return body


def exchange(host, port, payload):
    sock = socket.create_connection((host, port), timeout=2)
    try:
        sock.sendall(frame(payload))
        return recv_frame(sock)
    finally:
        sock.close()


def post_body(host, port, payload):
    req = urllib.request.Request(
        f"http://{host}:{port}/echo", data=payload, method="POST"
    )
    with urllib.request.urlopen(req, timeout=2) as resp:
        return resp.status, resp.read()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(n)
        out = b"echo:" + body
        self.send_response(200)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, fmt, *args):
        return


def check(label, got, want):
    ok = got == want
    print(("PASS " if ok else "FAIL ") + label, "" if ok else f"got {got!r}, want {want!r}")
    return ok


def serve_frames(modes):
    ls = socket.socket()
    ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ls.bind(("127.0.0.1", 0))
    ls.listen()
    ls.settimeout(2)

    def loop():
        for mode in modes:
            try:
                conn, _ = ls.accept()
            except OSError:
                return
            try:
                if mode == "echo":
                    msg = recv_frame(conn)
                    conn.sendall(frame(msg.upper()))
                elif mode == "drop":
                    conn.sendall(b"\x00\x00")
                else:
                    conn.settimeout(2)
                    try:
                        conn.recv(1)
                    except OSError:
                        pass
            finally:
                conn.close()

    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return ls, t


def run():
    out = []
    ls, thread = serve_frames(["echo", "silent", "drop"])
    port = ls.getsockname()[1]
    try:
        out.append(check("exchange", exchange("127.0.0.1", port, b"ping"), b"PING"))
        sock = socket.create_connection(("127.0.0.1", port), timeout=2)
        sock.settimeout(0.15)
        try:
            recv_frame(sock)
            out.append(check("timeout", "no error", "TimeoutError"))
        except TimeoutError:
            out.append(check("timeout", "TimeoutError", "TimeoutError"))
        finally:
            sock.close()
        sock = socket.create_connection(("127.0.0.1", port), timeout=2)
        try:
            recv_frame(sock)
            out.append(check("truncated", "no error", "EOFError"))
        except EOFError:
            out.append(check("truncated", "EOFError", "EOFError"))
        finally:
            sock.close()
    finally:
        ls.close()
        thread.join(timeout=2)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    ht = threading.Thread(target=httpd.serve_forever, daemon=True)
    ht.start()
    try:
        status, body = post_body("127.0.0.1", httpd.server_address[1], b"hi")
        out.append(check("http", (status, body), (200, b"echo:hi")))
    finally:
        httpd.shutdown()
        httpd.server_close()
        ht.join(timeout=2)
    return out


raise SystemExit(0 if all(run()) else 1)
```

</details>

Next: [17 — Advanced concurrency](17-advanced-concurrency.md)
