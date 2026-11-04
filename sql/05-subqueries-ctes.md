# SQL 05 — Subqueries and CTEs

A query can contain queries. A scalar subquery returns one value. `IN` and
`EXISTS` test a set. A derived table sits in `FROM`. A CTE (`WITH name AS
(...)`) names a subquery so a long query reads top to bottom.

## A scalar subquery is one value

It must return one row and one column. More than one row is an error. Make
it one value with an aggregate, `LIMIT 1`, or a unique key. `avg(integer)`
is `numeric`, so the difference prints at full scale. Subtracting the
average shows who sits above it.

```sql file=n01.sql
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, salary INTEGER);
INSERT INTO emp VALUES
  (1, 'Ada',   'eng', 150), (2, 'Linus', 'eng', 120), (3, 'Grace', 'eng', 130),
  (4, 'Don',   'sales', 90), (5, 'Peggy', 'sales', 95), (6, 'Zed', 'ops', 70);
-- expect-error
SELECT (SELECT salary FROM emp);
.headers on
SELECT name, salary, salary - (SELECT avg(salary) FROM emp) AS vs_avg
FROM emp ORDER BY salary DESC LIMIT 2;
```

```text output
Error: more than one row returned by a subquery used as an expression
name|salary|vs_avg
Ada|150|40.8333333333333333
Grace|130|20.8333333333333333
```

## IN tests membership in a subquery

The inner query returns the set of lead ids. The outer query keeps
employees whose id is in that set. A NULL lead id never matches, because
`NULL = id` is unknown.

```sql file=n02.sql
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, salary INTEGER);
CREATE TABLE project (id INTEGER PRIMARY KEY, name TEXT, lead_id INTEGER);
INSERT INTO emp VALUES
  (1, 'Ada',   'eng', 150), (2, 'Linus', 'eng', 120), (3, 'Grace', 'eng', 130),
  (4, 'Don',   'sales', 90), (5, 'Peggy', 'sales', 95), (6, 'Zed', 'ops', 70);
INSERT INTO project VALUES (1, 'compiler', 1), (2, 'kernel', 2), (3, 'ads', NULL);
.headers on
SELECT name FROM emp WHERE id IN (SELECT lead_id FROM project) ORDER BY name;
```

```text output
name
Ada
Linus
```

## EXISTS asks whether any row matches

`SELECT 1` is a convention. The column list is ignored. `EXISTS` is
NULL-safe: it cares that a row exists, not that values compare equal.
`NOT EXISTS` is the safe way to say "no match".

```sql file=n03.sql
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, salary INTEGER);
CREATE TABLE project (id INTEGER PRIMARY KEY, name TEXT, lead_id INTEGER);
INSERT INTO emp VALUES
  (1, 'Ada',   'eng', 150), (2, 'Linus', 'eng', 120), (3, 'Grace', 'eng', 130),
  (4, 'Don',   'sales', 90), (5, 'Peggy', 'sales', 95), (6, 'Zed', 'ops', 70);
INSERT INTO project VALUES (1, 'compiler', 1), (2, 'kernel', 2), (3, 'ads', NULL);
.headers on
SELECT name FROM emp e
WHERE EXISTS (SELECT 1 FROM project p WHERE p.lead_id = e.id) ORDER BY name;
SELECT name FROM emp e
WHERE NOT EXISTS (SELECT 1 FROM project p WHERE p.lead_id = e.id) ORDER BY name;
```

```text output
name
Ada
Linus
name
Don
Grace
Peggy
Zed
```

## A correlated subquery sees the outer row

The inner query mentions `e.dept`, so it is re-run for each outer row.
The database often rewrites that as a join. When it does not, the query
can be very slow. A join with `GROUP BY`, or a window function (lesson 06),
is often faster.

```sql file=n04.sql
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, salary INTEGER);
INSERT INTO emp VALUES
  (1, 'Ada',   'eng', 150), (2, 'Linus', 'eng', 120), (3, 'Grace', 'eng', 130),
  (4, 'Don',   'sales', 90), (5, 'Peggy', 'sales', 95), (6, 'Zed', 'ops', 70);
.headers on
SELECT name, dept FROM emp e
WHERE salary = (SELECT max(salary) FROM emp WHERE dept = e.dept)
ORDER BY dept;
```

