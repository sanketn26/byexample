# Go 16 — Network programming

TCP is the byte stream from the previous lesson with a peer attached.
`net.Dial` and `net.Listen` speak `io.Reader` and `io.Writer`. One `Read`
can return a single byte of a frame, so loop until the length prefix and
the body are both complete. Bind `127.0.0.1` and port 0: the kernel picks
a free port, the port changes every run, and these programs print the
payload rather than the address. This is not TLS, HTTP/2, or `epoll`.
Those sit one layer down or up.

## A length prefix survives a short read

`sendAll` retries until every byte is written. The server reads one frame,
upper-cases it, and writes one frame back. The client never assumes that
one `Write` or one `Read` finished the message.

```go file=n01.go
package main

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"io"
	"net"
	"time"
)

func frame(payload []byte) []byte {
	buf := make([]byte, 4+len(payload))
	binary.BigEndian.PutUint32(buf[:4], uint32(len(payload)))
	copy(buf[4:], payload)
	return buf
}

func readFull(r io.Reader, n int) ([]byte, error) {
	buf := make([]byte, n)
	_, err := io.ReadFull(r, buf)
	return buf, err
}

func readFrame(r io.Reader) ([]byte, error) {
	hdr, err := readFull(r, 4)
	if err != nil {
		return nil, err
	}
	return readFull(r, int(binary.BigEndian.Uint32(hdr)))
}

func sendAll(w io.Writer, p []byte) error {
	for len(p) > 0 {
		n, err := w.Write(p)
		p = p[n:]
		if err != nil {
			return err
		}
		if n == 0 {
			return io.ErrShortWrite
		}
	}
	return nil
}

func main() {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		panic(err)
	}
	defer ln.Close()
	done := make(chan struct{})
	go func() {
		defer close(done)
		conn, err := ln.Accept()
		if err != nil {
			return
		}
		defer conn.Close()
		msg, err := readFrame(conn)
		if err == nil {
			_ = sendAll(conn, frame(bytes.ToUpper(msg)))
		}
	}()

	c, err := net.DialTimeout("tcp", ln.Addr().String(), 2*time.Second)
	if err != nil {
		panic(err)
	}
	defer c.Close()
	if err := sendAll(c, frame([]byte("ping"))); err != nil {
		panic(err)
	}
	msg, err := readFrame(c)
	if err != nil {
		panic(err)
	}
	fmt.Println("frame", string(msg))
	<-done
}
```

```text output
frame PING
```

## A timeout is not a closed peer

The server accepts and then stays silent. The client's read deadline
fires. Closing your side matters: the timeout does not cancel the server,
and an accept loop left inside that connection never takes the next one.
On Rust, `set_read_timeout` usually surfaces as `WouldBlock`, not
`TimedOut`. Treat both as a timeout.

```go file=n02.go
package main

import (
	"encoding/binary"
	"fmt"
	"io"
	"net"
	"time"
)

func readFull(r io.Reader, n int) ([]byte, error) {
	buf := make([]byte, n)
	_, err := io.ReadFull(r, buf)
	return buf, err
}

func readFrame(r io.Reader) ([]byte, error) {
	hdr, err := readFull(r, 4)
	if err != nil {
		return nil, err
	}
	return readFull(r, int(binary.BigEndian.Uint32(hdr)))
}

func main() {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		panic(err)
	}
	defer ln.Close()
	done := make(chan struct{})
	go func() {
		defer close(done)
		conn, err := ln.Accept()
		if err != nil {
			return
		}
		defer conn.Close()
		_ = conn.SetReadDeadline(time.Now().Add(2 * time.Second))
		buf := make([]byte, 1)
		_, _ = conn.Read(buf)
	}()

	c, err := net.DialTimeout("tcp", ln.Addr().String(), 2*time.Second)
	if err != nil {
		panic(err)
	}
	_ = c.SetReadDeadline(time.Now().Add(150 * time.Millisecond))
	_, err = readFrame(c)
	c.Close()
	if ne, ok := err.(net.Error); ok && ne.Timeout() {
		fmt.Println("timeout")
	} else {
		fmt.Println("unexpected", err)
	}
	<-done
}
```

```text output
timeout
```

## A peer who closes mid-frame is `unexpected EOF`

The server writes two bytes of a four-byte header and closes. That is a
different error from a timeout. `io.EOF` before any byte, or
`io.ErrUnexpectedEOF` after some, both mean the frame was cut off.

