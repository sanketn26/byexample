# Go 15 — Streaming

A file, a pipe, and a socket are the same shape: an `io.Reader` and an
`io.Writer` that deliver bytes in pieces. `Read` may return fewer bytes
than the buffer. `Write` may accept fewer than you offered. A short read
is normal. End of stream is `io.EOF`. The loop below is what `io.Copy`,
and the copy helpers in the other languages of this course, actually do.

## Copy until every short write is accepted

A short write must be retried from the first byte the callee did not take.
"I called Write" is not "those bytes are stored". This reader returns at
most 3 bytes, and this writer accepts at most 2, so one `Copy` would be
wrong. The counts are the reads and the writes it took to move 11 bytes.

```go file=n01.go
package main

import (
	"bytes"
	"fmt"
	"io"
)

type shortReader struct {
	data  []byte
	limit int
	i     int
	reads int
}

func (r *shortReader) Read(p []byte) (int, error) {
	r.reads++
	if r.i >= len(r.data) {
		return 0, io.EOF
	}
	n := len(p)
	if n > r.limit {
		n = r.limit
	}
	if n > len(r.data)-r.i {
		n = len(r.data) - r.i
	}
	copy(p, r.data[r.i:r.i+n])
	r.i += n
	return n, nil
}

type shortWriter struct {
	buf    bytes.Buffer
	limit  int
	writes int
}

func (w *shortWriter) Write(p []byte) (int, error) {
	w.writes++
	n := len(p)
	if n > w.limit {
		n = w.limit
	}
	w.buf.Write(p[:n])
	return n, nil
}

func copyChunks(src io.Reader, dst io.Writer, size int) (int, error) {
	buf := make([]byte, size)
	total := 0
	for {
		n, err := src.Read(buf)
		if n > 0 {
			off := 0
			for off < n {
				w, werr := dst.Write(buf[off:n])
				if w < 0 || (w == 0 && werr == nil) {
					werr = io.ErrShortWrite
				}
				off += w
				total += w
				if werr != nil {
					return total, werr
				}
			}
		}
		if err == io.EOF {
			return total, nil
		}
		if err != nil {
			return total, err
		}
	}
}

func main() {
	src := &shortReader{data: []byte("hello world"), limit: 3}
	dst := &shortWriter{limit: 2}
	n, err := copyChunks(src, dst, 8)
	if err != nil {
		panic(err)
	}
	fmt.Println(n, src.reads, dst.writes, dst.buf.String())
}
```

```text output
11 5 7 hello world
```

## A frame is a length and then a body

The length is a big-endian `uint32` of the body, so the other languages in
this course can read the same bytes. Cap that length before you allocate
it. `readFull` loops until it has every byte. `io.EOF` before any byte of
a frame means there is no next frame.

```go file=n02.go
package main

import (
	"encoding/binary"
	"fmt"
	"io"
)

type shortReader struct {
	data  []byte
	limit int
	i     int
}

func (r *shortReader) Read(p []byte) (int, error) {
	if r.i >= len(r.data) {
		return 0, io.EOF
	}
	n := len(p)
	if n > r.limit {
		n = r.limit
	}
	if n > len(r.data)-r.i {
		n = len(r.data) - r.i
	}
	copy(p, r.data[r.i:r.i+n])
	r.i += n
	return n, nil
}

func readFull(src io.Reader, n int) ([]byte, error) {
	buf := make([]byte, n)
	got := 0
	for got < n {
		k, err := src.Read(buf[got:])
		got += k
		if err != nil {
			if err == io.EOF && got == 0 {
				return nil, io.EOF
			}
			if err == io.EOF {
				return nil, io.ErrUnexpectedEOF
			}
			return nil, err
		}
	}
	return buf, nil
}

func encodeFrame(payload []byte) []byte {
	buf := make([]byte, 4+len(payload))
	binary.BigEndian.PutUint32(buf, uint32(len(payload)))
	copy(buf[4:], payload)
	return buf
}

func readFrame(src io.Reader) ([]byte, error) {
	header, err := readFull(src, 4)
	if err != nil {
		return nil, err
	}
	n := binary.BigEndian.Uint32(header)
	return readFull(src, int(n))
}

func main() {
	raw := append(encodeFrame([]byte("hello")), encodeFrame([]byte("world"))...)
	stream := &shortReader{data: raw, limit: 3}
	a, err := readFrame(stream)
	if err != nil {
		panic(err)
	}
	b, err := readFrame(stream)
	if err != nil {
		panic(err)
	}
	_, err = readFrame(stream)
	fmt.Printf("%s %s %v\n", a, b, err)
}
```

