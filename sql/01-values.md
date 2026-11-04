# SQL 01 — Values, Types and NULL

SQL is declarative: you describe the rows you want, not the loops that
find them. This track uses PostgreSQL 16.

A query is a table in, a table out. `SELECT` with no `FROM` is an
expression evaluator, which is enough to see how values behave.

## Integer division truncates

`7 / 2` is `3`. `%` is the remainder. `7 / 2.0` is `numeric`, so it prints
at full scale. Cast to `float8` when you want the short float.

```sql file=n01.sql
SELECT 1 + 2, 7 / 2, 7 % 2, 7 / 2.0, (7 / 2.0)::float8;
```

```text output
3|3|1|3.5000000000000000|3.5
```

## Strings use single quotes

`||` concatenates. A quote inside a string is `''`. `"double"` quotes name
identifiers (tables and columns), not text. Keywords are case-insensitive;
upper case is only a convention. `length` counts characters.

```sql file=n02.sql
SELECT 'it''s' || ' ' || 'SQL', length('héllo'), upper('abc');
```

```text output
it's SQL|5|ABC
```

## Every value has a type

`pg_typeof` reports the type. An untyped `NULL` is `unknown` until you cast
it; cast a literal before you ask, as in `pg_typeof('x'::text)`. `1.5` is
`numeric`. A binary literal is `bytea`. A column's type is a rule: a text
token does not go into an `integer` column.

```sql file=n03.sql
SELECT pg_typeof(1), pg_typeof(1.5), pg_typeof('x'::text), pg_typeof(NULL), pg_typeof('\xFF'::bytea);
CREATE TABLE city (name TEXT, population INTEGER);
-- expect-error
INSERT INTO city VALUES ('Tokyo', 'many');
```

```text output
integer|numeric|text|unknown|bytea
Error: invalid input syntax for type integer: "many"
```

## An alias names the column

`.headers on` prints column names for later selects. `AS` names an
expression. `.headers off` stops printing them.

```sql file=n04.sql
.headers on
SELECT 6 * 7 AS answer, 'ok' AS status;
.headers off
SELECT 1 + 1;
```

```text output
answer|status
42|ok
2
```

## NULL is unknown, and it spreads

`NULL = NULL` is NULL, not true. Arithmetic and `||` with NULL yield NULL.
Test with `IS NULL` or `IS NOT NULL`. `IS NOT DISTINCT FROM` is the
comparison that treats two NULLs as the same value.

```sql file=n05.sql
SELECT NULL + 1, NULL || 'x', NULL = NULL, NULL IS NULL,
       NULL IS NOT DISTINCT FROM NULL, 1 IS NOT DISTINCT FROM NULL;
```

```text output
|||t|t|f
```

## WHERE keeps only TRUE

A comparison is a boolean: `t`, `f`, or unknown. `WHERE` drops unknown
rows, so `population <> 37400000` skips Lagos. `NULL AND false` is false,
because the false decides it. `NULL OR true` is true. `NOT NULL` is
unknown. An integer is not a boolean.

```sql file=n06.sql
SELECT 1 = 1, 1 = 2, NULL = 1, NULL AND false, NULL OR true, NOT NULL;

CREATE TABLE city (name TEXT, population INTEGER);
INSERT INTO city VALUES ('Tokyo', 37400000), ('Oslo', 700000), ('Lagos', NULL);
SELECT name FROM city WHERE population <> 37400000;
```

```text output
t|f||f|t|
Oslo
```

## coalesce and nullif handle NULL on purpose

`coalesce` returns the first non-NULL argument. `nullif(a, b)` returns
NULL when `a` equals `b`, and `a` otherwise.

```sql file=n07.sql
SELECT coalesce(NULL, NULL, 'third'), coalesce(NULL, 'fallback'), nullif(5, 5), nullif(5, 6);
```

```text output
third|fallback||5
```

## CASE is if/else as an expression

`CASE` returns one value. It does not control flow. The first true `WHEN`
wins, otherwise `ELSE` does.

```sql file=n08.sql
SELECT CASE WHEN 15 % 15 = 0 THEN 'FizzBuzz'
            WHEN 15 % 3 = 0  THEN 'Fizz'
            ELSE '15' END;
```

```text output
FizzBuzz
```

## count(column) skips NULL

`count(*)` counts rows. `count(population)` counts values that are not
NULL. A NULL population prints as an empty field.

