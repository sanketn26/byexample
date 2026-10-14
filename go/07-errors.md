# Go 07 — Errors

Errors are ordinary values returned from functions. There are no exceptions;
`panic` is for programmer bugs and truly unrecoverable states.

## Example

```go file=example.go
package main

import (
	"errors"
	"fmt"
	"strconv"
	"strings"
)

// Sentinel error: compare with errors.Is.
var ErrNotFound = errors.New("not found")

// Custom error type: extract with errors.As.
type ValidationError struct {
	Field, Msg string
}

func (e *ValidationError) Error() string { return e.Field + ": " + e.Msg }

func find(id int) (string, error) {
	if id == 0 {
		// %w wraps, preserving the chain for Is/As
		return "", fmt.Errorf("find %d: %w", id, ErrNotFound)
	}
	return "item" + strconv.Itoa(id), nil
}

func validate(name string) error {
	if name == "" {
		return &ValidationError{"name", "required"}
	}
	return nil
}

// The typed-nil trap: a nil *ValidationError in an error interface is NOT nil.
func mayFailBad(fail bool) error {
	var e *ValidationError
	if fail {
		e = &ValidationError{"x", "bad"}
	}
	return e
}

func mayFailGood(fail bool) error {
	if fail {
		return &ValidationError{"x", "bad"}
	}
	return nil
}

// recover turns a panic into an error, only inside a deferred function.
func safeDiv(a, b int) (res int, err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("recovered: %v", r)
		}
	}()
	return a / b, nil
}

func main() {
	_, err := find(0)
	fmt.Println(err)
	fmt.Println(errors.Is(err, ErrNotFound), errors.Unwrap(err) == ErrNotFound)

	if v, err := find(7); err == nil {
		fmt.Println(v)
	}

	err = validate("")
	var ve *ValidationError
	if errors.As(err, &ve) {
		fmt.Println("field:", ve.Field)
	}
	wrapped := fmt.Errorf("signup: %w", err)
	fmt.Println(wrapped, errors.As(wrapped, &ve))

	joined := errors.Join(errors.New("a"), errors.New("b"))
	fmt.Println(strings.ReplaceAll(joined.Error(), "\n", "|"))

	fmt.Println(mayFailBad(false) == nil, mayFailGood(false) == nil)

	_, err = strconv.Atoi("x")
	fmt.Println(errors.Is(err, strconv.ErrSyntax))

	fmt.Println(safeDiv(1, 0))
	fmt.Println(safeDiv(6, 3))
}
```

```text output
find 0: not found
true true
item7
field: name
signup: name: required true
a|b
false true
true
0 recovered: runtime error: integer divide by zero
2 <nil>
```

## Details that bite

- Always check `err` immediately. Handle it **or** return it, with context:
  `fmt.Errorf("load config: %w", err)`.
- Do not both log and return an error; the caller will log it again.
- Never declare a function result as a concrete pointer error type
  (`*MyErr`) and return it as `error` unless you return a literal `nil`
  otherwise — see `mayFailBad`.
- Compare with `errors.Is` / `errors.As`, not `==` or type assertions, so
  wrapping keeps working.
- Error strings are lowercase with no trailing punctuation: they get
  embedded in longer messages.
- `panic` unwinds running deferred functions; an unrecovered panic crashes
  the program. Libraries should not let panics escape their public API.

## Exercises