```text output
hello world EOF
```

## A truncated header is not a payload

Two bytes of a four-byte length, then end of stream, is
`io.ErrUnexpectedEOF`. Fail the frame. Do not return a partial body.

```go file=n03.go
package main

import (
	"encoding/binary"
	"fmt"
	"io"
)

type shortReader struct {
	data  []byte
	limit int
	i     int
}

func (r *shortReader) Read(p []byte) (int, error) {
	if r.i >= len(r.data) {
		return 0, io.EOF
	}
	n := len(p)
	if n > r.limit {
		n = r.limit
	}
	if n > len(r.data)-r.i {
		n = len(r.data) - r.i
	}
	copy(p, r.data[r.i:r.i+n])
	r.i += n
	return n, nil
}

func readFull(src io.Reader, n int) ([]byte, error) {
	buf := make([]byte, n)
	got := 0
	for got < n {
		k, err := src.Read(buf[got:])
		got += k
		if err != nil {
			if err == io.EOF && got == 0 {
				return nil, io.EOF
			}
			if err == io.EOF {
				return nil, io.ErrUnexpectedEOF
			}
			return nil, err
		}
	}
	return buf, nil
}

func encodeFrame(payload []byte) []byte {
	buf := make([]byte, 4+len(payload))
	binary.BigEndian.PutUint32(buf, uint32(len(payload)))
	copy(buf[4:], payload)
	return buf
}

func readFrame(src io.Reader) ([]byte, error) {
	header, err := readFull(src, 4)
	if err != nil {
		return nil, err
	}
	n := binary.BigEndian.Uint32(header)
	return readFull(src, int(n))
}

func main() {
	raw := append(encodeFrame([]byte("hello")), 0, 0)
	stream := &shortReader{data: raw, limit: 3}
	if _, err := readFrame(stream); err != nil {
		panic(err)
	}
	_, err := readFrame(stream)
	fmt.Println(err)
}
```

```text output
unexpected EOF
```

## Rename a temp file in the same directory

`rename` on one filesystem replaces the destination atomically. Write the
temporary beside the target, and check the error from `Write` and from
`Close`. A buffered writer can fail there, after `Write` returned success.
On any failure, remove the temporary so it is not left behind.

```go file=n04.go
package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

func atomicWrite(path string, data []byte) error {
	dir := filepath.Dir(path)
	f, err := os.CreateTemp(dir, filepath.Base(path)+".tmp*")
	if err != nil {
		return err
	}
	tmp := f.Name()
	_, werr := f.Write(data)
	cerr := f.Close()
	if werr != nil {
		os.Remove(tmp)
		return werr
	}
	if cerr != nil {
		os.Remove(tmp)
		return cerr
	}
	if err := os.Rename(tmp, path); err != nil {
		os.Remove(tmp)
		return err
	}
	return nil
}

func main() {
	dir, err := os.MkdirTemp("", "stream")
	if err != nil {
		panic(err)
	}
	defer os.RemoveAll(dir)
	path := filepath.Join(dir, "notes.txt")
	if err := atomicWrite(path, []byte("hello\n")); err != nil {
		panic(err)
	}
	got, err := os.ReadFile(path)
	if err != nil {
		panic(err)
	}
	entries, err := os.ReadDir(dir)
	if err != nil {
		panic(err)
	}
	fmt.Println("notes.txt", strings.TrimSpace(string(got)), len(entries) == 1)
}
```

```text output
notes.txt hello true
```

## A pipe uses the same frame reader

`io.Pipe` is an in-memory stream. The writer runs in another goroutine
because a pipe blocks when its buffer is full. `readFrame` does not care
that the bytes came from a pipe instead of a slice.

