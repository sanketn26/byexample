# Go 06 — Structs and Methods

Go has no classes. You get structs (data), methods (functions with a
receiver), and embedding (composition that looks like inheritance). A name
is exported when it starts with an uppercase letter. The same rule covers
functions, types, and methods.

## A value receiver sees a copy

The method gets its own `Point`. Callers keep the original. If any method
on the type needs a pointer receiver, give them all pointer receivers: a
value stored in an interface has only the value-receiver methods.

```go file=n01.go
package main

import (
	"fmt"
	"math"
)

type Point struct{ X, Y float64 }

func (p Point) Dist(q Point) float64 { return math.Hypot(p.X-q.X, p.Y-q.Y) }

func main() {
	p := Point{3, 4}
	fmt.Println(p.X, p.Y, p.Dist(Point{}))
}
```

```text output
3 4 5
```

## `String` customises printing

A `String() string` method satisfies `fmt.Stringer`. `Println` calls it
instead of printing the fields.

```go file=n02.go
package main

import "fmt"

type Point struct{ X, Y float64 }

func (p Point) String() string { return fmt.Sprintf("(%g,%g)", p.X, p.Y) }

func main() {
	fmt.Println(Point{3, 4})
}
```

```text output
(3,4)
```

## A pointer receiver can modify

`Scale` writes the caller's fields. When `p` is a variable, `p.Scale(2)`
is short for `(&p).Scale(2)`. A pointer method is not in the method set of
a plain value inside an interface.

```go file=n03.go
package main

import "fmt"

type Point struct{ X, Y float64 }

func (p Point) String() string { return fmt.Sprintf("(%g,%g)", p.X, p.Y) }

func (p *Point) Scale(k float64) {
	p.X *= k
	p.Y *= k
}

func main() {
	p := Point{3, 4}
	p.Scale(2)
	fmt.Println(p)

	pp := &Point{1, 1}
	pp.Scale(3)
	fmt.Println(*pp, pp)
}
```

```text output
(6,8)
(3,3) (3,3)
```

## A method value binds the receiver

`pp.Scale` is a function that already knows which point to change. Calling
it is the same as calling the method.

```go file=n04.go
package main

import "fmt"

type Point struct{ X, Y float64 }

func (p Point) String() string { return fmt.Sprintf("(%g,%g)", p.X, p.Y) }

func (p *Point) Scale(k float64) {
	p.X *= k
	p.Y *= k
}

func main() {
	pp := &Point{1, 1}
	scale := pp.Scale
	scale(2)
	fmt.Println(pp)
}
```

```text output
(2,2)
```

## Assignment copies the struct

`q := p` duplicates the fields. `==` compares them, and it compiles only
when every field is comparable.

```go file=n05.go
package main

import "fmt"

type Point struct{ X, Y float64 }

func main() {
	p := Point{3, 4}
	q := p
	q.X = 0
	fmt.Println(p.X, Point{1, 2} == Point{1, 2})
}
```

```text output
3 true
```

## Embedding promotes fields and methods

`Dog` contains an `Animal`. `d.Name` and `d.Animal.Speak` are promoted, but
`Dog` is not an `Animal` and does not convert to one. `Speak` on `Dog`
overrides the promoted method; the inner one is still there under its type
name.

```go file=n06.go
package main

import "fmt"

type Animal struct{ Name string }

func (a Animal) Speak() string { return a.Name + " makes a sound" }

type Dog struct {
	Animal
	Breed string
}

func (d Dog) Speak() string { return d.Animal.Speak() + " (woof)" }

func main() {
	d := Dog{Animal{"Rex"}, "lab"}
	fmt.Println(d.Speak(), d.Name)
	fmt.Printf("%T\n", d)
}
```

```text output
Rex makes a sound (woof) Rex
main.Dog
```

## Unexported fields protect an invariant

`balance` is visible only inside the package. Callers go through
`NewAccount`, `Deposit`, and `Balance`, so a negative deposit can be
refused.

```go file=n07.go
package main

import "fmt"

type Account struct {
	owner   string
	balance int
}

func NewAccount(owner string) *Account { return &Account{owner: owner} }

func (a *Account) Deposit(n int) bool {
	if n <= 0 {
		return false
	}
	a.balance += n
	return true
}

func (a *Account) Balance() int { return a.balance }

func main() {
	acct := NewAccount("ada")
	acct.Deposit(50)
	fmt.Println(acct.Deposit(-1), acct.Balance())
}
```

```text output
false 50
```

## The zero value should be useful

Design the type so `var x T` is already valid. `%+v` prints field names,
including the zeros you did not set.

```go file=n08.go
package main

import "fmt"

type Config struct {
	Host string
	Port int
}

func main() {
	fmt.Printf("%+v\n", Config{"h", 80})
	var zero Config
	fmt.Printf("%+v\n", zero)
}
```

```text output
{Host:h Port:80}
{Host: Port:0}
```

## An anonymous struct needs no named type

The type is written at the variable. It is useful for a one-off shape that
no other function has to name.

```go file=n09.go
package main

import "fmt"

func main() {
	anon := struct {
		A int
		B string
	}{1, "x"}
	fmt.Println(anon)
}
```

```text output
{1 x}
```

## JSON uses tags and skips unexported fields

