# Rust 16 — Network programming

TCP is the stream from the previous lesson with a peer attached.
`TcpStream` implements `Read` and `Write`. One `read` can return a single
byte of a frame, so a length prefix is the smallest protocol that survives
that. Bind `127.0.0.1` and port 0. The kernel picks a free port, and the
port changes every run, so these programs print the payload, not the
address. This is not TLS, HTTP/2, or `epoll`. Tokio is the async version of
the same design, and it needs Cargo. The file stays on `std::net` and
threads so `rustc` still builds it.

## A frame survives a short read

`read_exact` loops until the header and the body are both complete.
`write` is retried from the first byte that was not accepted. The server
uppercases the body and sends it back as another frame.

```rust file=n01.rs
use std::io::{self, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;

fn read_full(mut src: impl Read, n: usize) -> io::Result<Vec<u8>> {
    let mut buf = vec![0u8; n];
    src.read_exact(&mut buf)?;
    Ok(buf)
}

fn read_frame(src: &mut impl Read) -> io::Result<Vec<u8>> {
    let header = read_full(&mut *src, 4)?;
    let n = u32::from_be_bytes(header.as_slice().try_into().unwrap()) as usize;
    read_full(src, n)
}

fn write_all_retry(dst: &mut impl Write, mut buf: &[u8]) -> io::Result<()> {
    while !buf.is_empty() {
        let n = dst.write(buf)?;
        if n == 0 {
            return Err(io::Error::new(io::ErrorKind::WriteZero, "short write"));
        }
        buf = &buf[n..];
    }
    Ok(())
}

fn frame(payload: &[u8]) -> Vec<u8> {
    let mut out = (payload.len() as u32).to_be_bytes().to_vec();
    out.extend_from_slice(payload);
    out
}

fn main() -> io::Result<()> {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let addr = listener.local_addr()?;
    let server = thread::spawn(move || -> io::Result<()> {
        let (mut conn, _) = listener.accept()?;
        let msg = read_frame(&mut conn)?;
        let up: Vec<u8> = msg.iter().map(|b| b.to_ascii_uppercase()).collect();
        write_all_retry(&mut conn, &frame(&up))?;
        Ok(())
    });
    let mut c = TcpStream::connect(addr)?;
    write_all_retry(&mut c, &frame(b"ping"))?;
    let msg = read_frame(&mut c)?;
    println!("frame {}", String::from_utf8_lossy(&msg));
    drop(c);
    server.join().unwrap()?;
    Ok(())
}
```

```text output
frame PING
```

## A timeout is not a closed peer

The server accepts and then waits. The client gives the read 150
milliseconds. On Rust, `set_read_timeout` usually surfaces as
`ErrorKind::WouldBlock`, not `TimedOut`. Treat both as a timeout. Drop your
side afterwards. The timeout does not cancel the server: an accept loop
that stays in the connection you abandoned is stuck. Closing the socket is
what lets it proceed.

```rust file=n02.rs
use std::io::{self, Read};
use std::net::{TcpListener, TcpStream};
use std::thread;
use std::time::Duration;

fn read_full(mut src: impl Read, n: usize) -> io::Result<Vec<u8>> {
    let mut buf = vec![0u8; n];
    src.read_exact(&mut buf)?;
    Ok(buf)
}

fn read_frame(src: &mut impl Read) -> io::Result<Vec<u8>> {
    let header = read_full(&mut *src, 4)?;
    let n = u32::from_be_bytes(header.as_slice().try_into().unwrap()) as usize;
    read_full(src, n)
}

fn main() -> io::Result<()> {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let addr = listener.local_addr()?;
    let server = thread::spawn(move || -> io::Result<()> {
        let (mut conn, _) = listener.accept()?;
        conn.set_read_timeout(Some(Duration::from_secs(2)))?;
        let mut b = [0u8; 1];
        let _ = conn.read(&mut b);
        Ok(())
    });
    let mut c = TcpStream::connect(addr)?;
    c.set_read_timeout(Some(Duration::from_millis(150)))?;
    match read_frame(&mut c) {
        Err(e) if e.kind() == io::ErrorKind::TimedOut || e.kind() == io::ErrorKind::WouldBlock => {
            println!("timeout")
        }
        other => println!("unexpected {other:?}"),
    }
    drop(c);
    server.join().unwrap()?;
    Ok(())
}
```