```text output
name|dept
Ada|eng
Zed|ops
Peggy|sales
```

## A derived table is a subquery in FROM

It needs a name, and so does every expression. Column names inside it must
be unique. Then you join it like any other table. `round` of an average
returns `numeric` with no decimal places.

```sql file=n05.sql
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, salary INTEGER);
INSERT INTO emp VALUES
  (1, 'Ada',   'eng', 150), (2, 'Linus', 'eng', 120), (3, 'Grace', 'eng', 130),
  (4, 'Don',   'sales', 90), (5, 'Peggy', 'sales', 95), (6, 'Zed', 'ops', 70);
.headers on
SELECT e.name, e.salary, d.avg_sal
FROM emp e JOIN (SELECT dept, round(avg(salary)) AS avg_sal FROM emp GROUP BY dept) d
  ON d.dept = e.dept
WHERE e.salary > d.avg_sal ORDER BY e.name;
```

```text output
name|salary|avg_sal
Ada|150|133
Peggy|95|93
```

## A CTE names a subquery

`WITH` is for readability. The same derived table reads top to bottom once
it has a name. PostgreSQL inlines a CTE by default. `MATERIALIZED` forces
it to run once and be reused. `NOT MATERIALIZED` insists on inlining. The
result is the same either way; only the plan changes. `string_agg` needs
a separator, and `ORDER BY` inside it if the list order matters.

```sql file=n06.sql
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, salary INTEGER);
INSERT INTO emp VALUES
  (1, 'Ada',   'eng', 150), (2, 'Linus', 'eng', 120), (3, 'Grace', 'eng', 130),
  (4, 'Don',   'sales', 90), (5, 'Peggy', 'sales', 95), (6, 'Zed', 'ops', 70);
WITH dept_avg AS (
  SELECT dept, avg(salary) AS avg_sal FROM emp GROUP BY dept
), above AS (
  SELECT e.name, e.dept FROM emp e JOIN dept_avg d USING (dept)
  WHERE e.salary > d.avg_sal
)
SELECT dept, string_agg(name, ',' ORDER BY name) AS names
FROM above GROUP BY dept ORDER BY dept;
```

```text output
eng|Ada
sales|Peggy
```

## The same CTE can be referenced twice

Both references see the same statement's result. Here the percentage
divides by the sum of the CTE, not by a second scan you wrote by hand.
`round` with no precision returns a whole number.

```sql file=n07.sql
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, salary INTEGER);
INSERT INTO emp VALUES
  (1, 'Ada',   'eng', 150), (2, 'Linus', 'eng', 120), (3, 'Grace', 'eng', 130),
  (4, 'Don',   'sales', 90), (5, 'Peggy', 'sales', 95), (6, 'Zed', 'ops', 70);
WITH totals AS (SELECT dept, sum(salary) AS pay FROM emp GROUP BY dept)
SELECT dept, pay, round(100.0 * pay / (SELECT sum(pay) FROM totals)) AS pct
FROM totals ORDER BY pay DESC;
```

```text output
eng|400|61
sales|185|28
ops|70|11
```

## A CTE name lives for one statement

The next statement cannot see it. For reuse across statements, make a view
(lesson 11) or a temporary table. A temporary table lasts for the session,
not for the next connection.

```sql file=n08.sql
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, salary INTEGER);
INSERT INTO emp VALUES
  (1, 'Ada',   'eng', 150), (2, 'Linus', 'eng', 120), (3, 'Grace', 'eng', 130),
  (4, 'Don',   'sales', 90), (5, 'Peggy', 'sales', 95), (6, 'Zed', 'ops', 70);
WITH totals AS (SELECT dept, sum(salary) AS pay FROM emp GROUP BY dept)
SELECT dept FROM totals ORDER BY dept;
-- expect-error
SELECT dept FROM totals;
```

```text output
eng
ops
sales
Error: relation "totals" does not exist
```

## ALL means greater than every value

`salary > ALL (subquery)` keeps rows greater than every value in the set.
`> ANY` means greater than at least one. A NULL in that set makes `ALL`
unknown for every row, the same trap as `NOT IN`. `salary > max(...)`
ignores NULL and reads as one comparison. Prefer it.

