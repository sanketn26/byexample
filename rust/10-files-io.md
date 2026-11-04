# Rust 10 — Files, I/O and Processes

I/O is the `Read`, `Write`, and `BufRead` traits. Every call returns
`io::Result`, so `?` keeps the success path in a straight line. A `File` is
closed when it is dropped. `main` may return `io::Result<()>`: an `Err`
prints a debug message and the process exits non-zero.

## `write` and `read_to_string` move a whole file

`fs::write` creates or replaces the file. `read_to_string` fails if the
bytes are not UTF-8. For arbitrary bytes, use `fs::read` and
`String::from_utf8_lossy`.

```rust file=n01.rs
use std::env;
use std::fs;

fn main() -> std::io::Result<()> {
    let dir = env::temp_dir().join(format!("rust_by_example_{}", std::process::id()));
    fs::create_dir_all(&dir)?;
    let notes = dir.join("notes.txt");
    fs::write(&notes, "alpha\nbeta\ngamma\n")?;
    let text = fs::read_to_string(&notes)?;
    println!("{:?}", text.lines().collect::<Vec<_>>());
    fs::write(dir.join("bad.bin"), [0xffu8])?;
    println!("{}", fs::read_to_string(dir.join("bad.bin")).is_err());
    println!("{}", String::from_utf8_lossy(&fs::read(dir.join("bad.bin"))?));
    fs::remove_dir_all(&dir)?;
    Ok(())
}
```

```text output
["alpha", "beta", "gamma"]
true
�
```

## `BufReader` reads a line at a time

An unbuffered `File` is one syscall per `read`. Wrap it in `BufReader` for
lines, and in `BufWriter` for many small writes. `lines` yields a `Result`
per line because the underlying read can fail.

```rust file=n02.rs
use std::env;
use std::fs::{self, File};
use std::io::{BufRead, BufReader};

fn main() -> std::io::Result<()> {
    let dir = env::temp_dir().join(format!("rust_by_example_{}", std::process::id()));
    fs::create_dir_all(&dir)?;
    let notes = dir.join("notes.txt");
    fs::write(&notes, "alpha\nbeta\ngamma\n")?;
    let reader = BufReader::new(File::open(&notes)?);
    for (i, line) in reader.lines().enumerate() {
        println!("{} {}", i + 1, line?);
    }
    fs::remove_dir_all(&dir)?;
    Ok(())
}
```

```text output
1 alpha
2 beta
3 gamma
```

## Append, then drop the handle before you reread

`OpenOptions` opens the file without truncating it. `drop(f)` closes the
handle so the next read sees the new bytes. Drop would also close it at the
end of the scope.

```rust file=n03.rs
use std::env;
use std::fs::{self, OpenOptions};
use std::io::Write;

fn main() -> std::io::Result<()> {
    let dir = env::temp_dir().join(format!("rust_by_example_{}", std::process::id()));
    fs::create_dir_all(&dir)?;
    let notes = dir.join("notes.txt");
    fs::write(&notes, "alpha\nbeta\ngamma\n")?;
    let mut f = OpenOptions::new().append(true).open(&notes)?;
    writeln!(f, "delta")?;
    drop(f);
    println!("{}", fs::read_to_string(&notes)?.lines().count());
    fs::remove_dir_all(&dir)?;
    Ok(())
}
```

```text output
4
```

## Bytes and metadata are not text

`fs::read` returns the raw `Vec<u8>`. `metadata().len()` is the length in
bytes, here four.

```rust file=n04.rs
use std::env;
use std::fs;

fn main() -> std::io::Result<()> {
    let dir = env::temp_dir().join(format!("rust_by_example_{}", std::process::id()));
    fs::create_dir_all(&dir)?;
    let bin = dir.join("data.bin");
    fs::write(&bin, [0u8, 1, 2, 255])?;
    println!("{:?} {}", fs::read(&bin)?, fs::metadata(&bin)?.len());
    fs::remove_dir_all(&dir)?;
    Ok(())
}
```

```text output
[0, 1, 2, 255] 4
```

## `BufWriter` forgets a flush error on drop

The buffer is flushed when the writer is dropped, and that flush ignores
the error. Call `flush()?` when a short write must not disappear. The
`Debug` of the string shows the newlines.

