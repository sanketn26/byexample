# Rust 10 — Files, I/O and Processes

I/O is built on the `Read`, `Write` and `BufRead` traits. Every operation
returns `io::Result`, so `?` makes the happy path read straight down. Files
close automatically when dropped.

## Example

```rust file=example.rs
use std::env;
use std::fs::{self, File, OpenOptions};
use std::io::{self, BufRead, BufReader, BufWriter, Cursor, Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use std::process::Command;

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

    // Whole-file helpers
    let notes = dir.join("notes.txt");
    fs::write(&notes, "alpha\nbeta\ngamma\n")?;
    let text = fs::read_to_string(&notes)?;
    println!("{:?}", text.lines().collect::<Vec<_>>());

    // Streaming line by line
    let reader = BufReader::new(File::open(&notes)?);
    for (i, line) in reader.lines().enumerate() {
        println!("{} {}", i + 1, line?);
    }

    // Appending
    let mut f = OpenOptions::new().append(true).open(&notes)?;
    writeln!(f, "delta")?;
    drop(f);
    println!("{}", fs::read_to_string(&notes)?.lines().count());

    // Binary data and metadata
    let bin = dir.join("data.bin");
    fs::write(&bin, [0u8, 1, 2, 255])?;
    println!("{:?} {}", fs::read(&bin)?, fs::metadata(&bin)?.len());

    // Buffered writes (flushed on drop, but flush to see errors)
    {
        let mut w = BufWriter::new(File::create(dir.join("out.txt"))?);
        for i in 0..3 {
            writeln!(w, "line {i}")?;
        }
        w.flush()?;
    }
    println!("{:?}", fs::read_to_string(dir.join("out.txt"))?);

    // Seeking and fixed-size reads
    let mut f = File::open(&notes)?;
    f.seek(SeekFrom::Start(6))?;
    let mut buf = [0u8; 4];
    f.read_exact(&mut buf)?;
    println!("{}", String::from_utf8_lossy(&buf));

    // A tiny CSV reader
    fs::write(dir.join("people.csv"), "name,age\nAda,36\nLinus,55\n")?;
    let csv = fs::read_to_string(dir.join("people.csv"))?;
    let total: u32 = csv
        .lines()
        .skip(1)
        .filter_map(|l| l.split(',').nth(1)?.parse::<u32>().ok())
        .sum();
    println!("{total}");

    // Directory walk
    fs::create_dir(dir.join("sub"))?;
    fs::write(dir.join("sub").join("x.rs"), "fn main() {}")?;
    let mut files = Vec::new();
    walk(&dir, &dir, &mut files)?;
    files.sort(); // read_dir order is unspecified
    println!("{files:?}");

    // Paths are values
    let p = Path::new("/tmp/archive.tar.gz");
    println!("{:?} {:?} {:?}", p.file_name().unwrap(), p.extension().unwrap(), p.parent().unwrap());
    println!("{}", PathBuf::from("a").join("b").with_extension("txt").display());

    // Errors carry a kind
    let err = fs::read_to_string(dir.join("nope")).unwrap_err();
    println!("{:?}", err.kind());

    // Anything implementing Write: here an in-memory buffer
    let mut mem = Cursor::new(Vec::new());
    write!(mem, "hello {}", 5)?;
    println!("{}", String::from_utf8(mem.into_inner()).unwrap());

    // Running a process (no shell, so no injection)
    let out = Command::new("echo").arg("42").output()?;
    println!("{}", String::from_utf8_lossy(&out.stdout).trim());

    println!("{}", env::var("DEFINITELY_NOT_SET").unwrap_or_else(|_| "default".to_string()));

    fs::remove_dir_all(&dir)?;
    println!("{}", dir.exists());
    Ok(())
}
```

```text output
["alpha", "beta", "gamma"]
1 alpha
2 beta
3 gamma
4
[0, 1, 2, 255] 4
"line 0\nline 1\nline 2\n"
beta
91
["data.bin", "notes.txt", "out.txt", "people.csv", "sub/x.rs"]
"archive.tar.gz" "gz" "/tmp"
a/b.txt
NotFound
hello 5
42
default
false
```

## Details that bite

- Unbuffered `File` reads and writes are one syscall each. Wrap in
  `BufReader` / `BufWriter` for line-oriented or many small operations.
- `BufWriter` flushes on drop but **ignores errors there**; call
  `flush()?` when correctness matters.
- `read_to_string` fails on invalid UTF-8; use `fs::read` plus
  `String::from_utf8_lossy` for arbitrary bytes.
- `Path`/`PathBuf` are not guaranteed UTF-8; `to_str()` returns an
  `Option`. Use `Path::join`, never string concatenation.
- `fs::read_dir` order is arbitrary. Sort if you need determinism.
- `std::fs` has no atomic replace by itself: write to a temp file in the
  same directory and `fs::rename` over the target.
- `env::args()` yields program arguments; for real CLIs use the `clap`
  crate. `env::var` returns `Err` for unset *and* for non-UTF-8 values.
- Remember `main` can return `io::Result<()>`; a returned `Err` prints a
  debug message and exits non-zero.

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