```sql file=n09.sql
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, salary INTEGER);
INSERT INTO emp VALUES
  (1, 'Ada',   'eng', 150), (2, 'Linus', 'eng', 120), (3, 'Grace', 'eng', 130),
  (4, 'Don',   'sales', 90), (5, 'Peggy', 'sales', 95), (6, 'Zed', 'ops', 70);
.headers on
SELECT name FROM emp WHERE salary > (SELECT max(salary) FROM emp WHERE dept = 'sales')
ORDER BY name;
SELECT name FROM emp WHERE salary > ALL (SELECT salary FROM emp WHERE dept = 'sales')
ORDER BY name;
```

```text output
name
Ada
Grace
Linus
name
Ada
Grace
Linus
```

## NOT IN collapses when the subquery yields NULL

One NULL in the list and `x NOT IN (...)` is unknown for every x, so the
query returns no rows. `NOT EXISTS` still returns the four people who lead
nothing. The ads project has a NULL lead, which is enough to spring the trap.

```sql file=n10.sql
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, salary INTEGER);
CREATE TABLE project (id INTEGER PRIMARY KEY, name TEXT, lead_id INTEGER);
INSERT INTO emp VALUES
  (1, 'Ada',   'eng', 150), (2, 'Linus', 'eng', 120), (3, 'Grace', 'eng', 130),
  (4, 'Don',   'sales', 90), (5, 'Peggy', 'sales', 95), (6, 'Zed', 'ops', 70);
INSERT INTO project VALUES (1, 'compiler', 1), (2, 'kernel', 2), (3, 'ads', NULL);
.headers on
SELECT count(*) AS with_not_in
FROM emp WHERE id NOT IN (SELECT lead_id FROM project);
SELECT count(*) AS with_not_exists
FROM emp e WHERE NOT EXISTS (SELECT 1 FROM project p WHERE p.lead_id = e.id);
```

```text output
with_not_in
0
with_not_exists
4
```

## A subquery in the SELECT list is a per-row lookup

It runs as a scalar subquery for each outer row. A missing lead is NULL,
which prints as an empty field. This is another correlated subquery, so
the same speed warning applies. More than one matching lead would be an
error, same as any other scalar subquery.

```sql file=n11.sql
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, salary INTEGER);
CREATE TABLE project (id INTEGER PRIMARY KEY, name TEXT, lead_id INTEGER);
INSERT INTO emp VALUES
  (1, 'Ada',   'eng', 150), (2, 'Linus', 'eng', 120), (3, 'Grace', 'eng', 130),
  (4, 'Don',   'sales', 90), (5, 'Peggy', 'sales', 95), (6, 'Zed', 'ops', 70);
INSERT INTO project VALUES (1, 'compiler', 1), (2, 'kernel', 2), (3, 'ads', NULL);
.headers on
SELECT p.name AS project,
       (SELECT name FROM emp WHERE id = p.lead_id) AS lead
FROM project p ORDER BY p.id;
```

```text output
project|lead
compiler|Ada
kernel|Linus
ads|
```

## Exercises

