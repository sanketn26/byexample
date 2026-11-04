# SQL 04 — Joins

Data lives in several tables, linked by keys. A join combines rows where a
condition holds. Pick the join by what should happen to rows that have no
match. Alias every column once two tables are in play (`e.name`). A name
that exists on both tables is an error.

## INNER JOIN keeps only matches

`NULL` never equals `NULL`, so a NULL `dept_id` matches no department.
That is usually what you want. `JOIN ... USING (col)` merges same-named
columns. `NATURAL JOIN` joins on every shared name and breaks when someone
adds a column. Do not use it.

```sql file=n01.sql
CREATE TABLE dept (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE emp  (id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER, boss_id INTEGER, salary INTEGER);
INSERT INTO dept VALUES (1, 'Eng'), (2, 'Sales'), (3, 'Legal');
INSERT INTO emp VALUES
  (1, 'Ada',   1, NULL, 150),
  (2, 'Linus', 1, 1,    120),
  (3, 'Grace', 1, 1,    130),
  (4, 'Don',   2, 1,     90),
  (5, 'Zed',   NULL, 4,  70);
-- expect-error
SELECT name FROM emp JOIN dept ON dept.id = emp.dept_id;
.headers on
SELECT e.name AS emp, d.name AS dept
FROM emp e JOIN dept d ON d.id = e.dept_id
ORDER BY e.id;
```

```text output
Error: column reference "name" is ambiguous
emp|dept
Ada|Eng
Linus|Eng
Grace|Eng
Don|Sales
```

## LEFT JOIN keeps every left row

The right side is NULL when nothing matches. `RIGHT JOIN` is the same idea
with the tables swapped. Prefer `LEFT`: the preserved table is the one you
wrote first.

```sql file=n02.sql
CREATE TABLE dept (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE emp  (id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER, boss_id INTEGER, salary INTEGER);
INSERT INTO dept VALUES (1, 'Eng'), (2, 'Sales'), (3, 'Legal');
INSERT INTO emp VALUES
  (1, 'Ada',   1, NULL, 150),
  (2, 'Linus', 1, 1,    120),
  (3, 'Grace', 1, 1,    130),
  (4, 'Don',   2, 1,     90),
  (5, 'Zed',   NULL, 4,  70);
.headers on
SELECT e.name AS emp, d.name AS dept
FROM emp e LEFT JOIN dept d ON d.id = e.dept_id
ORDER BY e.id;
```

```text output
emp|dept
Ada|Eng
Linus|Eng
Grace|Eng
Don|Sales
Zed|
```

## FULL OUTER JOIN keeps unmatched rows from both sides

A department with nobody, and an employee with no department, both stay.
The missing side is NULL. `NULLS LAST` puts the unmatched employee on the
final row.

```sql file=n03.sql
CREATE TABLE dept (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE emp  (id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER, boss_id INTEGER, salary INTEGER);
INSERT INTO dept VALUES (1, 'Eng'), (2, 'Sales'), (3, 'Legal');
INSERT INTO emp VALUES
  (1, 'Ada',   1, NULL, 150),
  (2, 'Linus', 1, 1,    120),
  (3, 'Grace', 1, 1,    130),
  (4, 'Don',   2, 1,     90),
  (5, 'Zed',   NULL, 4,  70);
.headers on
SELECT d.name AS dept, e.name AS emp
FROM dept d FULL OUTER JOIN emp e ON e.dept_id = d.id
ORDER BY d.id NULLS LAST, e.id NULLS LAST;
```

```text output
dept|emp
Eng|Ada
Eng|Linus
Eng|Grace
Sales|Don
Legal|
|Zed
```

## An anti-join is a LEFT JOIN that keeps the misses

`WHERE` on the right key keeps left rows with no partner. Legal has no
employees, so it is the only row left. The filter has to be a column that
the join would have filled in, not a column you already allowed to be NULL
on the left.