```go file=exercise.go
package main

import (
	"errors"
	"fmt"
	"os"
	"reflect"
)

var ErrNotPositive = errors.New("not positive")

// ParsePositive parses a decimal integer and requires it to be > 0.
// A parse failure must wrap the underlying strconv error with context;
// a non-positive value must wrap ErrNotPositive.
func ParsePositive(s string) (int, error) {
	return 0, nil // TODO
}

// DivError reports division by zero and carries the numerator.
type DivError struct {
	Num int
}

func (e *DivError) Error() string { return "" } // TODO

// Divide returns a/b or a *DivError when b == 0.
func Divide(a, b int) (int, error) {
	return 0, nil // TODO
}

// Retry calls fn up to attempts times, stopping at the first success.
// If every attempt fails, return all errors combined (errors.Join).
func Retry(attempts int, fn func(i int) error) error {
	return nil // TODO
}

// SafeCall runs fn and converts a panic into a returned error.
func SafeCall(fn func()) (err error) {
	fn() // TODO
	return nil
}

var failed bool

func check(label string, got, want any) {
	if reflect.DeepEqual(got, want) {
		fmt.Println("PASS", label)
		return
	}
	failed = true
	fmt.Printf("FAIL %s: got %v, want %v\n", label, got, want)
}

func main() {
	n, err := ParsePositive("12")
	check("parse ok", []any{n, err}, []any{12, error(nil)})
	_, err = ParsePositive("-5")
	check("not positive", errors.Is(err, ErrNotPositive), true)
	_, err = ParsePositive("abc")
	check("parse error", err != nil && !errors.Is(err, ErrNotPositive), true)

	_, err = Divide(7, 0)
	var de *DivError
	check("div error", errors.As(err, &de) && de.Num == 7, true)
	q, err := Divide(7, 2)
	check("divide", []any{q, err}, []any{3, error(nil)})

	calls := 0
	err = Retry(3, func(i int) error {
		calls++
		if i < 2 {
			return fmt.Errorf("fail %d", i)
		}
		return nil
	})
	check("retry success", []any{err, calls}, []any{error(nil), 3})
	err = Retry(2, func(i int) error { return fmt.Errorf("e%d", i) })
	check("retry fail", err != nil && errors.Unwrap(err) == nil && err.Error() == "e0\ne1", true)

	err = SafeCall(func() { var m map[string]int; m["a"] = 1 })
	check("safecall", err != nil, true)
	check("safecall ok", SafeCall(func() {}), error(nil))
	if failed {
		os.Exit(1)
	}
}
```

<details><summary>Solution</summary>

```go file=solution.go
package main

import (
	"errors"
	"fmt"
	"os"
	"reflect"
	"strconv"
)

var ErrNotPositive = errors.New("not positive")

func ParsePositive(s string) (int, error) {
	n, err := strconv.Atoi(s)
	if err != nil {
		return 0, fmt.Errorf("parse positive: %w", err)
	}
	if n <= 0 {
		return 0, fmt.Errorf("parse positive %d: %w", n, ErrNotPositive)
	}
	return n, nil
}

type DivError struct {
	Num int
}

func (e *DivError) Error() string { return fmt.Sprintf("divide %d by zero", e.Num) }

func Divide(a, b int) (int, error) {
	if b == 0 {
		return 0, &DivError{Num: a}
	}
	return a / b, nil
}

func Retry(attempts int, fn func(i int) error) error {
	var errs []error
	for i := 0; i < attempts; i++ {
		err := fn(i)
		if err == nil {
			return nil
		}
		errs = append(errs, err)
	}
	return errors.Join(errs...)
}

func SafeCall(fn func()) (err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("panic: %v", r)
		}
	}()
	fn()
	return nil
}

var failed bool

func check(label string, got, want any) {
	if reflect.DeepEqual(got, want) {
		fmt.Println("PASS", label)
		return
	}
	failed = true
	fmt.Printf("FAIL %s: got %v, want %v\n", label, got, want)
}

func main() {
	n, err := ParsePositive("12")
	check("parse ok", []any{n, err}, []any{12, error(nil)})
	_, err = ParsePositive("-5")
	check("not positive", errors.Is(err, ErrNotPositive), true)
	_, err = ParsePositive("abc")
	check("parse error", err != nil && !errors.Is(err, ErrNotPositive), true)

	_, err = Divide(7, 0)
	var de *DivError
	check("div error", errors.As(err, &de) && de.Num == 7, true)
	q, err := Divide(7, 2)
	check("divide", []any{q, err}, []any{3, error(nil)})

	calls := 0
	err = Retry(3, func(i int) error {
		calls++
		if i < 2 {
			return fmt.Errorf("fail %d", i)
		}
		return nil
	})
	check("retry success", []any{err, calls}, []any{error(nil), 3})
	err = Retry(2, func(i int) error { return fmt.Errorf("e%d", i) })
	check("retry fail", err != nil && errors.Unwrap(err) == nil && err.Error() == "e0\ne1", true)

	err = SafeCall(func() { var m map[string]int; m["a"] = 1 })
	check("safecall", err != nil, true)
	check("safecall ok", SafeCall(func() {}), error(nil))
	if failed {
		os.Exit(1)
	}
}
```

</details>

Next: [08 — Pointers and memory](08-pointers-memory.md)