```rust file=n05.rs
use std::env;
use std::fs::{self, File};
use std::io::{BufWriter, Write};

fn main() -> std::io::Result<()> {
    let dir = env::temp_dir().join(format!("rust_by_example_{}", std::process::id()));
    fs::create_dir_all(&dir)?;
    let path = dir.join("out.txt");
    {
        let mut w = BufWriter::new(File::create(&path)?);
        for i in 0..3 {
            writeln!(w, "line {i}")?;
        }
        w.flush()?;
    }
    println!("{:?}", fs::read_to_string(path)?);
    fs::remove_dir_all(&dir)?;
    Ok(())
}
```

```text output
"line 0\nline 1\nline 2\n"
```

## `seek` and `read_exact` take a fixed slice

`SeekFrom::Start(6)` is the byte offset of `beta` in `alpha\nbeta\ngamma\n`.
`read_exact` fails if the file ends before the buffer is full.

```rust file=n06.rs
use std::env;
use std::fs::{self, File};
use std::io::{Read, Seek, SeekFrom};

fn main() -> std::io::Result<()> {
    let dir = env::temp_dir().join(format!("rust_by_example_{}", std::process::id()));
    fs::create_dir_all(&dir)?;
    let notes = dir.join("notes.txt");
    fs::write(&notes, "alpha\nbeta\ngamma\n")?;
    let mut f = File::open(&notes)?;
    f.seek(SeekFrom::Start(6))?;
    let mut buf = [0u8; 4];
    f.read_exact(&mut buf)?;
    println!("{}", String::from_utf8_lossy(&buf));
    fs::remove_dir_all(&dir)?;
    Ok(())
}
```

```text output
beta
```

## A few lines of CSV need no crate

Skip the header. `split` and `parse` pull out one column. This is not a
real CSV parser: no quotes, no escaped commas.

```rust file=n07.rs
use std::env;
use std::fs;

fn main() -> std::io::Result<()> {
    let dir = env::temp_dir().join(format!("rust_by_example_{}", std::process::id()));
    fs::create_dir_all(&dir)?;
    let path = dir.join("people.csv");
    fs::write(&path, "name,age\nAda,36\nLinus,55\n")?;
    let csv = fs::read_to_string(&path)?;
    let total: u32 = csv
        .lines()
        .skip(1)
        .filter_map(|l| l.split(',').nth(1)?.parse::<u32>().ok())
        .sum();
    println!("{total}");
    fs::remove_dir_all(&dir)?;
    Ok(())
}
```

```text output
91
```

## Replace a file by renaming in the same directory

`std::fs` has no separate atomic-replace call. Write a temporary file next
to the destination and `rename` it over the target. `rename` is atomic on
one filesystem. Sort after `read_dir`: the order it yields is arbitrary.

```rust file=n08.rs
use std::env;
use std::fs::{self, File};
use std::io::{self, Write};
use std::path::Path;

fn walk(dir: &Path, base: &Path, out: &mut Vec<String>) -> io::Result<()> {
    for entry in fs::read_dir(dir)? {
        let path = entry?.path();
        if path.is_dir() {
            walk(&path, base, out)?;
        } else {
            let rel = path.strip_prefix(base).unwrap();
            out.push(rel.to_string_lossy().replace('\\', "/"));
        }
    }
    Ok(())
}

fn main() -> io::Result<()> {
    let dir = env::temp_dir().join(format!("rust_by_example_{}", std::process::id()));
    fs::create_dir_all(&dir)?;
    let notes = dir.join("notes.txt");
    let tmp = dir.join("notes.txt.tmp");
    {
        let mut f = File::create(&tmp)?;
        write!(f, "alpha\n")?;
        f.sync_all()?;
    }
    fs::rename(&tmp, &notes)?;
    fs::create_dir(dir.join("sub"))?;
    fs::write(dir.join("sub").join("x.rs"), "fn main() {}")?;
    let mut files = Vec::new();
    walk(&dir, &dir, &mut files)?;
    files.sort();
    println!("{files:?} {}", tmp.exists());
    fs::remove_dir_all(&dir)?;
    Ok(())
}
```

```text output
["notes.txt", "sub/x.rs"] false
```

## `Path` is not a `String`

Join with `Path::join`. Do not concatenate separators yourself. `file_name`,
`extension`, and `parent` borrow from the path. `to_str` returns `Option`
because a path is not guaranteed to be UTF-8. `OsString` is the owned form
of those bytes.

```rust file=n09.rs
use std::path::{Path, PathBuf};

fn main() {
    let p = Path::new("/tmp/archive.tar.gz");
    println!(
        "{:?} {:?} {:?}",
        p.file_name().unwrap(),
        p.extension().unwrap(),
        p.parent().unwrap()
    );
    println!("{}", PathBuf::from("a").join("b").with_extension("txt").display());
    println!("{}", p.to_str().is_some());
}
```