```sql file=n04.sql
CREATE TABLE dept (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE emp  (id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER, boss_id INTEGER, salary INTEGER);
INSERT INTO dept VALUES (1, 'Eng'), (2, 'Sales'), (3, 'Legal');
INSERT INTO emp VALUES
  (1, 'Ada',   1, NULL, 150),
  (2, 'Linus', 1, 1,    120),
  (3, 'Grace', 1, 1,    130),
  (4, 'Don',   2, 1,     90),
  (5, 'Zed',   NULL, 4,  70);
.headers on
SELECT d.name FROM dept d LEFT JOIN emp e ON e.dept_id = d.id WHERE e.id IS NULL;
```

```text output
name
Legal
```

## A self join uses the same table twice

Each alias is a separate copy. `LEFT` keeps Ada, who has no boss.

```sql file=n05.sql
CREATE TABLE dept (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE emp  (id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER, boss_id INTEGER, salary INTEGER);
INSERT INTO dept VALUES (1, 'Eng'), (2, 'Sales'), (3, 'Legal');
INSERT INTO emp VALUES
  (1, 'Ada',   1, NULL, 150),
  (2, 'Linus', 1, 1,    120),
  (3, 'Grace', 1, 1,    130),
  (4, 'Don',   2, 1,     90),
  (5, 'Zed',   NULL, 4,  70);
.headers on
SELECT e.name AS emp, b.name AS boss
FROM emp e LEFT JOIN emp b ON b.id = e.boss_id
ORDER BY e.id;
```

```text output
emp|boss
Ada|
Linus|Ada
Grace|Ada
Don|Ada
Zed|Don
```

## Aggregate after the join, and count the many side

`count(e.id)` ignores the NULL-extended row, so Legal's headcount is 0.
`count(*)` would say 1. `coalesce` turns a NULL sum into 0. A one-to-many
join repeats the "one" side: summing a department column after joining
employees adds it once per employee. Aggregate in a subquery first, then
join. `dept.id` is the primary key, so `GROUP BY d.id` may still select
`d.name`.

```sql file=n06.sql
CREATE TABLE dept (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE emp  (id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER, boss_id INTEGER, salary INTEGER);
INSERT INTO dept VALUES (1, 'Eng'), (2, 'Sales'), (3, 'Legal');
INSERT INTO emp VALUES
  (1, 'Ada',   1, NULL, 150),
  (2, 'Linus', 1, 1,    120),
  (3, 'Grace', 1, 1,    130),
  (4, 'Don',   2, 1,     90),
  (5, 'Zed',   NULL, 4,  70);
.headers on
SELECT d.name AS dept, count(e.id) AS people, coalesce(sum(e.salary), 0) AS payroll
FROM dept d LEFT JOIN emp e ON e.dept_id = d.id
GROUP BY d.id ORDER BY d.id;
```

```text output
dept|people|payroll
Eng|3|400
Sales|1|90
Legal|0|0
```

## A WHERE on the right side undoes a LEFT JOIN

NULL-extended rows fail `e.salary > 125`, so they disappear and the join
behaves as an inner join. Put right-side filters in `ON` when you still
want the unmatched left rows.

```sql file=n07.sql
CREATE TABLE dept (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE emp  (id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER, boss_id INTEGER, salary INTEGER);
INSERT INTO dept VALUES (1, 'Eng'), (2, 'Sales'), (3, 'Legal');
INSERT INTO emp VALUES
  (1, 'Ada',   1, NULL, 150),
  (2, 'Linus', 1, 1,    120),
  (3, 'Grace', 1, 1,    130),
  (4, 'Don',   2, 1,     90),
  (5, 'Zed',   NULL, 4,  70);
.headers on
SELECT d.name AS dept, e.name AS emp
FROM dept d LEFT JOIN emp e ON e.dept_id = d.id AND e.salary > 125
ORDER BY d.id, e.id;
SELECT d.name AS dept, e.name AS emp
FROM dept d LEFT JOIN emp e ON e.dept_id = d.id
WHERE e.salary > 125 ORDER BY d.id, e.id;
```

