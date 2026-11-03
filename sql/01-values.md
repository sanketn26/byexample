# SQL 01 — Values, Types and NULL

SQL is **declarative**: you describe the rows you want, not the loops that
find them. This track uses **SQLite** because it needs no server, and
points out where PostgreSQL and MySQL differ (lesson 15).

A query is a table in, a table out. `SELECT` with no `FROM` is just an
expression evaluator, a perfect place to start.

## Example

```sql file=example.sql
-- Literals and arithmetic
SELECT 1 + 2, 7 / 2, 7 % 2, 7 / 2.0;

-- Strings use single quotes; || concatenates; '' escapes a quote
SELECT 'it''s' || ' ' || 'SQL', length('héllo'), upper('abc');

-- SQLite has dynamic types: every VALUE has a storage class
SELECT typeof(1), typeof(1.5), typeof('x'), typeof(NULL), typeof(x'FF');

-- Column aliases and headers
.headers on
SELECT 6 * 7 AS answer, 'ok' AS status;
.headers off

-- NULL means "unknown", and it is contagious
SELECT NULL + 1, NULL || 'x', NULL = NULL, NULL IS NULL;

-- Three-valued logic: TRUE, FALSE, NULL(unknown)
SELECT 1 = 1, 1 = 2, NULL = 1, NULL AND 0, NULL OR 1, NOT NULL;

-- Functions that handle NULL on purpose
SELECT coalesce(NULL, NULL, 'third'), ifnull(NULL, 'fallback'), nullif(5, 5), nullif(5, 6);

-- CASE is the expression form of if/else
SELECT CASE WHEN 15 % 15 = 0 THEN 'FizzBuzz'
            WHEN 15 % 3 = 0  THEN 'Fizz'
            ELSE '15' END;

-- A real table, with typed columns
CREATE TABLE city (name TEXT, country TEXT, population INTEGER);
INSERT INTO city VALUES
  ('Tokyo',  'JP', 37400000),
  ('Delhi',  'IN', 31000000),
  ('Lagos',  'NG', NULL),
  ('Oslo',   'NO',   700000);

SELECT name, population FROM city;
SELECT count(*), count(population) FROM city;     -- count(col) skips NULLs
SELECT name FROM city WHERE population IS NULL;

-- Casting, and type affinity
SELECT CAST('42' AS INTEGER) + 1, CAST(3.99 AS INTEGER), '5' + '5', '5' || '5';
SELECT round(2.5), round(3.14159, 2), abs(-4), max(3, 9, 5), min(3, 9, 5);
```

```text output
3|3|1|3.5
it's SQL|5|ABC
integer|real|text|null|blob
answer|status
42|ok
|||1
1|0||0|1|
third|fallback||5
FizzBuzz
Tokyo|37400000
Delhi|31000000
Lagos|
Oslo|700000
4|3
Lagos
43|3|10|55
3.0|3.14|4|9|3
```

## Details that bite

- `NULL = NULL` is **NULL**, not true. Test with `IS NULL` / `IS NOT NULL`
  (or `IS` / `IS NOT` to compare two values that might be NULL).
- `WHERE x <> 5` drops rows where `x` is NULL: the comparison yields
  unknown, and `WHERE` keeps only TRUE.
- Integer division truncates: `7 / 2` is `3` in SQLite, PostgreSQL and
  MySQL's `DIV`. (MySQL's `/` returns a decimal.) Make one side a decimal.
- `count(*)` counts rows; `count(col)` counts non-NULL values.
- SQLite is **dynamically typed**: a column's declared type is only a
  *preference* (affinity). `STRICT` tables (lesson 08) enforce types.
  PostgreSQL and MySQL are strict by default.
- String quotes are `'single'`. `"double"` quotes are for identifiers
  (table and column names) in standard SQL.
- `||` concatenates in standard SQL and SQLite; MySQL uses `CONCAT()`.
- Keywords are case-insensitive. Writing them in UPPER CASE is convention.

## Exercises

Each exercise is a view you fill in. The checks at the bottom stop at the
first wrong answer and name it. Replace each `SELECT NULL` with a query.

```sql file=exercise.sql
CREATE TABLE city (name TEXT, country TEXT, population INTEGER);
INSERT INTO city VALUES
  ('Tokyo', 'JP', 37400000), ('Delhi', 'IN', 31000000),
  ('Lagos', 'NG', NULL),     ('Oslo',  'NO',   700000);

-- q1: one row, one column "avg_pop": the average population of cities
--     where it is known (NULLs ignored), as a whole number via CAST.
CREATE VIEW q1 AS SELECT NULL AS avg_pop;                       -- TODO

-- q2: names of cities whose population is NOT known, one column "name".
CREATE VIEW q2 AS SELECT NULL AS name WHERE 0;                  -- TODO

-- q3: one row, column "label": 'big' if Oslo's population is over 1,000,000,
--     'small' if not, 'unknown' if it is NULL. Use CASE and a subquery.
CREATE VIEW q3 AS SELECT NULL AS label;                         -- TODO

-- q4: one row, column "pop": each city's population or 0 when unknown,
--     summed for all cities.
CREATE VIEW q4 AS SELECT NULL AS pop;                           -- TODO

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('q1 average',   (SELECT avg_pop FROM q1) IS 23033333);
INSERT INTO t VALUES ('q2 unknown',   (SELECT group_concat(name) FROM q2) IS 'Lagos');
INSERT INTO t VALUES ('q3 label',     (SELECT label FROM q3) IS 'small');
INSERT INTO t VALUES ('q4 total',     (SELECT pop FROM q4) IS 69100000);
SELECT 'PASS ' || name FROM t;
```

<details><summary>Solution</summary>

```sql file=solution.sql
CREATE TABLE city (name TEXT, country TEXT, population INTEGER);
INSERT INTO city VALUES
  ('Tokyo', 'JP', 37400000), ('Delhi', 'IN', 31000000),
  ('Lagos', 'NG', NULL),     ('Oslo',  'NO',   700000);

CREATE VIEW q1 AS SELECT CAST(avg(population) AS INTEGER) AS avg_pop FROM city;
CREATE VIEW q2 AS SELECT name FROM city WHERE population IS NULL;
CREATE VIEW q3 AS
  SELECT CASE WHEN p IS NULL THEN 'unknown'
              WHEN p > 1000000 THEN 'big'
              ELSE 'small' END AS label
  FROM (SELECT population AS p FROM city WHERE name = 'Oslo');
CREATE VIEW q4 AS SELECT sum(coalesce(population, 0)) AS pop FROM city;

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('q1 average',   (SELECT avg_pop FROM q1) IS 23033333);
INSERT INTO t VALUES ('q2 unknown',   (SELECT group_concat(name) FROM q2) IS 'Lagos');
INSERT INTO t VALUES ('q3 label',     (SELECT label FROM q3) IS 'small');
INSERT INTO t VALUES ('q4 total',     (SELECT pop FROM q4) IS 69100000);
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [02 — Filtering and sorting](02-filtering-sorting.md)