```text output
"archive.tar.gz" "gz" "/tmp"
a/b.txt
true
```

## Errors carry a `kind`

`NotFound` is the kind for a missing path. Match on `kind` when you care
which failure it was, and keep the full error when you only need to report
it.

```rust file=n10.rs
use std::env;
use std::fs;

fn main() -> std::io::Result<()> {
    let dir = env::temp_dir().join(format!("rust_by_example_{}", std::process::id()));
    fs::create_dir_all(&dir)?;
    let err = fs::read_to_string(dir.join("nope")).unwrap_err();
    println!("{:?}", err.kind());
    fs::remove_dir_all(&dir)?;
    println!("{}", dir.exists());
    Ok(())
}
```

```text output
NotFound
false
```

## Anything that implements `Write` can be the destination

`Cursor<Vec<u8>>` is an in-memory file. The same `write!` macro targets a
socket or a `File`.

```rust file=n11.rs
use std::io::{Cursor, Write};

fn main() -> std::io::Result<()> {
    let mut mem = Cursor::new(Vec::new());
    write!(mem, "hello {}", 5)?;
    println!("{}", String::from_utf8(mem.into_inner()).unwrap());
    Ok(())
}
```

```text output
hello 5
```

## A process is not a shell

`Command` runs `echo` directly, with a separate argument, so nothing is
parsed as a shell command. `env::args` yields the program name and then the
arguments; this binary is started with none, so the length is 1. `env::var`
is `Err` both when the variable is unset and when its bytes are not UTF-8.
For a real command-line parser, use the `clap` crate.

```rust file=n12.rs
use std::env;
use std::process::Command;

fn main() -> std::io::Result<()> {
    let out = Command::new("echo").arg("42").output()?;
    println!("{}", String::from_utf8_lossy(&out.stdout).trim());
    println!("{}", env::args().len());
    println!("{}", env::var("DEFINITELY_NOT_SET").unwrap_or_else(|_| "default".into()));
    Ok(())
}
```

```text output
42
1
default
```

## Exercises

```rust file=exercise.rs
use std::fs;
use std::io::{self, BufRead, Cursor};
use std::path::Path;

/// Number of lines in the file.
fn count_lines(_path: &Path) -> io::Result<usize> {
    todo!()
}

/// "N:line" for each line containing needle, N starting at 1.
fn grep(_reader: impl BufRead, _needle: &str) -> io::Result<Vec<String>> {
    todo!()
}

/// Sum the integer column named `column` of CSV text with a header row.
/// Err describes a missing column or a bad number.
fn sum_csv_column(_reader: impl BufRead, _column: &str) -> Result<i64, String> {
    todo!()
}

/// Write data to `path` via `path.tmp` and an atomic rename.
fn write_atomic(_path: &Path, _data: &[u8]) -> io::Result<()> {
    todo!()
}

/// The longest line (the first one on ties), None for empty input.
fn longest_line(_reader: impl BufRead) -> io::Result<Option<String>> {
    todo!()
}

fn check<T: PartialEq + std::fmt::Debug>(label: &str, got: T, want: T) -> bool {
    let ok = got == want;
    if ok {
        println!("PASS {label}");
    } else {
        println!("FAIL {label}: got {got:?}, want {want:?}");
    }
    ok
}

fn main() {
    fs::write("ex_a.txt", "one\ntwo\nthree two\n").unwrap();
    let csv = "id,qty\n1,5\n2,7\n3,10\n";
    let results = [
        check("count_lines", count_lines(Path::new("ex_a.txt")).ok(), Some(3)),
        check("count_lines missing", count_lines(Path::new("ex_nope.txt")).is_err(), true),
        check(
            "grep",
            grep(Cursor::new("one\ntwo\nthree two\n"), "two").ok(),
            Some(vec!["2:two".to_string(), "3:three two".to_string()]),
        ),
        check("csv sum", sum_csv_column(Cursor::new(csv), "qty"), Ok(22)),
        check("csv missing", sum_csv_column(Cursor::new(csv), "nope").is_err(), true),
        check("csv bad number", sum_csv_column(Cursor::new("a\nx\n"), "a").is_err(), true),
        check(
            "atomic",
            {
                write_atomic(Path::new("ex_b.txt"), b"hi").unwrap();
                (
                    fs::read_to_string("ex_b.txt").ok(),
                    Path::new("ex_b.txt.tmp").exists(),
                )
            },
            (Some("hi".to_string()), false),
        ),
        check(
            "longest",
            longest_line(Cursor::new("ab\nabcd\nabcd\nx")).ok(),
            Some(Some("abcd".to_string())),
        ),
        check("longest empty", longest_line(Cursor::new("")).ok(), Some(None)),
    ];
    let _ = fs::remove_file("ex_a.txt");
    let _ = fs::remove_file("ex_b.txt");
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

<details><summary>Solution</summary>

```rust file=solution.rs
use std::fs::{self, File};
use std::io::{self, BufRead, BufReader, Cursor};
use std::path::Path;