```text output
dept|emp
Eng|Ada
Eng|Grace
Sales|
Legal|
dept|emp
Eng|Ada
Eng|Grace
```

## A missing condition is a cartesian product

`CROSS JOIN` is every combination, on purpose. Forgetting the `ON` clause
does the same thing: 5 employees times 3 departments is 15 rows. A result
that is suspiciously huge is usually this.

```sql file=n08.sql
CREATE TABLE dept (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE emp  (id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER, boss_id INTEGER, salary INTEGER);
INSERT INTO dept VALUES (1, 'Eng'), (2, 'Sales'), (3, 'Legal');
INSERT INTO emp VALUES
  (1, 'Ada',   1, NULL, 150),
  (2, 'Linus', 1, 1,    120),
  (3, 'Grace', 1, 1,    130),
  (4, 'Don',   2, 1,     90),
  (5, 'Zed',   NULL, 4,  70);
.headers on
SELECT count(*) AS pairs FROM emp, dept;
SELECT d.name AS dept, s.size
FROM dept d CROSS JOIN (SELECT 'S' AS size UNION ALL SELECT 'L') s
WHERE d.id < 3 ORDER BY d.id, s.size;
```

```text output
pairs
15
dept|size
Eng|L
Eng|S
Sales|L
Sales|S
```

## The condition does not have to be equality

`a.id < b.id` lists each pair once. Both sides still have to share a
department.

```sql file=n09.sql
CREATE TABLE dept (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE emp  (id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER, boss_id INTEGER, salary INTEGER);
INSERT INTO dept VALUES (1, 'Eng'), (2, 'Sales'), (3, 'Legal');
INSERT INTO emp VALUES
  (1, 'Ada',   1, NULL, 150),
  (2, 'Linus', 1, 1,    120),
  (3, 'Grace', 1, 1,    130),
  (4, 'Don',   2, 1,     90),
  (5, 'Zed',   NULL, 4,  70);
.headers on
SELECT a.name AS a, b.name AS b
FROM emp a JOIN emp b ON a.dept_id = b.dept_id AND a.id < b.id
ORDER BY a.id, b.id;
```

```text output
a|b
Ada|Linus
Ada|Grace
Linus|Grace
```

## Each extra table adds one join

One `ON` per join. The badge table only matches Ada and Grace.

```sql file=n10.sql
CREATE TABLE dept (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE emp  (id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER, boss_id INTEGER, salary INTEGER);
INSERT INTO dept VALUES (1, 'Eng'), (2, 'Sales'), (3, 'Legal');
INSERT INTO emp VALUES
  (1, 'Ada',   1, NULL, 150),
  (2, 'Linus', 1, 1,    120),
  (3, 'Grace', 1, 1,    130),
  (4, 'Don',   2, 1,     90),
  (5, 'Zed',   NULL, 4,  70);
CREATE TABLE badge (emp_id INTEGER, color TEXT);
INSERT INTO badge VALUES (1, 'gold'), (3, 'silver');
.headers on
SELECT e.name, b.color FROM emp e JOIN badge b ON b.emp_id = e.id ORDER BY e.id;
```

```text output
name|color
Ada|gold
Grace|silver
```

## UNION removes duplicates; UNION ALL keeps them

`UNION` sorts and dedupes. `UNION ALL` is cheaper. Use `ALL` unless you
need the duplicates gone. Eng names plus anyone paid at least 130 repeats
Ada and Grace only in the `ALL` form.

