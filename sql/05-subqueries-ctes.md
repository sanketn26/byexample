# SQL 05 — Subqueries and CTEs

A query can contain queries. A **scalar subquery** returns one value; a
**row-set subquery** (`IN`, `EXISTS`) returns a set; a **derived table** sits
in `FROM`. A **CTE** (`WITH name AS (...)`) gives a subquery a name so a
long query reads top to bottom.

## Example

```sql file=example.sql
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, salary INTEGER);
CREATE TABLE project (id INTEGER PRIMARY KEY, name TEXT, lead_id INTEGER);
INSERT INTO emp VALUES
  (1, 'Ada',   'eng', 150), (2, 'Linus', 'eng', 120), (3, 'Grace', 'eng', 130),
  (4, 'Don',   'sales', 90), (5, 'Peggy', 'sales', 95), (6, 'Zed', 'ops', 70);
INSERT INTO project VALUES (1, 'compiler', 1), (2, 'kernel', 2), (3, 'ads', NULL);

.headers on
-- 1. Scalar subquery: one row, one column, used like a value
SELECT name, salary, salary - (SELECT avg(salary) FROM emp) AS vs_avg
FROM emp ORDER BY salary DESC LIMIT 2;

-- 2. IN with a subquery
SELECT name FROM emp WHERE id IN (SELECT lead_id FROM project) ORDER BY name;

-- 3. EXISTS: "is there at least one matching row?"; NULL-safe
SELECT name FROM emp e
WHERE EXISTS (SELECT 1 FROM project p WHERE p.lead_id = e.id) ORDER BY name;
SELECT name FROM emp e
WHERE NOT EXISTS (SELECT 1 FROM project p WHERE p.lead_id = e.id) ORDER BY name;

-- 4. Correlated subquery: refers to the outer row (runs "per row")
SELECT name, dept FROM emp e
WHERE salary = (SELECT max(salary) FROM emp WHERE dept = e.dept)
ORDER BY dept;

-- 5. Derived table: a subquery in FROM, joined like a table
SELECT e.name, e.salary, d.avg_sal
FROM emp e JOIN (SELECT dept, round(avg(salary)) AS avg_sal FROM emp GROUP BY dept) d
  ON d.dept = e.dept
WHERE e.salary > d.avg_sal ORDER BY e.name;

-- 6. CTE: the same thing, named and readable
WITH dept_avg AS (
  SELECT dept, avg(salary) AS avg_sal FROM emp GROUP BY dept
), above AS (
  SELECT e.name, e.dept FROM emp e JOIN dept_avg d USING (dept)
  WHERE e.salary > d.avg_sal
)
SELECT dept, group_concat(name, ',') AS names FROM above GROUP BY dept ORDER BY dept;

-- 7. A CTE can be used more than once in the main query
WITH totals AS (SELECT dept, sum(salary) AS pay FROM emp GROUP BY dept)
SELECT dept, pay, round(100.0 * pay / (SELECT sum(pay) FROM totals)) AS pct
FROM totals ORDER BY pay DESC;

-- 8. ANY/ALL style comparisons via aggregates
SELECT name FROM emp WHERE salary > (SELECT max(salary) FROM emp WHERE dept = 'sales')
ORDER BY name;

-- 9. The NOT IN trap: one NULL in the list and nothing matches
SELECT count(*) AS with_not_in
FROM emp WHERE id NOT IN (SELECT lead_id FROM project);
SELECT count(*) AS with_not_exists
FROM emp e WHERE NOT EXISTS (SELECT 1 FROM project p WHERE p.lead_id = e.id);

-- 10. Subquery in the SELECT list: a per-row lookup
SELECT p.name AS project,
       (SELECT name FROM emp WHERE id = p.lead_id) AS lead
FROM project p ORDER BY p.id;
```

```text output
name|salary|vs_avg
Ada|150|40.8333333333333
Grace|130|20.8333333333333
name
Ada
Linus
name
Ada
Linus
name
Don
Grace
Peggy
Zed
name|dept
Ada|eng
Zed|ops
Peggy|sales
name|salary|avg_sal
Ada|150|133.0
Peggy|95|93.0
dept|names
eng|Ada
sales|Peggy
dept|pay|pct
eng|400|61.0
sales|185|28.0
ops|70|11.0
name
Ada
Grace
Linus
with_not_in
0
with_not_exists
4
project|lead
compiler|Ada
kernel|Linus
ads|
```