```go file=n05.go
package main

import (
	"encoding/binary"
	"fmt"
	"io"
)

func readFull(src io.Reader, n int) ([]byte, error) {
	buf := make([]byte, n)
	got := 0
	for got < n {
		k, err := src.Read(buf[got:])
		got += k
		if err != nil {
			if err == io.EOF && got == 0 {
				return nil, io.EOF
			}
			if err == io.EOF {
				return nil, io.ErrUnexpectedEOF
			}
			return nil, err
		}
	}
	return buf, nil
}

func encodeFrame(payload []byte) []byte {
	buf := make([]byte, 4+len(payload))
	binary.BigEndian.PutUint32(buf, uint32(len(payload)))
	copy(buf[4:], payload)
	return buf
}

func readFrame(src io.Reader) ([]byte, error) {
	header, err := readFull(src, 4)
	if err != nil {
		return nil, err
	}
	return readFull(src, int(binary.BigEndian.Uint32(header)))
}

func main() {
	pr, pw := io.Pipe()
	go func() {
		_, _ = pw.Write(encodeFrame([]byte("via-pipe")))
		pw.Close()
	}()
	frame, err := readFrame(pr)
	if err != nil {
		panic(err)
	}
	fmt.Printf("%s\n", frame)
}
```

```text output
via-pipe
```

## Exercises

`CopyChunks` must honour short reads and short writes. `ReadFrame` returns `io.EOF` before a frame and `io.ErrUnexpectedEOF` when one is cut off. `AtomicWrite` leaves exactly the destination file behind.

```go file=exercise.go
package main

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"io"
	"os"
	"path/filepath"
)

type shortReader struct {
	data  []byte
	limit int
	i     int
}

func (r *shortReader) Read(p []byte) (int, error) {
	if r.i >= len(r.data) {
		return 0, io.EOF
	}
	n := len(p)
	if n > r.limit {
		n = r.limit
	}
	if n > len(r.data)-r.i {
		n = len(r.data) - r.i
	}
	copy(p, r.data[r.i:r.i+n])
	r.i += n
	return n, nil
}

type shortWriter struct {
	buf   bytes.Buffer
	limit int
}

func (w *shortWriter) Write(p []byte) (int, error) {
	n := len(p)
	if n > w.limit {
		n = w.limit
	}
	w.buf.Write(p[:n])
	return n, nil
}

func CopyChunks(src io.Reader, dst io.Writer, size int) (int, error) {
	return 0, nil
}

func ReadFrame(src io.Reader) ([]byte, error) {
	return nil, nil
}

func AtomicWrite(path string, data []byte) error {
	return nil
}

func frame(payload []byte) []byte {
	buf := make([]byte, 4+len(payload))
	binary.BigEndian.PutUint32(buf, uint32(len(payload)))
	copy(buf[4:], payload)
	return buf
}

var failed bool

func check(label string, got, want any) {
	if fmt.Sprint(got) == fmt.Sprint(want) {
		fmt.Println("PASS", label)
		return
	}
	failed = true
	fmt.Printf("FAIL %s: got %v, want %v\n", label, got, want)
}

func main() {
	src := &shortReader{data: []byte("hello world"), limit: 3}
	dst := &shortWriter{limit: 2}
	n, err := CopyChunks(src, dst, 8)
	check("copy", []any{n, err, dst.buf.String()}, []any{11, nil, "hello world"})

	stream := &shortReader{data: append(frame([]byte("hello")), frame([]byte("world"))...), limit: 3}
	a, err1 := ReadFrame(stream)
	b, err2 := ReadFrame(stream)
	_, err3 := ReadFrame(stream)
	check("frames", []any{string(a), err1, string(b), err2, err3}, []any{"hello", nil, "world", nil, io.EOF})

	bad := &shortReader{data: append(frame([]byte("hello")), 0, 0), limit: 1}
	ReadFrame(bad)
	_, err = ReadFrame(bad)
	check("truncated", err, io.ErrUnexpectedEOF)

	dir, err := os.MkdirTemp("", "atomic")
	if err != nil {
		panic(err)
	}
	defer os.RemoveAll(dir)
	path := filepath.Join(dir, "notes.txt")
	err = AtomicWrite(path, []byte("hello"))
	got, _ := os.ReadFile(path)
	entries, _ := os.ReadDir(dir)
	check("atomic", []any{err, string(got), len(entries)}, []any{nil, "hello", 1})
	if failed {
		os.Exit(1)
	}
}
```

<details><summary>Solution</summary>

