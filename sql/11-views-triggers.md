# SQL 11 — Views and Triggers

A **view** is a saved query you use like a table: a stable, named
interface over the real schema. A **trigger** is code the database runs
automatically when rows change: audit trails, derived columns, guard rails.

## Example

```sql file=example.sql
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT NOT NULL, dept TEXT, salary INTEGER NOT NULL);
INSERT INTO emp VALUES (1, 'Ada', 'eng', 150), (2, 'Linus', 'eng', 120), (3, 'Don', 'sales', 90);

.headers on
-- 1. A view hides complexity and sensitive columns
CREATE VIEW dept_summary AS
  SELECT dept, count(*) AS people, sum(salary) AS payroll FROM emp GROUP BY dept;
CREATE VIEW emp_public AS SELECT id, name, dept FROM emp;     -- no salary

SELECT * FROM dept_summary ORDER BY dept;
SELECT * FROM emp_public ORDER BY id;

-- Views are live: they always reflect the current table
INSERT INTO emp VALUES (4, 'Peggy', 'sales', 95);
SELECT * FROM dept_summary WHERE dept = 'sales';

-- 2. A trigger runs on INSERT / UPDATE / DELETE, BEFORE or AFTER
CREATE TABLE audit (
  id INTEGER PRIMARY KEY, at TEXT DEFAULT (datetime('2024-01-01')),
  emp_id INTEGER, action TEXT, old_salary INTEGER, new_salary INTEGER
);
CREATE TRIGGER emp_salary_audit AFTER UPDATE OF salary ON emp
WHEN OLD.salary <> NEW.salary
BEGIN
  INSERT INTO audit (emp_id, action, old_salary, new_salary)
  VALUES (OLD.id, 'raise', OLD.salary, NEW.salary);
END;

UPDATE emp SET salary = salary + 10 WHERE dept = 'sales';
UPDATE emp SET name = 'Linus T.' WHERE id = 2;          -- not a salary change: no audit
SELECT emp_id, action, old_salary, new_salary FROM audit ORDER BY id;

-- 3. A BEFORE trigger can reject bad changes with RAISE
CREATE TRIGGER no_pay_cut BEFORE UPDATE OF salary ON emp
WHEN NEW.salary < OLD.salary
BEGIN
  SELECT RAISE(ABORT, 'salary cannot decrease');
END;
-- expect-error
UPDATE emp SET salary = 1 WHERE id = 1;
SELECT salary FROM emp WHERE id = 1;

-- 4. Keep a derived value in sync
CREATE TABLE post (id INTEGER PRIMARY KEY, title TEXT);
CREATE TABLE comment (id INTEGER PRIMARY KEY, post_id INTEGER, body TEXT);
ALTER TABLE post ADD COLUMN comment_count INTEGER NOT NULL DEFAULT 0;
CREATE TRIGGER comment_ins AFTER INSERT ON comment
BEGIN UPDATE post SET comment_count = comment_count + 1 WHERE id = NEW.post_id; END;
CREATE TRIGGER comment_del AFTER DELETE ON comment
BEGIN UPDATE post SET comment_count = comment_count - 1 WHERE id = OLD.post_id; END;
INSERT INTO post (id, title) VALUES (1, 'Hello');
INSERT INTO comment (post_id, body) VALUES (1, 'a'), (1, 'b'), (1, 'c');
DELETE FROM comment WHERE body = 'b';
SELECT title, comment_count FROM post;

-- 5. INSTEAD OF triggers make a view writable
CREATE TRIGGER emp_public_ins INSTEAD OF INSERT ON emp_public
BEGIN INSERT INTO emp (name, dept, salary) VALUES (NEW.name, NEW.dept, 50); END;
INSERT INTO emp_public (id, name, dept) VALUES (NULL, 'Intern', 'eng');
SELECT name, salary FROM emp WHERE name = 'Intern';

-- 6. Soft delete through a view: queries see only live rows
CREATE TABLE doc (id INTEGER PRIMARY KEY, title TEXT, deleted_at TEXT);
CREATE VIEW live_doc AS SELECT id, title FROM doc WHERE deleted_at IS NULL;
INSERT INTO doc (title) VALUES ('keep'), ('drop');
UPDATE doc SET deleted_at = '2024-06-01' WHERE title = 'drop';
SELECT * FROM live_doc;

-- 7. List and remove
SELECT name, type FROM sqlite_master WHERE type IN ('view', 'trigger') ORDER BY type, name;
DROP VIEW live_doc;
DROP TRIGGER no_pay_cut;
```

