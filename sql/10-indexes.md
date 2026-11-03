# SQL 10 — Indexes and Query Plans

An **index** is a sorted copy of some columns pointing back at the rows, so
the database can jump to matches instead of reading the whole table. You
write the same SQL; the *plan* changes. `EXPLAIN QUERY PLAN` (SQLite;
`EXPLAIN` in PostgreSQL and MySQL) shows which plan was chosen.

## Example

```sql file=example.sql
CREATE TABLE event (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, kind TEXT NOT NULL,
  at TEXT NOT NULL, note TEXT
);
-- 2,000 rows from a recursive CTE (lesson 13 explains how it works)
WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 2000)
INSERT INTO event (user_id, kind, at, note)
SELECT i % 100, CASE i % 4 WHEN 0 THEN 'login' WHEN 1 THEN 'view' WHEN 2 THEN 'buy' ELSE 'logout' END,
       printf('2024-%02d-%02d', 1 + i % 12, 1 + i % 28), 'n' || i FROM n;

-- Plan without an index: a full table SCAN
EXPLAIN QUERY PLAN SELECT count(*) FROM event WHERE user_id = 42;

CREATE INDEX event_user ON event (user_id);

-- Now it SEARCHes the index; COVERING means the index alone answered it
EXPLAIN QUERY PLAN SELECT count(*) FROM event WHERE user_id = 42;
EXPLAIN QUERY PLAN SELECT note FROM event WHERE user_id = 42;

-- Composite index: column ORDER matters (leftmost prefix rule)
CREATE INDEX event_user_kind ON event (user_id, kind);
EXPLAIN QUERY PLAN SELECT * FROM event WHERE user_id = 42 AND kind = 'buy';
EXPLAIN QUERY PLAN SELECT * FROM event WHERE kind = 'buy';          -- cannot use it well

-- Sorting: an index in the right order avoids a sort step
EXPLAIN QUERY PLAN SELECT * FROM event WHERE user_id = 7 ORDER BY kind;
EXPLAIN QUERY PLAN SELECT * FROM event ORDER BY note;                -- needs a TEMP B-TREE sort

-- Wrapping the column in a function defeats the index...
EXPLAIN QUERY PLAN SELECT * FROM event WHERE substr(at, 1, 7) = '2024-03';
-- ...unless there is an index ON the expression
CREATE INDEX event_month ON event (substr(at, 1, 7));
EXPLAIN QUERY PLAN SELECT * FROM event WHERE substr(at, 1, 7) = '2024-03';

-- Leading wildcard LIKE cannot use a normal index; a prefix can (with NOCASE caveats)
EXPLAIN QUERY PLAN SELECT * FROM event WHERE note LIKE '%99';

-- Partial index: smaller, only the rows you query
CREATE INDEX event_buys ON event (at) WHERE kind = 'buy';
EXPLAIN QUERY PLAN SELECT at FROM event WHERE kind = 'buy' AND at > '2024-06';

-- Unique indexes enforce rules, too
CREATE UNIQUE INDEX event_note_uq ON event (note);
-- expect-error
INSERT INTO event (user_id, kind, at, note) VALUES (1, 'view', '2024-01-01', 'n5');

-- What indexes exist?
SELECT name FROM pragma_index_list('event') ORDER BY name;

-- Refresh planner statistics after big changes
ANALYZE;
SELECT count(*) > 0 AS has_stats FROM sqlite_stat1;

-- Indexes are not free: every INSERT/UPDATE/DELETE maintains each one
DROP INDEX event_note_uq;
DROP INDEX event_month;
SELECT count(*) AS indexes_left FROM pragma_index_list('event');
```