## Details that bite

- A scalar subquery that returns **more than one row** is an error in
  PostgreSQL; SQLite silently uses the first. Make it return exactly one
  (aggregate, `LIMIT 1`, or a unique key).
- `x NOT IN (subquery)` returns no rows if the subquery yields any NULL.
  Use `NOT EXISTS`.
- A correlated subquery is conceptually re-run per outer row. Databases
  often rewrite it to a join; if not, it can be very slow. A join with
  `GROUP BY` or a window function (next lesson) is often faster.
- CTEs are for **readability**. PostgreSQL before 12 treated them as
  optimisation fences (always materialised); SQLite and newer PostgreSQL
  inline them unless told otherwise (`MATERIALIZED` / `NOT MATERIALIZED`).
- A CTE name lives for **one statement**. For reuse across statements, make
  a view (lesson 11) or a temp table.
- `SELECT 1` inside `EXISTS` is a convention; the column list is ignored.
- Column names inside a derived table must be unique and aliased
  expressions need names (`AS avg_sal`).

## Exercises

```sql file=exercise.sql
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, salary INTEGER);
CREATE TABLE project (id INTEGER PRIMARY KEY, name TEXT, lead_id INTEGER);
INSERT INTO emp VALUES
  (1, 'Ada',   'eng', 150), (2, 'Linus', 'eng', 120), (3, 'Grace', 'eng', 130),
  (4, 'Don',   'sales', 90), (5, 'Peggy', 'sales', 95), (6, 'Zed', 'ops', 70);
INSERT INTO project VALUES (1, 'compiler', 1), (2, 'kernel', 2), (3, 'ads', NULL);

-- q1: employees who earn more than the company average. Column: name (by name).
CREATE VIEW q1 AS SELECT NULL AS name WHERE 0;                          -- TODO

-- q2: employees who lead NO project, using NOT EXISTS. Column: name (by name).
CREATE VIEW q2 AS SELECT NULL AS name WHERE 0;                          -- TODO

-- q3: for each department, the name of its lowest-paid employee.
--     Columns: dept, name (by dept). Use a correlated subquery.
CREATE VIEW q3 AS SELECT NULL AS dept, NULL AS name WHERE 0;            -- TODO

-- q4: using a CTE, departments whose total pay is over 200. Columns:
--     dept, pay (by dept).
CREATE VIEW q4 AS SELECT NULL AS dept, NULL AS pay WHERE 0;             -- TODO

-- q5: the second-highest salary (a single value). Column: salary.
CREATE VIEW q5 AS SELECT NULL AS salary;                                -- TODO

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('q1', (SELECT group_concat(name) FROM q1) IS 'Ada,Grace,Linus');
INSERT INTO t VALUES ('q2', (SELECT group_concat(name) FROM q2) IS 'Don,Grace,Peggy,Zed');
INSERT INTO t VALUES ('q3', (SELECT group_concat(dept || ':' || name) FROM q3) IS 'eng:Linus,ops:Zed,sales:Don');
INSERT INTO t VALUES ('q4', (SELECT group_concat(dept || '=' || pay) FROM q4) IS 'eng=400');
INSERT INTO t VALUES ('q5', (SELECT salary FROM q5) IS 130);
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

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('q1', (SELECT group_concat(name) FROM q1) IS 'Ada,Grace,Linus');
INSERT INTO t VALUES ('q2', (SELECT group_concat(name) FROM q2) IS 'Don,Grace,Peggy,Zed');
INSERT INTO t VALUES ('q3', (SELECT group_concat(dept || ':' || name) FROM q3) IS 'eng:Linus,ops:Zed,sales:Don');
INSERT INTO t VALUES ('q4', (SELECT group_concat(dept || '=' || pay) FROM q4) IS 'eng=400');
INSERT INTO t VALUES ('q5', (SELECT salary FROM q5) IS 130);
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [06 — Window functions](06-window-functions.md)