```text output
timeout
```

## A peer that closes mid-frame is `UnexpectedEof`

Two bytes are not a four-byte header. That is a different error from the
timeout. The server writes them and returns. The client's `read_exact`
stops because the stream ended.

```rust file=n03.rs
use std::io::{self, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;

fn read_full(mut src: impl Read, n: usize) -> io::Result<Vec<u8>> {
    let mut buf = vec![0u8; n];
    src.read_exact(&mut buf)?;
    Ok(buf)
}

fn read_frame(src: &mut impl Read) -> io::Result<Vec<u8>> {
    let header = read_full(&mut *src, 4)?;
    let n = u32::from_be_bytes(header.as_slice().try_into().unwrap()) as usize;
    read_full(src, n)
}

fn main() -> io::Result<()> {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    let addr = listener.local_addr()?;
    let server = thread::spawn(move || -> io::Result<()> {
        let (mut conn, _) = listener.accept()?;
        let _ = conn.write(&[0, 0]);
        Ok(())
    });
    let mut c = TcpStream::connect(addr)?;
    match read_frame(&mut c) {
        Err(e) if e.kind() == io::ErrorKind::UnexpectedEof => println!("truncated"),
        other => println!("unexpected {other:?}"),
    }
    drop(c);
    server.join().unwrap()?;
    Ok(())
}
```

```text output
truncated
```

## HTTP/1.1 is the same bytes plus headers

The standard library has no HTTP client. The request below is written by
hand. `Content-Length` says when the body ends. `Connection: close` is the
other signal. A blank line (`\r\n\r\n`) ends the headers. Go's `net/http`
and a hand-written request in C put the same bytes on the socket.

```rust file=n04.rs
use std::io::{self, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;

fn write_all_retry(dst: &mut impl Write, mut buf: &[u8]) -> io::Result<()> {
    while !buf.is_empty() {
        let n = dst.write(buf)?;
        if n == 0 {
            return Err(io::Error::new(io::ErrorKind::WriteZero, "short write"));
        }
        buf = &buf[n..];
    }
    Ok(())
}

fn main() -> io::Result<()> {
    let http_listener = TcpListener::bind("127.0.0.1:0")?;
    let http_addr = http_listener.local_addr()?;
    let http = thread::spawn(move || -> io::Result<()> {
        let (mut conn, _) = http_listener.accept()?;
        let mut req = Vec::new();
        let mut buf = [0u8; 256];
        loop {
            let n = conn.read(&mut buf)?;
            if n == 0 {
                break;
            }
            req.extend_from_slice(&buf[..n]);
            if req.windows(4).any(|w| w == b"\r\n\r\n") {
                break;
            }
        }
        let resp = b"HTTP/1.1 200 OK\r\nContent-Length: 7\r\nConnection: close\r\n\r\necho:hi";
        write_all_retry(&mut conn, resp)?;
        Ok(())
    });
    let mut c = TcpStream::connect(http_addr)?;
    let req = b"POST /echo HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: 2\r\nConnection: close\r\n\r\nhi";
    write_all_retry(&mut c, req)?;
    let mut resp = Vec::new();
    c.read_to_end(&mut resp)?;
    let body = resp.windows(4).position(|w| w == b"\r\n\r\n").map(|i| &resp[i + 4..]).unwrap();
    println!("http {}", String::from_utf8_lossy(body));
    http.join().unwrap()?;
    Ok(())
}
```

```text output
http echo:hi
```

## Exercises

The harness is a small server. You write the client: one framed exchange, a classifier that reports `timeout` or `truncated`, and an HTTP POST whose body you return. `WouldBlock` from a read timeout counts as a timeout.