The tag renames the field. `omitempty` drops an empty exported field.
`age` starts with a lowercase letter, so `encoding/json` ignores it.

```go file=n10.go
package main

import (
	"encoding/json"
	"fmt"
)

type User struct {
	Name  string `json:"name"`
	Email string `json:"email,omitempty"`
	age   int
}

func main() {
	out, _ := json.Marshal(User{Name: "Ada", age: 3})
	fmt.Println(string(out))
}
```

```text output
{"name":"Ada"}
```

## Exercises

```go file=exercise.go
package main

import (
	"fmt"
	"os"
	"reflect"
)

// Stack is a LIFO stack of ints. The zero value must be ready to use.
type Stack struct {
	// TODO
}

// Push adds v. Pop removes and returns the top (ok=false when empty).
// Peek returns the top without removing. Len returns the size.
func (s *Stack) Push(v int)         {}
func (s *Stack) Pop() (int, bool)   { return 0, false }
func (s *Stack) Peek() (int, bool)  { return 0, false }
func (s *Stack) Len() int           { return -1 }

// Rect is a rectangle. Scale multiplies both sides in place.
type Rect struct{ W, H float64 }

func (r Rect) Area() float64      { return 0 }
func (r Rect) Perimeter() float64 { return 0 }
func (r *Rect) Scale(k float64)   {}

// Celsius is a named type; String renders one decimal and a unit, e.g. "36.6°C".
type Celsius float64

func (c Celsius) Fahrenheit() float64 { return 0 }
func (c Celsius) String() string       { return "" }

// Employee and Manager demonstrate embedding.
// Employee.Describe: "Ann earns 100"
// Manager.Describe:  "Ann earns 100, manages 3"
type Employee struct {
	Name   string
	Salary int
}

func (e Employee) Describe() string { return "" }

type Manager struct {
	Employee
	Reports int
}

func (m Manager) Describe() string { return "" }

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
	var s Stack
	_, ok := s.Pop()
	check("empty pop", ok, false)
	s.Push(1)
	s.Push(2)
	top, _ := s.Peek()
	check("peek", []int{top, s.Len()}, []int{2, 2})
	v, _ := s.Pop()
	check("pop", []int{v, s.Len()}, []int{2, 1})

	r := Rect{2, 3}
	r.Scale(2)
	check("rect", []float64{r.Area(), r.Perimeter()}, []float64{24, 20})

	c := Celsius(36.6)
	check("celsius", fmt.Sprint(c), "36.6°C")
	check("fahrenheit", Celsius(100).Fahrenheit(), 212.0)

	m := Manager{Employee{"Ann", 100}, 3}
	check("employee", m.Employee.Describe(), "Ann earns 100")
	check("manager", m.Describe(), "Ann earns 100, manages 3")
	if failed {
		os.Exit(1)
	}
}
```

<details><summary>Solution</summary>

```go file=solution.go
package main

import (
	"fmt"
	"os"
	"reflect"
)

type Stack struct {
	items []int
}

func (s *Stack) Push(v int) { s.items = append(s.items, v) }

func (s *Stack) Pop() (int, bool) {
	if len(s.items) == 0 {
		return 0, false
	}
	v := s.items[len(s.items)-1]
	s.items = s.items[:len(s.items)-1]
	return v, true
}

func (s *Stack) Peek() (int, bool) {
	if len(s.items) == 0 {
		return 0, false
	}
	return s.items[len(s.items)-1], true
}

func (s *Stack) Len() int { return len(s.items) }

type Rect struct{ W, H float64 }

func (r Rect) Area() float64      { return r.W * r.H }
func (r Rect) Perimeter() float64 { return 2 * (r.W + r.H) }
func (r *Rect) Scale(k float64) {
	r.W *= k
	r.H *= k
}

type Celsius float64

func (c Celsius) Fahrenheit() float64 { return float64(c)*9/5 + 32 }
func (c Celsius) String() string       { return fmt.Sprintf("%.1f°C", float64(c)) }

type Employee struct {
	Name   string
	Salary int
}

func (e Employee) Describe() string {
	return fmt.Sprintf("%s earns %d", e.Name, e.Salary)
}

type Manager struct {
	Employee
	Reports int
}

func (m Manager) Describe() string {
	return fmt.Sprintf("%s, manages %d", m.Employee.Describe(), m.Reports)
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
	var s Stack
	_, ok := s.Pop()
	check("empty pop", ok, false)
	s.Push(1)
	s.Push(2)
	top, _ := s.Peek()
	check("peek", []int{top, s.Len()}, []int{2, 2})
	v, _ := s.Pop()
	check("pop", []int{v, s.Len()}, []int{2, 1})

	r := Rect{2, 3}
	r.Scale(2)
	check("rect", []float64{r.Area(), r.Perimeter()}, []float64{24, 20})

	c := Celsius(36.6)
	check("celsius", fmt.Sprint(c), "36.6°C")
	check("fahrenheit", Celsius(100).Fahrenheit(), 212.0)

	m := Manager{Employee{"Ann", 100}, 3}
	check("employee", m.Employee.Describe(), "Ann earns 100")
	check("manager", m.Describe(), "Ann earns 100, manages 3")
	if failed {
		os.Exit(1)
	}
}
```

</details>

Next: [07 — Errors](07-errors.md)