```go file=n03.go
package main

import (
	"encoding/binary"
	"fmt"
	"io"
	"net"
	"time"
)

func readFull(r io.Reader, n int) ([]byte, error) {
	buf := make([]byte, n)
	_, err := io.ReadFull(r, buf)
	return buf, err
}

func readFrame(r io.Reader) ([]byte, error) {
	hdr, err := readFull(r, 4)
	if err != nil {
		return nil, err
	}
	return readFull(r, int(binary.BigEndian.Uint32(hdr)))
}

func main() {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		panic(err)
	}
	defer ln.Close()
	done := make(chan struct{})
	go func() {
		defer close(done)
		conn, err := ln.Accept()
		if err != nil {
			return
		}
		defer conn.Close()
		_, _ = conn.Write([]byte{0, 0})
	}()

	c, err := net.DialTimeout("tcp", ln.Addr().String(), 2*time.Second)
	if err != nil {
		panic(err)
	}
	defer c.Close()
	_, err = readFrame(c)
	if err == io.ErrUnexpectedEOF || err == io.EOF {
		fmt.Println("truncated")
	} else {
		fmt.Println("unexpected", err)
	}
	<-done
}
```

```text output
truncated
```

## HTTP is the same stream plus text headers

`Content-Length` tells the peer when the body ends. `Connection: close` is
the other signal. `net/http` writes those bytes for you. A hand-written
request in C or Rust puts the same text on the socket.

```go file=n04.go
package main

import (
	"bytes"
	"fmt"
	"io"
	"net"
	"net/http"
)

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/echo", func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		fmt.Fprintf(w, "echo:%s", body)
	})
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		panic(err)
	}
	srv := &http.Server{Handler: mux}
	go srv.Serve(ln)
	resp, err := http.Post("http://"+ln.Addr().String()+"/echo", "text/plain", bytes.NewReader([]byte("hi")))
	if err != nil {
		panic(err)
	}
	body, err := io.ReadAll(resp.Body)
	resp.Body.Close()
	if err != nil {
		panic(err)
	}
	fmt.Println("http", resp.StatusCode, string(body))
	srv.Close()
}
```

```text output
http 200 echo:hi
```

## Exercises

The harness is a small server. You write the client: one framed exchange, a classifier that reports `timeout` or `truncated`, and an HTTP POST whose status and body you return.