```rust file=exercise.rs
#![allow(dead_code, unused_imports, unused_variables)]
use std::io::{self, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;
use std::time::Duration;

fn read_full(src: &mut impl Read, n: usize) -> io::Result<Vec<u8>> {
    let mut buf = vec![0u8; n];
    src.read_exact(&mut buf)?;
    Ok(buf)
}

fn read_frame(src: &mut impl Read) -> io::Result<Vec<u8>> {
    let header = read_full(src, 4)?;
    let n = u32::from_be_bytes(header.as_slice().try_into().unwrap()) as usize;
    read_full(src, n)
}

fn write_all_retry(dst: &mut impl Write, mut buf: &[u8]) -> io::Result<()> {
    while !buf.is_empty() {
        let n = dst.write(buf)?;
        if n == 0 {
            return Err(io::Error::new(io::ErrorKind::WriteZero, "short write"));
        }
        buf = &buf[n..];
    }
    Ok(())
}

fn frame(payload: &[u8]) -> Vec<u8> {
    let mut out = (payload.len() as u32).to_be_bytes().to_vec();
    out.extend_from_slice(payload);
    out
}

fn exchange(addr: &str, payload: &[u8]) -> io::Result<Vec<u8>> {
    let _ = (addr, payload);
    todo!()
}



fn classify(stream: &mut TcpStream) -> &'static str {
    let _ = stream;
    todo!()
}



fn http_body(addr: &str) -> io::Result<String> {
    let _ = addr;
    todo!()
}



fn check(label: &str, got: impl std::fmt::Debug, want: impl std::fmt::Debug) -> bool {
    let gs = format!("{got:?}");
    let ws = format!("{want:?}");
    if gs == ws {
        println!("PASS {label}");
        true
    } else {
        println!("FAIL {label}: got {gs}, want {ws}");
        false
    }
}

fn main() {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let server = thread::spawn(move || -> io::Result<()> {
        for mode in ["echo", "silent", "drop"] {
            let (mut conn, _) = listener.accept()?;
            match mode {
                "echo" => {
                    let msg = read_frame(&mut conn)?;
                    let up: Vec<u8> = msg.iter().map(|b| b.to_ascii_uppercase()).collect();
                    write_all_retry(&mut conn, &frame(&up))?;
                }
                "silent" => {
                    conn.set_read_timeout(Some(Duration::from_secs(2)))?;
                    let mut b = [0u8; 1];
                    let _ = conn.read(&mut b);
                }
                _ => {
                    let _ = conn.write(&[0, 0]);
                }
            }
        }
        Ok(())
    });

    let addr_s = addr.to_string();
    let msg = exchange(&addr_s, b"ping").unwrap();
    let mut ok = check("exchange", String::from_utf8(msg).unwrap(), "PING".to_string());

    let mut c = TcpStream::connect(addr).unwrap();
    ok &= check("timeout", classify(&mut c), "timeout");
    drop(c);
    let mut c = TcpStream::connect(addr).unwrap();
    ok &= check("truncated", classify(&mut c), "truncated");
    drop(c);
    server.join().unwrap().unwrap();

    let http_listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let http_addr = http_listener.local_addr().unwrap();
    let http = thread::spawn(move || -> io::Result<()> {
        let (mut conn, _) = http_listener.accept()?;
        let mut req = Vec::new();
        let mut buf = [0u8; 256];
        loop {
            let n = conn.read(&mut buf)?;
            if n == 0 {
                break;
            }
            req.extend_from_slice(&buf[..n]);
            if req.windows(4).any(|w| w == b"\r\n\r\n") {
                break;
            }
        }
        let resp = b"HTTP/1.1 200 OK\r\nContent-Length: 7\r\nConnection: close\r\n\r\necho:hi";
        write_all_retry(&mut conn, resp)?;
        Ok(())
    });
    ok &= check("http", http_body(&http_addr.to_string()).unwrap(), "echo:hi".to_string());
    http.join().unwrap().unwrap();
    if !ok {
        std::process::exit(1);
    }
}
```

<details><summary>Solution</summary>