```sql file=n09.sql
CREATE TABLE city (name TEXT, country TEXT, population INTEGER);
INSERT INTO city VALUES
  ('Tokyo',  'JP', 37400000),
  ('Delhi',  'IN', 31000000),
  ('Lagos',  'NG', NULL),
  ('Oslo',   'NO',   700000);
SELECT name, population FROM city;
SELECT count(*), count(population) FROM city;
SELECT name FROM city WHERE population IS NULL;
```

```text output
Tokyo|37400000
Delhi|31000000
Lagos|
Oslo|700000
4|3
Lagos
```

## Text is not a number

`'5' + '5'` is an error: a quoted literal is `unknown`, and `unknown` is
not added. Concatenate with `||`. Cast with `CAST` or `::` before you do
arithmetic. `CAST` of `numeric` to `integer` rounds. `trunc` chops toward
zero.

```sql file=n10.sql
-- expect-error
SELECT '5' + '5';
SELECT CAST('42' AS INTEGER) + 1, trunc(3.99)::INTEGER, CAST(3.99 AS INTEGER), '5' || '5';
```

```text output
Error: operator is not unique: unknown + unknown
43|3|4|55
```

## greatest and least compare several values

`round` with no precision returns a `numeric` rounded to a whole number.
`max` and `min` are aggregates (lesson 03): they do not take a list of
arguments. `greatest` and `least` do. They skip NULL unless every argument
is NULL.

```sql file=n11.sql
SELECT round(2.5), round(3.14159, 2), abs(-4), greatest(3, 9, 5), least(3, 9, 5);
```

```text output
3|3.14|4|9|3
```

## Exercises

Each exercise is a view you fill in. The checks at the bottom stop at the
first wrong answer and name it. Replace each stub with a query.

```sql file=exercise.sql
CREATE TABLE city (name TEXT, country TEXT, population INTEGER);
INSERT INTO city VALUES
  ('Tokyo', 'JP', 37400000), ('Delhi', 'IN', 31000000),
  ('Lagos', 'NG', NULL),     ('Oslo',  'NO',   700000);

-- q1: one row, one column "avg_pop": the average population of cities
--     where it is known (NULLs ignored), rounded to a whole number via CAST.
CREATE VIEW q1 AS SELECT NULL::INTEGER AS avg_pop;                  -- TODO

-- q2: names of cities whose population is NOT known, one column "name".
CREATE VIEW q2 AS SELECT NULL::TEXT AS name WHERE false;            -- TODO

-- q3: one row, column "label": 'big' if Oslo's population is over 1,000,000,
--     'small' if not, 'unknown' if it is NULL. Use CASE and a subquery.
CREATE VIEW q3 AS SELECT NULL::TEXT AS label;                       -- TODO

-- q4: one row, column "pop": each city's population or 0 when unknown,
--     summed for all cities.
CREATE VIEW q4 AS SELECT NULL::BIGINT AS pop;                       -- TODO

CREATE TABLE t (name TEXT, ok BOOLEAN CHECK (ok));
INSERT INTO t VALUES ('q1 average', (SELECT avg_pop FROM q1) IS NOT DISTINCT FROM 23033333);
INSERT INTO t VALUES ('q2 unknown', (SELECT string_agg(name, ',') FROM q2) IS NOT DISTINCT FROM 'Lagos');
INSERT INTO t VALUES ('q3 label',   (SELECT label FROM q3) IS NOT DISTINCT FROM 'small');
INSERT INTO t VALUES ('q4 total',   (SELECT pop FROM q4) IS NOT DISTINCT FROM 69100000);
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

CREATE TABLE t (name TEXT, ok BOOLEAN CHECK (ok));
INSERT INTO t VALUES ('q1 average', (SELECT avg_pop FROM q1) IS NOT DISTINCT FROM 23033333);
INSERT INTO t VALUES ('q2 unknown', (SELECT string_agg(name, ',') FROM q2) IS NOT DISTINCT FROM 'Lagos');
INSERT INTO t VALUES ('q3 label',   (SELECT label FROM q3) IS NOT DISTINCT FROM 'small');
INSERT INTO t VALUES ('q4 total',   (SELECT pop FROM q4) IS NOT DISTINCT FROM 69100000);
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [02 — Filtering and sorting](02-filtering-sorting.md)