```go file=exercise.go
package main

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"time"
)

func frame(payload []byte) []byte {
	buf := make([]byte, 4+len(payload))
	binary.BigEndian.PutUint32(buf[:4], uint32(len(payload)))
	copy(buf[4:], payload)
	return buf
}

func readFull(r io.Reader, n int) ([]byte, error) {
	buf := make([]byte, n)
	_, err := io.ReadFull(r, buf)
	return buf, err
}

func ReadFrame(r io.Reader) ([]byte, error) {
	hdr, err := readFull(r, 4)
	if err != nil {
		return nil, err
	}
	n := binary.BigEndian.Uint32(hdr)
	return readFull(r, int(n))
}

func sendAll(w io.Writer, p []byte) error {
	for len(p) > 0 {
		n, err := w.Write(p)
		p = p[n:]
		if err != nil {
			return err
		}
		if n == 0 {
			return io.ErrShortWrite
		}
	}
	return nil
}

func Exchange(addr string, payload []byte) ([]byte, error) {
	return nil, nil
}

func Classify(conn net.Conn) string {
	return ""
}

func PostHTTP(url, body string) (int, string, error) {
	return 0, "", nil
}

func stringsReader(s string) io.Reader { return bytes.NewReader([]byte(s)) }

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
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		panic(err)
	}
	go func() {
		for _, mode := range []string{"echo", "silent", "drop"} {
			conn, err := ln.Accept()
			if err != nil {
				return
			}
			switch mode {
			case "echo":
				msg, err := ReadFrame(conn)
				if err == nil {
					_ = sendAll(conn, frame(bytes.ToUpper(msg)))
				}
			case "silent":
				_ = conn.SetReadDeadline(time.Now().Add(2 * time.Second))
				buf := make([]byte, 1)
				_, _ = conn.Read(buf)
			default:
				_, _ = conn.Write([]byte{0, 0})
			}
			conn.Close()
		}
	}()

	addr := ln.Addr().String()
	msg, err := Exchange(addr, []byte("ping"))
	check("exchange", []any{string(msg), err}, []any{"PING", nil})

	c, err := net.Dial("tcp", addr)
	if err != nil {
		panic(err)
	}
	check("timeout", Classify(c), "timeout")
	c.Close()

	c, err = net.Dial("tcp", addr)
	if err != nil {
		panic(err)
	}
	check("truncated", Classify(c), "truncated")
	c.Close()
	ln.Close()

	mux := http.NewServeMux()
	mux.HandleFunc("/echo", func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		fmt.Fprintf(w, "echo:%s", body)
	})
	httpLn, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		panic(err)
	}
	srv := &http.Server{Handler: mux}
	go srv.Serve(httpLn)
	status, body, err := PostHTTP("http://"+httpLn.Addr().String()+"/echo", "hi")
	check("http", []any{status, body, err}, []any{200, "echo:hi", nil})
	srv.Close()
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
	"net"
	"net/http"
	"os"
	"time"
)

func frame(payload []byte) []byte {
	buf := make([]byte, 4+len(payload))
	binary.BigEndian.PutUint32(buf[:4], uint32(len(payload)))
	copy(buf[4:], payload)
	return buf
}

func readFull(r io.Reader, n int) ([]byte, error) {
	buf := make([]byte, n)
	_, err := io.ReadFull(r, buf)
	return buf, err
}

func ReadFrame(r io.Reader) ([]byte, error) {
	hdr, err := readFull(r, 4)
	if err != nil {
		return nil, err
	}
	n := binary.BigEndian.Uint32(hdr)
	return readFull(r, int(n))
}

func sendAll(w io.Writer, p []byte) error {
	for len(p) > 0 {
		n, err := w.Write(p)
		p = p[n:]
		if err != nil {
			return err
		}
		if n == 0 {
			return io.ErrShortWrite
		}
	}
	return nil
}

func Exchange(addr string, payload []byte) ([]byte, error) {
	c, err := net.DialTimeout("tcp", addr, 2*time.Second)
	if err != nil {
		return nil, err
	}
	defer c.Close()
	if err := sendAll(c, frame(payload)); err != nil {
		return nil, err
	}
	return ReadFrame(c)
}

func Classify(conn net.Conn) string {
	_ = conn.SetReadDeadline(time.Now().Add(150 * time.Millisecond))
	_, err := ReadFrame(conn)
	if err == nil {
		return "ok"
	}
	if ne, ok := err.(net.Error); ok && ne.Timeout() {
		return "timeout"
	}
	if err == io.EOF || err == io.ErrUnexpectedEOF {
		return "truncated"
	}
	return err.Error()
}

func PostHTTP(url, body string) (int, string, error) {
	resp, err := http.Post(url, "text/plain", stringsReader(body))
	if err != nil {
		return 0, "", err
	}
	defer resp.Body.Close()
	b, err := io.ReadAll(resp.Body)
	return resp.StatusCode, string(b), err
}

func stringsReader(s string) io.Reader { return bytes.NewReader([]byte(s)) }

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
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		panic(err)
	}
	go func() {
		for _, mode := range []string{"echo", "silent", "drop"} {
			conn, err := ln.Accept()
			if err != nil {
				return
			}
			switch mode {
			case "echo":
				msg, err := ReadFrame(conn)
				if err == nil {
					_ = sendAll(conn, frame(bytes.ToUpper(msg)))
				}
			case "silent":
				_ = conn.SetReadDeadline(time.Now().Add(2 * time.Second))
				buf := make([]byte, 1)
				_, _ = conn.Read(buf)
			default:
				_, _ = conn.Write([]byte{0, 0})
			}
			conn.Close()
		}
	}()

	addr := ln.Addr().String()
	msg, err := Exchange(addr, []byte("ping"))
	check("exchange", []any{string(msg), err}, []any{"PING", nil})

	c, err := net.Dial("tcp", addr)
	if err != nil {
		panic(err)
	}
	check("timeout", Classify(c), "timeout")
	c.Close()

	c, err = net.Dial("tcp", addr)
	if err != nil {
		panic(err)
	}
	check("truncated", Classify(c), "truncated")
	c.Close()
	ln.Close()

	mux := http.NewServeMux()
	mux.HandleFunc("/echo", func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		fmt.Fprintf(w, "echo:%s", body)
	})
	httpLn, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		panic(err)
	}
	srv := &http.Server{Handler: mux}
	go srv.Serve(httpLn)
	status, body, err := PostHTTP("http://"+httpLn.Addr().String()+"/echo", "hi")
	check("http", []any{status, body, err}, []any{200, "echo:hi", nil})
	srv.Close()
	if failed {
		os.Exit(1)
	}
}
```

</details>

Next: [17 — Advanced concurrency](17-advanced-concurrency.md)
