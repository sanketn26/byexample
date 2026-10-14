# Go 06 — Structs and Methods

Go has no classes. You get structs (data), methods (functions with a
receiver), and embedding (composition that looks like inheritance).

## Example

```go file=example.go
package main

import (
	"encoding/json"
	"fmt"
	"math"
)

type Point struct{ X, Y float64 }

// Value receiver: works on a copy.
func (p Point) Dist(q Point) float64 { return math.Hypot(p.X-q.X, p.Y-q.Y) }

// Pointer receiver: can modify the original.
func (p *Point) Scale(k float64) {
	p.X *= k
	p.Y *= k
}

// Implementing fmt.Stringer customises printing.
func (p Point) String() string { return fmt.Sprintf("(%g,%g)", p.X, p.Y) }

type Config struct {
	Host string
	Port int
}

type Animal struct{ Name string }

func (a Animal) Speak() string { return a.Name + " makes a sound" }

// Embedding promotes the fields and methods of Animal into Dog.
type Dog struct {
	Animal
	Breed string
}

func (d Dog) Speak() string { return d.Animal.Speak() + " (woof)" }

// Keep invariants with unexported fields and a constructor.
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

type User struct {
	Name  string `json:"name"`
	Email string `json:"email,omitempty"`
	age   int    // unexported: ignored by encoding/json
}

func main() {
	p := Point{3, 4}
	fmt.Println(p, p.Dist(Point{}))
	p.Scale(2) // p is addressable, so Go takes &p for you
	fmt.Println(p)

	pp := &Point{1, 1}
	pp.Scale(3)
	fmt.Println(*pp, pp)

	scale := pp.Scale // method value bound to pp
	scale(2)
	fmt.Println(pp)

	q := p // structs are copied on assignment
	q.X = 0
	fmt.Println(p.X, Point{1, 2} == Point{1, 2})

	fmt.Printf("%+v\n", Config{"h", 80})
	var zero Config
	fmt.Printf("%+v\n", zero)

	d := Dog{Animal{"Rex"}, "lab"}
	fmt.Println(d.Speak(), d.Name)

	acct := NewAccount("ada")
	acct.Deposit(50)
	fmt.Println(acct.Deposit(-1), acct.Balance())

	anon := struct {
		A int
		B string
	}{1, "x"}
	fmt.Println(anon)

	out, _ := json.Marshal(User{Name: "Ada", age: 3})
	fmt.Println(string(out))
}
```

```text output
(3,4) 5
(6,8)
(3,3) (3,3)
(6,6)
6 true
{Host:h Port:80}
{Host: Port:0}
Rex makes a sound (woof) Rex
false 50
{1 x}
{"name":"Ada"}
```

## Details that bite

- Choose receivers consistently: if any method needs a pointer receiver
  (mutation, or a big struct), use pointer receivers for all of them.
- A value stored in an interface only has the *value-receiver* methods; the
  pointer type has both. This is why `var s Shape = &Rect{}` is often
  required.
- Embedding is not inheritance: `Dog` is not an `Animal`. You cannot pass a
  `Dog` where an `Animal` is wanted, only call promoted methods.
- Struct comparison with `==` works only if all fields are comparable.
- Zero values should be useful. Design types so `var x T` works.
- Fields are exported if they start with an uppercase letter; the same rule
  governs functions, types and methods.

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
