# SQL 07 — Changing Data: INSERT, UPDATE, DELETE, UPSERT

Reads are forgiving; writes are not. Every `UPDATE` and `DELETE` without a
`WHERE` touches **every row**. This lesson is about writing data precisely,
and about getting back what you wrote (`RETURNING`).

## Example

```sql file=example.sql
CREATE TABLE item (
  id INTEGER PRIMARY KEY, sku TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
  stock INTEGER NOT NULL DEFAULT 0, updated TEXT
);

.headers on
-- INSERT: list the columns (do not rely on column order)
INSERT INTO item (sku, name, stock) VALUES ('A-1', 'bolt', 100);
INSERT INTO item (sku, name) VALUES ('B-2', 'nut');                 -- stock defaults to 0
INSERT INTO item (sku, name, stock) VALUES ('C-3', 'screw', 40), ('D-4', 'washer', 15);
SELECT id, sku, name, stock FROM item ORDER BY id;

-- RETURNING gives the generated values back (SQLite 3.35+, PostgreSQL)
INSERT INTO item (sku, name, stock) VALUES ('E-5', 'rivet', 5) RETURNING id, sku;

-- INSERT ... SELECT copies rows
CREATE TABLE low_stock (sku TEXT, stock INTEGER);
INSERT INTO low_stock SELECT sku, stock FROM item WHERE stock < 20;
SELECT * FROM low_stock ORDER BY sku;

-- UPDATE: SET expressions can read the old value
UPDATE item SET stock = stock + 10, updated = '2024-06-01' WHERE sku = 'B-2';
UPDATE item SET stock = stock - 1 WHERE stock > 0 RETURNING sku, stock;

-- UPDATE with a subquery
UPDATE item SET name = upper(name)
WHERE sku IN (SELECT sku FROM low_stock);
SELECT sku, name FROM item WHERE sku IN ('D-4', 'E-5', 'A-1') ORDER BY sku;

-- Constraint violations are errors; OR IGNORE / OR REPLACE choose behaviour
INSERT OR IGNORE INTO item (sku, name) VALUES ('A-1', 'dup');       -- silently skipped
SELECT count(*) AS still_five FROM item;

-- UPSERT: insert, or update when the key already exists
INSERT INTO item (sku, name, stock) VALUES ('A-1', 'bolt', 7)
ON CONFLICT (sku) DO UPDATE SET stock = stock + excluded.stock
RETURNING sku, stock;
INSERT INTO item (sku, name, stock) VALUES ('Z-9', 'new', 3)
ON CONFLICT (sku) DO UPDATE SET stock = stock + excluded.stock
RETURNING sku, stock;

-- DELETE: with a WHERE, always. Look first with a SELECT.
SELECT count(*) AS to_delete FROM item WHERE stock < 5;
DELETE FROM item WHERE stock < 5 RETURNING sku;

-- Counting what changed
SELECT changes() AS last_change;
DELETE FROM low_stock;
SELECT changes() AS deleted_rows, (SELECT count(*) FROM low_stock) AS remaining;

-- TRUNCATE does not exist in SQLite: DELETE FROM t is the equivalent.
-- Replace-all pattern: fill a new table, then swap the names
CREATE TABLE item_new AS SELECT id, sku, name FROM item WHERE stock > 50;
DROP TABLE item;
ALTER TABLE item_new RENAME TO item;
SELECT * FROM item;
```

```text output
id|sku|name|stock
1|A-1|bolt|100
2|B-2|nut|0
3|C-3|screw|40
4|D-4|washer|15
id|sku
5|E-5
sku|stock
B-2|0
D-4|15
E-5|5
sku|stock
A-1|99
B-2|9
C-3|39
D-4|14
E-5|4
sku|name
A-1|bolt
D-4|WASHER
E-5|RIVET
still_five
5
sku|stock
A-1|106
sku|stock
Z-9|3
to_delete
2
sku
E-5
Z-9
last_change
2
deleted_rows|remaining
3|0
id|sku|name
1|A-1|bolt
```

## Details that bite

- `UPDATE`/`DELETE` without `WHERE` hits every row. Habit: write the
  `WHERE` first, or run it as a `SELECT` to see the rows, then change the
  verb. In a session, wrap risky statements in a transaction (lesson 09)
  and check the count before `COMMIT`.