```sql file=n11.sql
CREATE TABLE dept (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE emp  (id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER, boss_id INTEGER, salary INTEGER);
INSERT INTO dept VALUES (1, 'Eng'), (2, 'Sales'), (3, 'Legal');
INSERT INTO emp VALUES
  (1, 'Ada',   1, NULL, 150),
  (2, 'Linus', 1, 1,    120),
  (3, 'Grace', 1, 1,    130),
  (4, 'Don',   2, 1,     90),
  (5, 'Zed',   NULL, 4,  70);
.headers on
SELECT name FROM emp WHERE dept_id = 1
UNION
SELECT name FROM emp WHERE salary >= 130
ORDER BY 1;
SELECT name FROM emp WHERE dept_id = 1
UNION ALL
SELECT name FROM emp WHERE salary >= 130
ORDER BY 1;
```

```text output
name
Ada
Grace
Linus
name
Ada
Ada
Grace
Grace
Linus
```

## EXCEPT and INTERSECT compare two result sets

`EXCEPT` is rows in the first select that are not in the second.
`INTERSECT` is rows in both. Both remove duplicates. `EXCEPT ALL` and
`INTERSECT ALL` keep duplicate multiplicity; leave off `ALL` unless you
need it.

```sql file=n12.sql
CREATE TABLE dept (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE emp  (id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER, boss_id INTEGER, salary INTEGER);
INSERT INTO dept VALUES (1, 'Eng'), (2, 'Sales'), (3, 'Legal');
INSERT INTO emp VALUES
  (1, 'Ada',   1, NULL, 150),
  (2, 'Linus', 1, 1,    120),
  (3, 'Grace', 1, 1,    130),
  (4, 'Don',   2, 1,     90),
  (5, 'Zed',   NULL, 4,  70);
.headers on
SELECT name FROM emp WHERE dept_id = 1
EXCEPT SELECT name FROM emp WHERE salary < 125 ORDER BY 1;
SELECT name FROM emp WHERE dept_id = 1
INTERSECT SELECT name FROM emp WHERE salary >= 130 ORDER BY 1;
```

```text output
name
Ada
Grace
name
Ada
Grace
```

## Exercises

```sql file=exercise.sql
CREATE TABLE dept (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE emp  (id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER, boss_id INTEGER, salary INTEGER);
INSERT INTO dept VALUES (1, 'Eng'), (2, 'Sales'), (3, 'Legal');
INSERT INTO emp VALUES
  (1, 'Ada',   1, NULL, 150),
  (2, 'Linus', 1, 1,    120),
  (3, 'Grace', 1, 1,    130),
  (4, 'Don',   2, 1,     90),
  (5, 'Zed',   NULL, 4,  70);

-- q1: employees paired with their department name, only those that have
--     one. Columns: emp, dept; ordered by emp name.
CREATE VIEW q1 AS SELECT NULL::TEXT AS emp, NULL::TEXT AS dept WHERE false;   -- TODO

-- q2: employees with NO department. Column: emp.
CREATE VIEW q2 AS SELECT NULL::TEXT AS emp WHERE false;                       -- TODO

-- q3: each employee's boss's name (NULL for the top boss). Columns:
--     emp, boss; ordered by emp name.
CREATE VIEW q3 AS SELECT NULL::TEXT AS emp, NULL::TEXT AS boss WHERE false;   -- TODO

-- q4: every department with its average salary (NULL if nobody works
--     there), rounded to a whole number. Columns: dept, avg_salary; by dept name.
CREATE VIEW q4 AS SELECT NULL::TEXT AS dept, NULL::INTEGER AS avg_salary WHERE false;  -- TODO

-- q5: the employees who earn more than their boss. Column: emp.
--     (Ada has no boss; Zed's boss Don earns more than Zed.)
CREATE VIEW q5 AS SELECT NULL::TEXT AS emp WHERE false;                       -- TODO

CREATE TABLE t (name TEXT, ok BOOLEAN CHECK (ok));
INSERT INTO t VALUES ('q1', (SELECT string_agg(emp || '@' || dept, ',' ORDER BY emp) FROM q1) IS NOT DISTINCT FROM 'Ada@Eng,Don@Sales,Grace@Eng,Linus@Eng');
INSERT INTO t VALUES ('q2', (SELECT string_agg(emp, ',') FROM q2) IS NOT DISTINCT FROM 'Zed');
INSERT INTO t VALUES ('q3', (SELECT string_agg(emp || '<' || coalesce(boss, '-'), ',' ORDER BY emp) FROM q3) IS NOT DISTINCT FROM 'Ada<-,Don<Ada,Grace<Ada,Linus<Ada,Zed<Don');
INSERT INTO t VALUES ('q4', (SELECT string_agg(dept || '=' || coalesce(avg_salary::TEXT, 'none'), ',' ORDER BY dept) FROM q4) IS NOT DISTINCT FROM 'Eng=133,Legal=none,Sales=90');
INSERT INTO t VALUES ('q5', (SELECT string_agg(emp, ',') FROM q5) IS NOT DISTINCT FROM NULL);
SELECT 'PASS ' || name FROM t;
```