```text output
QUERY PLAN
`--SCAN event
QUERY PLAN
`--SEARCH event USING COVERING INDEX event_user (user_id=?)
QUERY PLAN
`--SEARCH event USING INDEX event_user (user_id=?)
QUERY PLAN
`--SEARCH event USING INDEX event_user_kind (user_id=? AND kind=?)
QUERY PLAN
`--SCAN event
QUERY PLAN
`--SEARCH event USING INDEX event_user_kind (user_id=?)
QUERY PLAN
|--SCAN event
`--USE TEMP B-TREE FOR ORDER BY
QUERY PLAN
`--SCAN event
QUERY PLAN
`--SEARCH event USING INDEX event_month (<expr>=?)
QUERY PLAN
`--SCAN event
QUERY PLAN
`--SEARCH event USING COVERING INDEX event_buys (at>?)
Error: UNIQUE constraint failed: event.note
event_buys
event_month
event_note_uq
event_user
event_user_kind
1
3
```

## Details that bite

- **Measure, do not guess.** Read the plan for slow queries (`SCAN` =
  full read, `SEARCH ... USING INDEX` = jump). PostgreSQL's
  `EXPLAIN (ANALYZE, BUFFERS)` shows real timings; trust it over intuition.
- Composite indexes follow the **leftmost prefix rule**: `(a, b, c)` serves
  filters on `a`, `a,b`, `a,b,c`, but not on `b` alone. Put equality columns
  first, then the range or sort column.
- Functions and casts on the indexed column (`lower(email) = ...`,
  `date(at) = ...`) defeat the index. Compare the raw column, or add an
  expression index.
- Implicit type conversions do too: comparing a text column to a number
  may disable the index.
- Low-selectivity columns (booleans, "status" with 3 values) rarely
  benefit from a plain index; a *partial* index on the rare value does.
- Each index slows writes and uses disk. Do not index everything; drop
  the ones the plans never use.
- Primary keys and `UNIQUE` constraints already create indexes. Foreign
  key columns are **not** indexed automatically in PostgreSQL or SQLite:
  index them, or deletes on the parent scan the child table.
- Small tables are faster to scan than to index-probe. The planner knows;
  `ANALYZE` helps it know better.
- A **covering index** contains every column the query needs, so the table
  is never touched (`USING COVERING INDEX`).

## Exercises

```sql file=exercise.sql
CREATE TABLE event (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, kind TEXT NOT NULL,
  at TEXT NOT NULL, note TEXT
);
WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 500)
INSERT INTO event (user_id, kind, at, note)
SELECT i % 50, CASE i % 3 WHEN 0 THEN 'login' WHEN 1 THEN 'view' ELSE 'buy' END,
       printf('2024-%02d-%02d', 1 + i % 12, 1 + i % 28), 'n' || i FROM n;

-- Create indexes so the three queries below use them:
--   A: WHERE user_id = ? AND kind = ?        -> one composite index
--   B: WHERE lower(kind) = 'buy'             -> an expression index
--   C: WHERE at > '2024-10' AND kind = 'buy' -> a partial index on (at) for buys
-- TODO: CREATE INDEX statements here



CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('composite exists', (SELECT count(*) FROM pragma_index_list('event') pl
   WHERE (SELECT count(*) FROM pragma_index_info(pl.name)) = 2) IS 1);
INSERT INTO t VALUES ('expression index', (SELECT count(*) FROM sqlite_master
   WHERE type = 'index' AND tbl_name = 'event' AND sql LIKE '%lower(kind)%') IS 1);
INSERT INTO t VALUES ('partial index', (SELECT count(*) FROM sqlite_master
   WHERE type = 'index' AND tbl_name = 'event' AND sql LIKE '%WHERE%') IS 1);
SELECT 'PASS ' || name FROM t;
```

<details><summary>Solution</summary>

```sql file=solution.sql
CREATE TABLE event (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, kind TEXT NOT NULL,
  at TEXT NOT NULL, note TEXT
);
WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 500)
INSERT INTO event (user_id, kind, at, note)
SELECT i % 50, CASE i % 3 WHEN 0 THEN 'login' WHEN 1 THEN 'view' ELSE 'buy' END,
       printf('2024-%02d-%02d', 1 + i % 12, 1 + i % 28), 'n' || i FROM n;

CREATE INDEX event_user_kind ON event (user_id, kind);
CREATE INDEX event_kind_lower ON event (lower(kind));
CREATE INDEX event_buys_at ON event (at) WHERE kind = 'buy';

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('composite exists', (SELECT count(*) FROM pragma_index_list('event') pl
   WHERE (SELECT count(*) FROM pragma_index_info(pl.name)) = 2) IS 1);
INSERT INTO t VALUES ('expression index', (SELECT count(*) FROM sqlite_master
   WHERE type = 'index' AND tbl_name = 'event' AND sql LIKE '%lower(kind)%') IS 1);
INSERT INTO t VALUES ('partial index', (SELECT count(*) FROM sqlite_master
   WHERE type = 'index' AND tbl_name = 'event' AND sql LIKE '%WHERE%') IS 1);
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [11 — Views and triggers](11-views-triggers.md)