- `INSERT` without a column list breaks the day someone adds a column.
- `ON CONFLICT ... DO UPDATE` is the portable-ish upsert: PostgreSQL and
  SQLite share the syntax; MySQL uses `ON DUPLICATE KEY UPDATE`; standard
  SQL has `MERGE` (PostgreSQL 15+, not SQLite or MySQL).
- `INSERT OR REPLACE` (SQLite) **deletes and re-inserts** the row, which
  resets columns you did not list and fires delete triggers. Prefer
  `ON CONFLICT DO UPDATE`.
- `RETURNING` is not in MySQL; use `LAST_INSERT_ID()` there.
- Auto-increment: `INTEGER PRIMARY KEY` in SQLite, `GENERATED ... AS
  IDENTITY` in PostgreSQL, `AUTO_INCREMENT` in MySQL. Do not reuse or
  predict ids; take them from the insert.
- Writing many rows? One multi-row `INSERT` (or one transaction around
  many) is orders of magnitude faster than autocommitting each row.
- Deleting parents with child rows is governed by foreign keys
  (lesson 08), not by your intent.

## Exercises

```sql file=exercise.sql
CREATE TABLE item (
  id INTEGER PRIMARY KEY, sku TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
  stock INTEGER NOT NULL DEFAULT 0
);
INSERT INTO item (sku, name, stock) VALUES
  ('A-1', 'bolt', 100), ('B-2', 'nut', 0), ('C-3', 'screw', 40), ('D-4', 'washer', 15);

-- Do the changes with statements, in order, between the markers.
-- 1. Add a new item ('E-5', 'rivet', 5).
-- 2. Increase stock of every item below 20 by 10.
-- 3. Receive 25 more of 'C-3' and add ('F-6', 'pin', 8) with one UPSERT
--    statement each (sku is the conflict key; stock adds up on conflict).
-- 4. Delete items whose stock is 0 or less.
-- TODO: write the statements here



CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('rows',  (SELECT count(*) FROM item) IS 6);
INSERT INTO t VALUES ('rivet', (SELECT stock FROM item WHERE sku = 'E-5') IS 15);
INSERT INTO t VALUES ('low',   (SELECT stock FROM item WHERE sku = 'B-2') IS 10);
INSERT INTO t VALUES ('upsert',(SELECT stock FROM item WHERE sku = 'C-3') IS 65);
INSERT INTO t VALUES ('new',   (SELECT stock FROM item WHERE sku = 'F-6') IS 8);
SELECT 'PASS ' || name FROM t;
```

<details><summary>Solution</summary>

```sql file=solution.sql
CREATE TABLE item (
  id INTEGER PRIMARY KEY, sku TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
  stock INTEGER NOT NULL DEFAULT 0
);
INSERT INTO item (sku, name, stock) VALUES
  ('A-1', 'bolt', 100), ('B-2', 'nut', 0), ('C-3', 'screw', 40), ('D-4', 'washer', 15);

INSERT INTO item (sku, name, stock) VALUES ('E-5', 'rivet', 5);
UPDATE item SET stock = stock + 10 WHERE stock < 20;
INSERT INTO item (sku, name, stock) VALUES ('C-3', 'screw', 25)
  ON CONFLICT (sku) DO UPDATE SET stock = stock + excluded.stock;
INSERT INTO item (sku, name, stock) VALUES ('F-6', 'pin', 8)
  ON CONFLICT (sku) DO UPDATE SET stock = stock + excluded.stock;
DELETE FROM item WHERE stock <= 0;

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('rows',  (SELECT count(*) FROM item) IS 6);
INSERT INTO t VALUES ('rivet', (SELECT stock FROM item WHERE sku = 'E-5') IS 15);
INSERT INTO t VALUES ('low',   (SELECT stock FROM item WHERE sku = 'B-2') IS 10);
INSERT INTO t VALUES ('upsert',(SELECT stock FROM item WHERE sku = 'C-3') IS 65);
INSERT INTO t VALUES ('new',   (SELECT stock FROM item WHERE sku = 'F-6') IS 8);
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [08 — Schema design](08-schema-design.md)
