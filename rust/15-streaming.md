# Rust 15 — Streaming

A file, a pipe, and a socket are the same shape: something that implements
`Read` and `Write`. `read` may fill only part of the buffer. `write` may
accept only part of what you offered. End of stream is a zero-length read.
The loop below is what `std::io::copy` does. A pipe and a socket use it the
same way a file does.

## A short read and a short write are normal

`ShortReader` returns at most three bytes. `ShortWriter` accepts at most
two. The copy loop retries the write from the first byte the callee did
not take. "I called write" is not "those bytes are stored". A zero write
is an error (`WriteZero`), not success.

```rust file=n01.rs
use std::io::{self, Read, Write};

struct ShortReader<'a> {
    data: &'a [u8],
    limit: usize,
    i: usize,
    reads: usize,
}

impl Read for ShortReader<'_> {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
        self.reads += 1;
        if self.i >= self.data.len() {
            return Ok(0);
        }
        let n = buf.len().min(self.limit).min(self.data.len() - self.i);
        buf[..n].copy_from_slice(&self.data[self.i..self.i + n]);
        self.i += n;
        Ok(n)
    }
}

struct ShortWriter {
    buf: Vec<u8>,
    limit: usize,
    writes: usize,
}

impl Write for ShortWriter {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        self.writes += 1;
        let n = buf.len().min(self.limit);
        self.buf.extend_from_slice(&buf[..n]);
        Ok(n)
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

fn copy_chunks(src: &mut impl Read, dst: &mut impl Write, size: usize) -> io::Result<usize> {
    let mut buf = vec![0u8; size];
    let mut total = 0;
    loop {
        let n = src.read(&mut buf)?;
        if n == 0 {
            return Ok(total);
        }
        let mut off = 0;
        while off < n {
            let w = dst.write(&buf[off..n])?;
            if w == 0 {
                return Err(io::Error::new(io::ErrorKind::WriteZero, "short write"));
            }
            off += w;
            total += w;
        }
    }
}

fn main() -> io::Result<()> {
    let mut src = ShortReader { data: b"hello world", limit: 3, i: 0, reads: 0 };
    let mut dst = ShortWriter { buf: Vec::new(), limit: 2, writes: 0 };
    let n = copy_chunks(&mut src, &mut dst, 8)?;
    println!("{} {} {} {}", n, src.reads, dst.writes, String::from_utf8(dst.buf).unwrap());

    let mut src = ShortReader { data: b"hello world", limit: 3, i: 0, reads: 0 };
    let mut dst = ShortWriter { buf: Vec::new(), limit: 2, writes: 0 };
    let n = io::copy(&mut src, &mut dst)?;
    println!("{} {}", n, String::from_utf8(dst.buf).unwrap());
    Ok(())
}
```

```text output
11 5 7 hello world
11 hello world
```

## A frame is a length, then that many bytes

The length is a big-endian `u32` of the body, so the other languages in
this course can read the same bytes. Cap it before you allocate. A header
that stops after two of its four bytes is a truncated frame: fail it. Do
not return a partial payload. `Ok(None)` is only a clean end, before any
byte of the next frame.

```rust file=n02.rs
use std::io::{self, Read};

struct ShortReader<'a> {
    data: &'a [u8],
    limit: usize,
    i: usize,
}

impl Read for ShortReader<'_> {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
        if self.i >= self.data.len() {
            return Ok(0);
        }
        let n = buf.len().min(self.limit).min(self.data.len() - self.i);
        buf[..n].copy_from_slice(&self.data[self.i..self.i + n]);
        self.i += n;
        Ok(n)
    }
}

fn read_full(src: &mut impl Read, n: usize) -> io::Result<Option<Vec<u8>>> {
    let mut buf = vec![0u8; n];
    let mut got = 0;
    while got < n {
        match src.read(&mut buf[got..])? {
            0 if got == 0 => return Ok(None),
            0 => return Err(io::Error::new(io::ErrorKind::UnexpectedEof, "truncated")),
            k => got += k,
        }
    }
    Ok(Some(buf))
}

fn read_frame(src: &mut impl Read) -> io::Result<Option<Vec<u8>>> {
    let Some(header) = read_full(src, 4)? else {
        return Ok(None);
    };
    let n = u32::from_be_bytes(header.as_slice().try_into().unwrap()) as usize;
    if n > 32 {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "frame too large"));
    }
    match read_full(src, n)? {
        Some(body) => Ok(Some(body)),
        None => Err(io::Error::new(io::ErrorKind::UnexpectedEof, "truncated frame")),
    }
}

fn encode_frame(payload: &[u8]) -> Vec<u8> {
    let mut out = (payload.len() as u32).to_be_bytes().to_vec();
    out.extend_from_slice(payload);
    out
}

fn main() -> io::Result<()> {
    let mut raw = encode_frame(b"hello");
    raw.extend(encode_frame(b"world"));
    raw.extend_from_slice(&[0, 0]);
    let mut stream = ShortReader { data: &raw, limit: 3, i: 0 };
    let a = read_frame(&mut stream)?.unwrap();
    let b = read_frame(&mut stream)?.unwrap();
    let err = read_frame(&mut stream).unwrap_err();
    println!("{} {} {:?}", String::from_utf8(a).unwrap(), String::from_utf8(b).unwrap(), err.kind());

    let huge = 1000u32.to_be_bytes();
    let mut big = ShortReader { data: &huge, limit: 4, i: 0 };
    println!("{:?}", read_frame(&mut big).unwrap_err().kind());
    Ok(())
}
```