fn count_lines(path: &Path) -> io::Result<usize> {
    let reader = BufReader::new(File::open(path)?);
    let mut n = 0;
    for line in reader.lines() {
        line?;
        n += 1;
    }
    Ok(n)
}

fn grep(reader: impl BufRead, needle: &str) -> io::Result<Vec<String>> {
    let mut out = Vec::new();
    for (i, line) in reader.lines().enumerate() {
        let line = line?;
        if line.contains(needle) {
            out.push(format!("{}:{line}", i + 1));
        }
    }
    Ok(out)
}

fn sum_csv_column(reader: impl BufRead, column: &str) -> Result<i64, String> {
    let mut lines = reader.lines();
    let header = lines
        .next()
        .ok_or("empty input")?
        .map_err(|e| e.to_string())?;
    let idx = header
        .split(',')
        .position(|h| h == column)
        .ok_or_else(|| format!("no column {column:?}"))?;
    let mut total = 0;
    for line in lines {
        let line = line.map_err(|e| e.to_string())?;
        let field = line.split(',').nth(idx).ok_or("short row")?;
        total += field
            .parse::<i64>()
            .map_err(|e| format!("bad number {field:?}: {e}"))?;
    }
    Ok(total)
}

fn write_atomic(path: &Path, data: &[u8]) -> io::Result<()> {
    let mut tmp = path.as_os_str().to_owned();
    tmp.push(".tmp");
    fs::write(&tmp, data)?;
    fs::rename(&tmp, path)
}

fn longest_line(reader: impl BufRead) -> io::Result<Option<String>> {
    let mut best: Option<String> = None;
    for line in reader.lines() {
        let line = line?;
        if best.as_ref().map_or(true, |b| line.len() > b.len()) {
            best = Some(line);
        }
    }
    Ok(best)
}

fn check<T: PartialEq + std::fmt::Debug>(label: &str, got: T, want: T) -> bool {
    let ok = got == want;
    if ok {
        println!("PASS {label}");
    } else {
        println!("FAIL {label}: got {got:?}, want {want:?}");
    }
    ok
}

fn main() {
    fs::write("ex_a.txt", "one\ntwo\nthree two\n").unwrap();
    let csv = "id,qty\n1,5\n2,7\n3,10\n";
    let results = [
        check("count_lines", count_lines(Path::new("ex_a.txt")).ok(), Some(3)),
        check("count_lines missing", count_lines(Path::new("ex_nope.txt")).is_err(), true),
        check(
            "grep",
            grep(Cursor::new("one\ntwo\nthree two\n"), "two").ok(),
            Some(vec!["2:two".to_string(), "3:three two".to_string()]),
        ),
        check("csv sum", sum_csv_column(Cursor::new(csv), "qty"), Ok(22)),
        check("csv missing", sum_csv_column(Cursor::new(csv), "nope").is_err(), true),
        check("csv bad number", sum_csv_column(Cursor::new("a\nx\n"), "a").is_err(), true),
        check(
            "atomic",
            {
                write_atomic(Path::new("ex_b.txt"), b"hi").unwrap();
                (
                    fs::read_to_string("ex_b.txt").ok(),
                    Path::new("ex_b.txt.tmp").exists(),
                )
            },
            (Some("hi".to_string()), false),
        ),
        check(
            "longest",
            longest_line(Cursor::new("ab\nabcd\nabcd\nx")).ok(),
            Some(Some("abcd".to_string())),
        ),
        check("longest empty", longest_line(Cursor::new("")).ok(), Some(None)),
    ];
    let _ = fs::remove_file("ex_a.txt");
    let _ = fs::remove_file("ex_b.txt");
    if !results.iter().all(|&r| r) {
        std::process::exit(1);
    }
}
```

</details>

Next: [11 — Concurrency](11-concurrency.md)