```text output
dept|people|payroll
eng|2|270
sales|1|90
id|name|dept
1|Ada|eng
2|Linus|eng
3|Don|sales
dept|people|payroll
sales|2|185
emp_id|action|old_salary|new_salary
3|raise|90|100
4|raise|95|105
Error: salary cannot decrease
salary
150
title|comment_count
Hello|2
name|salary
Intern|50
id|title
1|keep
name|type
comment_del|trigger
comment_ins|trigger
emp_public_ins|trigger
emp_salary_audit|trigger
no_pay_cut|trigger
dept_summary|view
emp_public|view
live_doc|view
```

## Details that bite

- A view stores **no data** (plain views). Its query runs every time, so a
  slow view is a slow query. PostgreSQL's `MATERIALIZED VIEW` stores the
  result and needs `REFRESH`; SQLite has none (use a table you rebuild).
- Views and `SELECT *`: the column list can be frozen when the view is
  created in some databases, so `ALTER TABLE ... ADD COLUMN` does not show up.
  Name columns explicitly.
- Simple views are updatable in PostgreSQL and MySQL; in SQLite you make
  them writable with `INSTEAD OF` triggers.
- Triggers are **invisible** to the code that fires them. A hidden trigger
  is a surprise at 3 a.m. Use them for invariants (audit, derived counters,
  enforcement), not business workflows, and document them.
- Triggers cost write time, and a trigger that updates another table can
  fire more triggers. Watch for loops.
- `OLD` and `NEW` mean the row before and after. `INSERT` has only `NEW`,
  `DELETE` only `OLD`. `WHEN` limits when the body runs.
- Application-side logic is easier to test and version. Database-side
  guarantees (constraints, triggers) are enforced for *every* client. Use
  constraints first, triggers second.
- PostgreSQL triggers call a function (`CREATE FUNCTION ... RETURNS
  trigger`); MySQL has inline bodies like SQLite. Only the idea ports.

## Exercises

```sql file=exercise.sql
CREATE TABLE product (id INTEGER PRIMARY KEY, name TEXT NOT NULL, price INTEGER NOT NULL, stock INTEGER NOT NULL);
CREATE TABLE price_log (product_id INTEGER, old_price INTEGER, new_price INTEGER);
INSERT INTO product VALUES (1, 'pen', 100, 50), (2, 'ink', 450, 5), (3, 'pad', 300, 0);

-- 1. View in_stock: id, name, price for products with stock > 0.
-- 2. Trigger price_changed (AFTER UPDATE OF price ON product): when the price
--    changes, add a row to price_log (product_id, old_price, new_price).
-- 3. Trigger no_free (BEFORE UPDATE OF price ON product): if NEW.price <= 0,
--    RAISE(ABORT, 'price must be positive').
-- TODO: write the CREATE VIEW / CREATE TRIGGER statements here



UPDATE product SET price = price + 50 WHERE id IN (1, 2);
-- expect-error
UPDATE product SET price = 0 WHERE id = 3;

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('view', (SELECT group_concat(name) FROM (SELECT name FROM in_stock ORDER BY id)) IS 'pen,ink');
INSERT INTO t VALUES ('log',  (SELECT group_concat(product_id || ':' || old_price || '>' || new_price) FROM (SELECT * FROM price_log ORDER BY product_id)) IS '1:100>150,2:450>500');
INSERT INTO t VALUES ('guard', (SELECT price FROM product WHERE id = 3) IS 300);
SELECT 'PASS ' || name FROM t;
```

<details><summary>Solution</summary>

```sql file=solution.sql
CREATE TABLE product (id INTEGER PRIMARY KEY, name TEXT NOT NULL, price INTEGER NOT NULL, stock INTEGER NOT NULL);
CREATE TABLE price_log (product_id INTEGER, old_price INTEGER, new_price INTEGER);
INSERT INTO product VALUES (1, 'pen', 100, 50), (2, 'ink', 450, 5), (3, 'pad', 300, 0);

CREATE VIEW in_stock AS SELECT id, name, price FROM product WHERE stock > 0;

CREATE TRIGGER price_changed AFTER UPDATE OF price ON product
WHEN OLD.price <> NEW.price
BEGIN
  INSERT INTO price_log VALUES (OLD.id, OLD.price, NEW.price);
END;

CREATE TRIGGER no_free BEFORE UPDATE OF price ON product
WHEN NEW.price <= 0
BEGIN
  SELECT RAISE(ABORT, 'price must be positive');
END;

UPDATE product SET price = price + 50 WHERE id IN (1, 2);
-- expect-error
UPDATE product SET price = 0 WHERE id = 3;

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('view', (SELECT group_concat(name) FROM (SELECT name FROM in_stock ORDER BY id)) IS 'pen,ink');
INSERT INTO t VALUES ('log',  (SELECT group_concat(product_id || ':' || old_price || '>' || new_price) FROM (SELECT * FROM price_log ORDER BY product_id)) IS '1:100>150,2:450>500');
INSERT INTO t VALUES ('guard', (SELECT price FROM product WHERE id = 3) IS 300);
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [12 — JSON, dates and text](12-json-dates-text.md)