```text output
hello world UnexpectedEof
InvalidData
```

## Rename a temp file over the destination

Write the temporary in the same directory, then `rename`. On one filesystem
that replace is atomic. A buffered writer can still fail in `flush` or when
it is dropped, after `write` returned success, so check those errors too.
The directory listing afterwards contains only the destination.

```rust file=n03.rs
use std::fs;
use std::io::{self, Write};
use std::path::Path;

fn atomic_write(path: &Path, data: &[u8]) -> io::Result<()> {
    let mut name = path.file_name().unwrap().to_os_string();
    name.push(".tmp");
    let tmp = path.with_file_name(name);
    let mut f = fs::File::create(&tmp)?;
    f.write_all(data)?;
    f.flush()?;
    f.sync_all()?;
    fs::rename(&tmp, path)?;
    Ok(())
}

fn main() -> io::Result<()> {
    let dir = std::env::temp_dir().join(format!("ruststream{}", std::process::id()));
    fs::create_dir_all(&dir)?;
    let path = dir.join("notes.txt");
    atomic_write(&path, b"hello")?;
    let left = fs::read_dir(&dir)?.count();
    println!("notes.txt {} {}", fs::read_to_string(&path)?, left == 1);
    fs::remove_dir_all(&dir)?;
    Ok(())
}
```

```text output
notes.txt hello true
```

## A socket pair is the same loop

`UnixStream::pair` is a pipe with two ends. The writer sends one frame and
drops its end, which is end-of-stream for the reader. `read_frame` does not
care that the bytes came from a socket.

```rust file=n04.rs
use std::io::{self, Read, Write};
use std::os::unix::net::UnixStream;

fn read_full(src: &mut impl Read, n: usize) -> io::Result<Option<Vec<u8>>> {
    let mut buf = vec![0u8; n];
    let mut got = 0;
    while got < n {
        match src.read(&mut buf[got..])? {
            0 if got == 0 => return Ok(None),
            0 => return Err(io::Error::new(io::ErrorKind::UnexpectedEof, "truncated")),
            k => got += k,
        }
    }
    Ok(Some(buf))
}

fn read_frame(src: &mut impl Read) -> io::Result<Option<Vec<u8>>> {
    let Some(header) = read_full(src, 4)? else {
        return Ok(None);
    };
    let n = u32::from_be_bytes(header.as_slice().try_into().unwrap()) as usize;
    match read_full(src, n)? {
        Some(body) => Ok(Some(body)),
        None => Err(io::Error::new(io::ErrorKind::UnexpectedEof, "truncated frame")),
    }
}

fn encode_frame(payload: &[u8]) -> Vec<u8> {
    let mut out = (payload.len() as u32).to_be_bytes().to_vec();
    out.extend_from_slice(payload);
    out
}

fn main() -> io::Result<()> {
    let (mut here, mut there) = UnixStream::pair()?;
    there.write_all(&encode_frame(b"via-pipe"))?;
    drop(there);
    let frame = read_frame(&mut here)?.unwrap();
    println!("{}", String::from_utf8(frame).unwrap());
    Ok(())
}
```

```text output
via-pipe
```

## Exercises

`copy_chunks` must honour short reads and short writes. `read_frame` returns `Ok(None)` before a frame and `UnexpectedEof` when one is cut off. `atomic_write` leaves exactly the destination file behind.