```sql file=exercise.sql
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, salary INTEGER);
CREATE TABLE project (id INTEGER PRIMARY KEY, name TEXT, lead_id INTEGER);
INSERT INTO emp VALUES
  (1, 'Ada',   'eng', 150), (2, 'Linus', 'eng', 120), (3, 'Grace', 'eng', 130),
  (4, 'Don',   'sales', 90), (5, 'Peggy', 'sales', 95), (6, 'Zed', 'ops', 70);
INSERT INTO project VALUES (1, 'compiler', 1), (2, 'kernel', 2), (3, 'ads', NULL);

-- q1: employees who earn more than the company average. Column: name (by name).
CREATE VIEW q1 AS SELECT NULL::TEXT AS name WHERE false;                -- TODO

-- q2: employees who lead NO project, using NOT EXISTS. Column: name (by name).
CREATE VIEW q2 AS SELECT NULL::TEXT AS name WHERE false;                -- TODO

-- q3: for each department, the name of its lowest-paid employee.
--     Columns: dept, name (by dept). Use a correlated subquery.
CREATE VIEW q3 AS SELECT NULL::TEXT AS dept, NULL::TEXT AS name WHERE false;  -- TODO

-- q4: using a CTE, departments whose total pay is over 200. Columns:
--     dept, pay (by dept).
CREATE VIEW q4 AS SELECT NULL::TEXT AS dept, NULL::BIGINT AS pay WHERE false;  -- TODO

-- q5: the second-highest salary (a single value). Column: salary.
CREATE VIEW q5 AS SELECT NULL::INTEGER AS salary;                       -- TODO

CREATE TABLE t (name TEXT, ok BOOLEAN CHECK (ok));
INSERT INTO t VALUES ('q1', (SELECT string_agg(name, ',' ORDER BY name) FROM q1) IS NOT DISTINCT FROM 'Ada,Grace,Linus');
INSERT INTO t VALUES ('q2', (SELECT string_agg(name, ',' ORDER BY name) FROM q2) IS NOT DISTINCT FROM 'Don,Grace,Peggy,Zed');
INSERT INTO t VALUES ('q3', (SELECT string_agg(dept || ':' || name, ',' ORDER BY dept) FROM q3) IS NOT DISTINCT FROM 'eng:Linus,ops:Zed,sales:Don');
INSERT INTO t VALUES ('q4', (SELECT string_agg(dept || '=' || pay, ',' ORDER BY dept) FROM q4) IS NOT DISTINCT FROM 'eng=400');
INSERT INTO t VALUES ('q5', (SELECT salary FROM q5) IS NOT DISTINCT FROM 130);
SELECT 'PASS ' || name FROM t;
```

<details><summary>Solution</summary>

```sql file=solution.sql
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, salary INTEGER);
CREATE TABLE project (id INTEGER PRIMARY KEY, name TEXT, lead_id INTEGER);
INSERT INTO emp VALUES
  (1, 'Ada',   'eng', 150), (2, 'Linus', 'eng', 120), (3, 'Grace', 'eng', 130),
  (4, 'Don',   'sales', 90), (5, 'Peggy', 'sales', 95), (6, 'Zed', 'ops', 70);
INSERT INTO project VALUES (1, 'compiler', 1), (2, 'kernel', 2), (3, 'ads', NULL);

CREATE VIEW q1 AS
  SELECT name FROM emp WHERE salary > (SELECT avg(salary) FROM emp) ORDER BY name;
CREATE VIEW q2 AS
  SELECT name FROM emp e
  WHERE NOT EXISTS (SELECT 1 FROM project p WHERE p.lead_id = e.id) ORDER BY name;
CREATE VIEW q3 AS
  SELECT dept, name FROM emp e
  WHERE salary = (SELECT min(salary) FROM emp WHERE dept = e.dept) ORDER BY dept;
CREATE VIEW q4 AS
  WITH totals AS (SELECT dept, sum(salary) AS pay FROM emp GROUP BY dept)
  SELECT dept, pay FROM totals WHERE pay > 200 ORDER BY dept;
CREATE VIEW q5 AS
  SELECT max(salary) AS salary FROM emp WHERE salary < (SELECT max(salary) FROM emp);

CREATE TABLE t (name TEXT, ok BOOLEAN CHECK (ok));
INSERT INTO t VALUES ('q1', (SELECT string_agg(name, ',' ORDER BY name) FROM q1) IS NOT DISTINCT FROM 'Ada,Grace,Linus');
INSERT INTO t VALUES ('q2', (SELECT string_agg(name, ',' ORDER BY name) FROM q2) IS NOT DISTINCT FROM 'Don,Grace,Peggy,Zed');
INSERT INTO t VALUES ('q3', (SELECT string_agg(dept || ':' || name, ',' ORDER BY dept) FROM q3) IS NOT DISTINCT FROM 'eng:Linus,ops:Zed,sales:Don');
INSERT INTO t VALUES ('q4', (SELECT string_agg(dept || '=' || pay, ',' ORDER BY dept) FROM q4) IS NOT DISTINCT FROM 'eng=400');
INSERT INTO t VALUES ('q5', (SELECT salary FROM q5) IS NOT DISTINCT FROM 130);
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [06 — Window functions](06-window-functions.md)
