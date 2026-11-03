# SQL 04 — Joins

Data lives in several tables, linked by keys. A **join** combines rows from
two tables where a condition holds. Pick the join by what you want to do
with the rows that have **no match**.

## Example

```sql file=example.sql
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
-- INNER JOIN: only rows that match on both sides
SELECT e.name AS emp, d.name AS dept
FROM emp e JOIN dept d ON d.id = e.dept_id
ORDER BY e.id;

-- LEFT JOIN: every left row; right side NULL when there is no match
SELECT e.name AS emp, d.name AS dept
FROM emp e LEFT JOIN dept d ON d.id = e.dept_id
ORDER BY e.id;

-- Anti-join: left rows with NO match (departments with no employees)
SELECT d.name FROM dept d LEFT JOIN emp e ON e.dept_id = d.id WHERE e.id IS NULL;

-- Self join: the same table twice, with different aliases
SELECT e.name AS emp, b.name AS boss
FROM emp e LEFT JOIN emp b ON b.id = e.boss_id
ORDER BY e.id;

-- Join, then aggregate: headcount and payroll per department
SELECT d.name AS dept, count(e.id) AS people, coalesce(sum(e.salary), 0) AS payroll
FROM dept d LEFT JOIN emp e ON e.dept_id = d.id
GROUP BY d.id ORDER BY d.id;

-- Condition placement: in ON vs WHERE changes a LEFT JOIN's meaning
SELECT d.name AS dept, e.name AS emp
FROM dept d LEFT JOIN emp e ON e.dept_id = d.id AND e.salary > 125
ORDER BY d.id, e.id;                       -- keeps Sales and Legal with NULL
SELECT d.name AS dept, e.name AS emp
FROM dept d LEFT JOIN emp e ON e.dept_id = d.id
WHERE e.salary > 125 ORDER BY d.id, e.id;  -- the WHERE turns it into an inner join

-- CROSS JOIN: every combination (use deliberately)
SELECT d.name AS dept, s.size
FROM dept d CROSS JOIN (SELECT 'S' AS size UNION ALL SELECT 'L') s
WHERE d.id < 3 ORDER BY d.id, s.size;

-- Non-equality join: pair employees and list each pair once
SELECT a.name AS a, b.name AS b
FROM emp a JOIN emp b ON a.dept_id = b.dept_id AND a.id < b.id
ORDER BY a.id, b.id;

-- A third table: join as many as you need, one ON per join
CREATE TABLE badge (emp_id INTEGER, color TEXT);
INSERT INTO badge VALUES (1, 'gold'), (3, 'silver');
SELECT e.name, b.color FROM emp e JOIN badge b ON b.emp_id = e.id ORDER BY e.id;

-- Combining result sets: UNION (dedupes), UNION ALL (keeps), EXCEPT, INTERSECT
SELECT name FROM emp WHERE dept_id = 1
EXCEPT SELECT name FROM emp WHERE salary < 125 ORDER BY 1;
```

```text output
emp|dept
Ada|Eng
Linus|Eng
Grace|Eng
Don|Sales
emp|dept
Ada|Eng
Linus|Eng
Grace|Eng
Don|Sales
Zed|
name
Legal
emp|boss
Ada|
Linus|Ada
Grace|Ada
Don|Ada
Zed|Don
dept|people|payroll
Eng|3|400
Sales|1|90
Legal|0|0
dept|emp
Eng|Ada
Eng|Grace
Sales|
Legal|
dept|emp
Eng|Ada
Eng|Grace
dept|size
Eng|L
Eng|S
Sales|L
Sales|S
a|b
Ada|Linus
Ada|Grace
Linus|Grace
name|color
Ada|gold
Grace|silver
name
Ada
Grace
```

## Details that bite

- Forgetting the join condition gives a **cartesian product**: `5 × 3`
  rows. If a result is suspiciously huge, that is why.
- `WHERE right_table.col = ...` after a `LEFT JOIN` silently turns it into
  an inner join, because the NULL-extended rows fail the test. Put
  right-side filters in `ON`.
- A one-to-many join repeats the "one" side. `sum(dept.budget)` after
  joining employees counts the budget once per employee. Aggregate in a
  subquery first, then join.
- `NULL` never equals `NULL` in a join: `emp.dept_id` NULL matches no
  department. That is usually what you want; know it.
- `RIGHT` and `FULL OUTER JOIN` exist (SQLite 3.39+, PostgreSQL), but MySQL
  lacks `FULL`. Swapping the table order and using `LEFT` is portable.
- `JOIN ... USING (col)` and `NATURAL JOIN` merge same-named columns.
  `NATURAL` breaks when someone adds a column with a clashing name:
  avoid it.
- Always alias and qualify columns (`e.name`) once two tables are in
  play; ambiguous names are errors or, worse, silent mistakes.
- `UNION` removes duplicates (a sort); `UNION ALL` is cheaper. Use `ALL`
  unless you need dedup.

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
CREATE VIEW q1 AS SELECT NULL AS emp, NULL AS dept WHERE 0;             -- TODO

-- q2: employees with NO department. Column: emp.
CREATE VIEW q2 AS SELECT NULL AS emp WHERE 0;                           -- TODO

-- q3: each employee's boss's name (NULL for the top boss). Columns:
--     emp, boss; ordered by emp name.
CREATE VIEW q3 AS SELECT NULL AS emp, NULL AS boss WHERE 0;             -- TODO

-- q4: every department with its average salary (NULL if nobody works
--     there), rounded to a whole number. Columns: dept, avg_salary; by dept name.
CREATE VIEW q4 AS SELECT NULL AS dept, NULL AS avg_salary WHERE 0;      -- TODO

-- q5: the employees who earn more than their boss. Column: emp.
--     (Ada has no boss; Zed's boss Don earns more than Zed.)
CREATE VIEW q5 AS SELECT NULL AS emp WHERE 0;                           -- TODO

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('q1', (SELECT group_concat(emp || '@' || dept, ',') FROM q1) IS 'Ada@Eng,Don@Sales,Grace@Eng,Linus@Eng');
INSERT INTO t VALUES ('q2', (SELECT group_concat(emp) FROM q2) IS 'Zed');
INSERT INTO t VALUES ('q3', (SELECT group_concat(emp || '<' || coalesce(boss, '-'), ',') FROM q3) IS 'Ada<-,Don<Ada,Grace<Ada,Linus<Ada,Zed<Don');
INSERT INTO t VALUES ('q4', (SELECT group_concat(dept || '=' || coalesce(avg_salary, 'none'), ',') FROM q4) IS 'Eng=133,Legal=none,Sales=90');
INSERT INTO t VALUES ('q5', (SELECT group_concat(emp) FROM q5) IS NULL);
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

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('q1', (SELECT group_concat(emp || '@' || dept, ',') FROM q1) IS 'Ada@Eng,Don@Sales,Grace@Eng,Linus@Eng');
INSERT INTO t VALUES ('q2', (SELECT group_concat(emp) FROM q2) IS 'Zed');
INSERT INTO t VALUES ('q3', (SELECT group_concat(emp || '<' || coalesce(boss, '-'), ',') FROM q3) IS 'Ada<-,Don<Ada,Grace<Ada,Linus<Ada,Zed<Don');
INSERT INTO t VALUES ('q4', (SELECT group_concat(dept || '=' || coalesce(avg_salary, 'none'), ',') FROM q4) IS 'Eng=133,Legal=none,Sales=90');
INSERT INTO t VALUES ('q5', (SELECT group_concat(emp) FROM q5) IS NULL);
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [05 — Subqueries and CTEs](05-subqueries-ctes.md)