<details><summary>Solution</summary>

```sql file=solution.sql
CREATE TABLE dept (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE emp  (id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER, boss_id INTEGER, salary INTEGER);
INSERT INTO dept VALUES (1, 'Eng'), (2, 'Sales'), (3, 'Legal');
INSERT INTO emp VALUES
  (1, 'Ada',   1, NULL, 150),
  (2, 'Linus', 1, 1,    120),
  (3, 'Grace', 1, 1,    130),
  (4, 'Don',   2, 1,     90),
  (5, 'Zed',   NULL, 4,  70);

CREATE VIEW q1 AS
  SELECT e.name AS emp, d.name AS dept FROM emp e JOIN dept d ON d.id = e.dept_id ORDER BY e.name;
CREATE VIEW q2 AS
  SELECT e.name AS emp FROM emp e LEFT JOIN dept d ON d.id = e.dept_id WHERE d.id IS NULL;
CREATE VIEW q3 AS
  SELECT e.name AS emp, b.name AS boss FROM emp e LEFT JOIN emp b ON b.id = e.boss_id ORDER BY e.name;
CREATE VIEW q4 AS
  SELECT d.name AS dept, CAST(round(avg(e.salary)) AS INTEGER) AS avg_salary
  FROM dept d LEFT JOIN emp e ON e.dept_id = d.id GROUP BY d.id ORDER BY d.name;
CREATE VIEW q5 AS
  SELECT e.name AS emp FROM emp e JOIN emp b ON b.id = e.boss_id WHERE e.salary > b.salary;

CREATE TABLE t (name TEXT, ok BOOLEAN CHECK (ok));
INSERT INTO t VALUES ('q1', (SELECT string_agg(emp || '@' || dept, ',' ORDER BY emp) FROM q1) IS NOT DISTINCT FROM 'Ada@Eng,Don@Sales,Grace@Eng,Linus@Eng');
INSERT INTO t VALUES ('q2', (SELECT string_agg(emp, ',') FROM q2) IS NOT DISTINCT FROM 'Zed');
INSERT INTO t VALUES ('q3', (SELECT string_agg(emp || '<' || coalesce(boss, '-'), ',' ORDER BY emp) FROM q3) IS NOT DISTINCT FROM 'Ada<-,Don<Ada,Grace<Ada,Linus<Ada,Zed<Don');
INSERT INTO t VALUES ('q4', (SELECT string_agg(dept || '=' || coalesce(avg_salary::TEXT, 'none'), ',' ORDER BY dept) FROM q4) IS NOT DISTINCT FROM 'Eng=133,Legal=none,Sales=90');
INSERT INTO t VALUES ('q5', (SELECT string_agg(emp, ',') FROM q5) IS NOT DISTINCT FROM NULL);
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [05 — Subqueries and CTEs](05-subqueries-ctes.md)