```go file=solution.go
package main

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"io"
	"os"
	"path/filepath"
)

type shortReader struct {
	data  []byte
	limit int
	i     int
}

func (r *shortReader) Read(p []byte) (int, error) {
	if r.i >= len(r.data) {
		return 0, io.EOF
	}
	n := len(p)
	if n > r.limit {
		n = r.limit
	}
	if n > len(r.data)-r.i {
		n = len(r.data) - r.i
	}
	copy(p, r.data[r.i:r.i+n])
	r.i += n
	return n, nil
}

type shortWriter struct {
	buf   bytes.Buffer
	limit int
}

func (w *shortWriter) Write(p []byte) (int, error) {
	n := len(p)
	if n > w.limit {
		n = w.limit
	}
	w.buf.Write(p[:n])
	return n, nil
}

func CopyChunks(src io.Reader, dst io.Writer, size int) (int, error) {
	buf := make([]byte, size)
	total := 0
	for {
		n, err := src.Read(buf)
		if n > 0 {
			off := 0
			for off < n {
				w, werr := dst.Write(buf[off:n])
				if w < 0 || (w == 0 && werr == nil) {
					werr = io.ErrShortWrite
				}
				off += w
				total += w
				if werr != nil {
					return total, werr
				}
			}
		}
		if err == io.EOF {
			return total, nil
		}
		if err != nil {
			return total, err
		}
	}
}

func readFull(src io.Reader, n int) ([]byte, error) {
	buf := make([]byte, n)
	got := 0
	for got < n {
		k, err := src.Read(buf[got:])
		got += k
		if err != nil {
			if err == io.EOF && got == 0 {
				return nil, io.EOF
			}
			if err == io.EOF {
				return nil, io.ErrUnexpectedEOF
			}
			return nil, err
		}
	}
	return buf, nil
}

func ReadFrame(src io.Reader) ([]byte, error) {
	header, err := readFull(src, 4)
	if err != nil {
		return nil, err
	}
	n := binary.BigEndian.Uint32(header)
	return readFull(src, int(n))
}

func AtomicWrite(path string, data []byte) error {
	dir := filepath.Dir(path)
	f, err := os.CreateTemp(dir, filepath.Base(path)+".tmp*")
	if err != nil {
		return err
	}
	tmp := f.Name()
	_, werr := f.Write(data)
	cerr := f.Close()
	if werr != nil || cerr != nil {
		os.Remove(tmp)
		if werr != nil {
			return werr
		}
		return cerr
	}
	if err := os.Rename(tmp, path); err != nil {
		os.Remove(tmp)
		return err
	}
	return nil
}

func frame(payload []byte) []byte {
	buf := make([]byte, 4+len(payload))
	binary.BigEndian.PutUint32(buf, uint32(len(payload)))
	copy(buf[4:], payload)
	return buf
}

var failed bool

func check(label string, got, want any) {
	if fmt.Sprint(got) == fmt.Sprint(want) {
		fmt.Println("PASS", label)
		return
	}
	failed = true
	fmt.Printf("FAIL %s: got %v, want %v\n", label, got, want)
}

func main() {
	src := &shortReader{data: []byte("hello world"), limit: 3}
	dst := &shortWriter{limit: 2}
	n, err := CopyChunks(src, dst, 8)
	check("copy", []any{n, err, dst.buf.String()}, []any{11, nil, "hello world"})

	stream := &shortReader{data: append(frame([]byte("hello")), frame([]byte("world"))...), limit: 3}
	a, err1 := ReadFrame(stream)
	b, err2 := ReadFrame(stream)
	_, err3 := ReadFrame(stream)
	check("frames", []any{string(a), err1, string(b), err2, err3}, []any{"hello", nil, "world", nil, io.EOF})

	bad := &shortReader{data: append(frame([]byte("hello")), 0, 0), limit: 1}
	ReadFrame(bad)
	_, err = ReadFrame(bad)
	check("truncated", err, io.ErrUnexpectedEOF)

	dir, err := os.MkdirTemp("", "atomic")
	if err != nil {
		panic(err)
	}
	defer os.RemoveAll(dir)
	path := filepath.Join(dir, "notes.txt")
	err = AtomicWrite(path, []byte("hello"))
	got, _ := os.ReadFile(path)
	entries, _ := os.ReadDir(dir)
	check("atomic", []any{err, string(got), len(entries)}, []any{nil, "hello", 1})
	if failed {
		os.Exit(1)
	}
}
```

</details>

Next: [16 — Network programming](16-network.md)