```rust file=solution.rs
use std::io::{self, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;
use std::time::Duration;

fn read_full(src: &mut impl Read, n: usize) -> io::Result<Vec<u8>> {
    let mut buf = vec![0u8; n];
    src.read_exact(&mut buf)?;
    Ok(buf)
}

fn read_frame(src: &mut impl Read) -> io::Result<Vec<u8>> {
    let header = read_full(src, 4)?;
    let n = u32::from_be_bytes(header.as_slice().try_into().unwrap()) as usize;
    read_full(src, n)
}

fn write_all_retry(dst: &mut impl Write, mut buf: &[u8]) -> io::Result<()> {
    while !buf.is_empty() {
        let n = dst.write(buf)?;
        if n == 0 {
            return Err(io::Error::new(io::ErrorKind::WriteZero, "short write"));
        }
        buf = &buf[n..];
    }
    Ok(())
}

fn frame(payload: &[u8]) -> Vec<u8> {
    let mut out = (payload.len() as u32).to_be_bytes().to_vec();
    out.extend_from_slice(payload);
    out
}

fn exchange(addr: &str, payload: &[u8]) -> io::Result<Vec<u8>> {
    let mut c = TcpStream::connect(addr)?;
    write_all_retry(&mut c, &frame(payload))?;
    read_frame(&mut c)
}

fn classify(stream: &mut TcpStream) -> &'static str {
    stream.set_read_timeout(Some(Duration::from_millis(150))).unwrap();
    match read_frame(stream) {
        Err(e) if e.kind() == io::ErrorKind::TimedOut || e.kind() == io::ErrorKind::WouldBlock => "timeout",
        Err(e) if e.kind() == io::ErrorKind::UnexpectedEof => "truncated",
        Ok(_) => "ok",
        Err(_) => "error",
    }
}

fn http_body(addr: &str) -> io::Result<String> {
    let mut c = TcpStream::connect(addr)?;
    let req = b"POST /echo HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: 2\r\nConnection: close\r\n\r\nhi";
    write_all_retry(&mut c, req)?;
    let mut resp = Vec::new();
    c.read_to_end(&mut resp)?;
    let body = resp.windows(4).position(|w| w == b"\r\n\r\n").map(|i| &resp[i + 4..]).unwrap_or(b"");
    Ok(String::from_utf8_lossy(body).into_owned())
}

fn check(label: &str, got: impl std::fmt::Debug, want: impl std::fmt::Debug) -> bool {
    let gs = format!("{got:?}");
    let ws = format!("{want:?}");
    if gs == ws {
        println!("PASS {label}");
        true
    } else {
        println!("FAIL {label}: got {gs}, want {ws}");
        false
    }
}

fn main() {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let addr = listener.local_addr().unwrap();
    let server = thread::spawn(move || -> io::Result<()> {
        for mode in ["echo", "silent", "drop"] {
            let (mut conn, _) = listener.accept()?;
            match mode {
                "echo" => {
                    let msg = read_frame(&mut conn)?;
                    let up: Vec<u8> = msg.iter().map(|b| b.to_ascii_uppercase()).collect();
                    write_all_retry(&mut conn, &frame(&up))?;
                }
                "silent" => {
                    conn.set_read_timeout(Some(Duration::from_secs(2)))?;
                    let mut b = [0u8; 1];
                    let _ = conn.read(&mut b);
                }
                _ => {
                    let _ = conn.write(&[0, 0]);
                }
            }
        }
        Ok(())
    });

    let addr_s = addr.to_string();
    let msg = exchange(&addr_s, b"ping").unwrap();
    let mut ok = check("exchange", String::from_utf8(msg).unwrap(), "PING".to_string());

    let mut c = TcpStream::connect(addr).unwrap();
    ok &= check("timeout", classify(&mut c), "timeout");
    drop(c);
    let mut c = TcpStream::connect(addr).unwrap();
    ok &= check("truncated", classify(&mut c), "truncated");
    drop(c);
    server.join().unwrap().unwrap();

    let http_listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let http_addr = http_listener.local_addr().unwrap();
    let http = thread::spawn(move || -> io::Result<()> {
        let (mut conn, _) = http_listener.accept()?;
        let mut req = Vec::new();
        let mut buf = [0u8; 256];
        loop {
            let n = conn.read(&mut buf)?;
            if n == 0 {
                break;
            }
            req.extend_from_slice(&buf[..n]);
            if req.windows(4).any(|w| w == b"\r\n\r\n") {
                break;
            }
        }
        let resp = b"HTTP/1.1 200 OK\r\nContent-Length: 7\r\nConnection: close\r\n\r\necho:hi";
        write_all_retry(&mut conn, resp)?;
        Ok(())
    });
    ok &= check("http", http_body(&http_addr.to_string()).unwrap(), "echo:hi".to_string());
    http.join().unwrap().unwrap();
    if !ok {
        std::process::exit(1);
    }
}
```

</details>

Next: [17 — Advanced concurrency](17-advanced-concurrency.md)