```rust file=exercise.rs
#![allow(dead_code, unused_imports, unused_variables)]
use std::fs;
use std::io::{self, Read, Write};
use std::path::Path;

struct ShortReader<'a> {
    data: &'a [u8],
    limit: usize,
    i: usize,
}

impl Read for ShortReader<'_> {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
        if self.i >= self.data.len() {
            return Ok(0);
        }
        let n = buf.len().min(self.limit).min(self.data.len() - self.i);
        buf[..n].copy_from_slice(&self.data[self.i..self.i + n]);
        self.i += n;
        Ok(n)
    }
}

struct ShortWriter {
    buf: Vec<u8>,
    limit: usize,
}

impl Write for ShortWriter {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        let n = buf.len().min(self.limit);
        self.buf.extend_from_slice(&buf[..n]);
        Ok(n)
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

fn copy_chunks(src: &mut impl Read, dst: &mut impl Write, size: usize) -> io::Result<usize> {
    let _ = (src, dst, size);
    todo!()
}



fn read_full(src: &mut impl Read, n: usize) -> io::Result<Option<Vec<u8>>> {
    let mut buf = vec![0u8; n];
    let mut got = 0;
    while got < n {
        match src.read(&mut buf[got..])? {
            0 if got == 0 => return Ok(None),
            0 => return Err(io::Error::new(io::ErrorKind::UnexpectedEof, "truncated")),
            k => got += k,
        }
    }
    Ok(Some(buf))
}

fn read_frame(src: &mut impl Read) -> io::Result<Option<Vec<u8>>> {
    let _ = src;
    todo!()
}



fn atomic_write(path: &Path, data: &[u8]) -> io::Result<()> {
    let _ = (path, data);
    todo!()
}



fn frame(payload: &[u8]) -> Vec<u8> {
    let mut out = (payload.len() as u32).to_be_bytes().to_vec();
    out.extend_from_slice(payload);
    out
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

fn show(r: io::Result<Option<Vec<u8>>>) -> String {
    match r {
        Ok(Some(b)) => format!("some:{}", String::from_utf8_lossy(&b)),
        Ok(None) => "none".into(),
        Err(e) => format!("{:?}", e.kind()),
    }
}

fn main() {
    let mut src = ShortReader { data: b"hello world", limit: 3, i: 0 };
    let mut dst = ShortWriter { buf: Vec::new(), limit: 2 };
    let n = copy_chunks(&mut src, &mut dst, 8).unwrap();
    let mut ok = check("copy", (n, String::from_utf8(dst.buf).unwrap()), (11, "hello world".to_string()));

    let raw = {
        let mut v = frame(b"hello");
        v.extend(frame(b"world"));
        v
    };
    let mut stream = ShortReader { data: &raw, limit: 3, i: 0 };
    let shown = (
        show(read_frame(&mut stream)),
        show(read_frame(&mut stream)),
        show(read_frame(&mut stream)),
    );
    ok &= check("frames", shown, ("some:hello".to_string(), "some:world".to_string(), "none".to_string()));

    let bad_raw = {
        let mut v = frame(b"hello");
        v.extend_from_slice(&[0, 0]);
        v
    };
    let mut bad = ShortReader { data: &bad_raw, limit: 1, i: 0 };
    let _ = read_frame(&mut bad).unwrap();
    ok &= check("truncated", show(read_frame(&mut bad)), "UnexpectedEof".to_string());

    let dir = std::env::temp_dir().join(format!("rustex{}", std::process::id()));
    fs::create_dir_all(&dir).unwrap();
    let path = dir.join("notes.txt");
    atomic_write(&path, b"hello").unwrap();
    let names: Vec<_> = fs::read_dir(&dir).unwrap().map(|e| e.unwrap().file_name().into_string().unwrap()).collect();
    ok &= check(
        "atomic",
        (fs::read_to_string(&path).unwrap(), names),
        ("hello".to_string(), vec!["notes.txt".to_string()]),
    );
    fs::remove_dir_all(&dir).unwrap();
    if !ok {
        std::process::exit(1);
    }
}
```

<details><summary>Solution</summary>

```rust file=solution.rs
use std::fs;
use std::io::{self, Read, Write};
use std::path::Path;

struct ShortReader<'a> {
    data: &'a [u8],
    limit: usize,
    i: usize,
}

impl Read for ShortReader<'_> {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
        if self.i >= self.data.len() {
            return Ok(0);
        }
        let n = buf.len().min(self.limit).min(self.data.len() - self.i);
        buf[..n].copy_from_slice(&self.data[self.i..self.i + n]);
        self.i += n;
        Ok(n)
    }
}

struct ShortWriter {
    buf: Vec<u8>,
    limit: usize,
}

impl Write for ShortWriter {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        let n = buf.len().min(self.limit);
        self.buf.extend_from_slice(&buf[..n]);
        Ok(n)
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

fn copy_chunks(src: &mut impl Read, dst: &mut impl Write, size: usize) -> io::Result<usize> {
    let mut buf = vec![0u8; size];
    let mut total = 0;
    loop {
        let n = src.read(&mut buf)?;
        if n == 0 {
            return Ok(total);
        }
        let mut off = 0;
        while off < n {
            let w = dst.write(&buf[off..n])?;
            if w == 0 {
                return Err(io::Error::new(io::ErrorKind::WriteZero, "short write"));
            }
            off += w;
            total += w;
        }
    }
}

fn read_full(src: &mut impl Read, n: usize) -> io::Result<Option<Vec<u8>>> {
    let mut buf = vec![0u8; n];
    let mut got = 0;
    while got < n {
        match src.read(&mut buf[got..])? {
            0 if got == 0 => return Ok(None),
            0 => return Err(io::Error::new(io::ErrorKind::UnexpectedEof, "truncated")),
            k => got += k,
        }
    }
    Ok(Some(buf))
}

fn read_frame(src: &mut impl Read) -> io::Result<Option<Vec<u8>>> {
    let Some(header) = read_full(src, 4)? else {
        return Ok(None);
    };
    let n = u32::from_be_bytes(header.as_slice().try_into().unwrap()) as usize;
    match read_full(src, n)? {
        Some(body) => Ok(Some(body)),
        None => Err(io::Error::new(io::ErrorKind::UnexpectedEof, "truncated frame")),
    }
}

fn atomic_write(path: &Path, data: &[u8]) -> io::Result<()> {
    let mut name = path.file_name().unwrap().to_os_string();
    name.push(".tmp");
    let tmp = path.with_file_name(name);
    fs::write(&tmp, data)?;
    fs::rename(&tmp, path)?;
    Ok(())
}

fn frame(payload: &[u8]) -> Vec<u8> {
    let mut out = (payload.len() as u32).to_be_bytes().to_vec();
    out.extend_from_slice(payload);
    out
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

fn show(r: io::Result<Option<Vec<u8>>>) -> String {
    match r {
        Ok(Some(b)) => format!("some:{}", String::from_utf8_lossy(&b)),
        Ok(None) => "none".into(),
        Err(e) => format!("{:?}", e.kind()),
    }
}

fn main() {
    let mut src = ShortReader { data: b"hello world", limit: 3, i: 0 };
    let mut dst = ShortWriter { buf: Vec::new(), limit: 2 };
    let n = copy_chunks(&mut src, &mut dst, 8).unwrap();
    let mut ok = check("copy", (n, String::from_utf8(dst.buf).unwrap()), (11, "hello world".to_string()));

    let raw = {
        let mut v = frame(b"hello");
        v.extend(frame(b"world"));
        v
    };
    let mut stream = ShortReader { data: &raw, limit: 3, i: 0 };
    let shown = (
        show(read_frame(&mut stream)),
        show(read_frame(&mut stream)),
        show(read_frame(&mut stream)),
    );
    ok &= check("frames", shown, ("some:hello".to_string(), "some:world".to_string(), "none".to_string()));

    let bad_raw = {
        let mut v = frame(b"hello");
        v.extend_from_slice(&[0, 0]);
        v
    };
    let mut bad = ShortReader { data: &bad_raw, limit: 1, i: 0 };
    let _ = read_frame(&mut bad).unwrap();
    ok &= check("truncated", show(read_frame(&mut bad)), "UnexpectedEof".to_string());

    let dir = std::env::temp_dir().join(format!("rustex{}", std::process::id()));
    fs::create_dir_all(&dir).unwrap();
    let path = dir.join("notes.txt");
    atomic_write(&path, b"hello").unwrap();
    let names: Vec<_> = fs::read_dir(&dir).unwrap().map(|e| e.unwrap().file_name().into_string().unwrap()).collect();
    ok &= check(
        "atomic",
        (fs::read_to_string(&path).unwrap(), names),
        ("hello".to_string(), vec!["notes.txt".to_string()]),
    );
    fs::remove_dir_all(&dir).unwrap();
    if !ok {
        std::process::exit(1);
    }
}
```

</details>

Next: [16 — Network programming](16-network.md)
