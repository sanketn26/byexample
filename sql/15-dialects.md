# SQL 15 — Dialects: SQLite, PostgreSQL, MySQL

SQL is a standard, and every database speaks a *dialect*. About 80% of what
you wrote in this track runs unchanged on all three. The remaining 20% is
where migrations and "it worked locally" bugs live. This lesson maps the
differences and shows how to write the portable core.

## Example

```sql file=example.sql
-- The portable core: standard joins, grouping, CASE, COALESCE, CAST, EXISTS,
-- window functions, CTEs. Same text, same answer, on all three databases.
CREATE TABLE t (id INTEGER PRIMARY KEY, grp TEXT, v INTEGER, note TEXT);
INSERT INTO t VALUES (1, 'a', 10, NULL), (2, 'a', 20, 'x'), (3, 'b', 5, 'y'), (4, 'b', NULL, 'z');

.headers on
SELECT grp, count(*) AS n, count(v) AS n_v, sum(v) AS total, coalesce(avg(v), 0) AS mean
FROM t GROUP BY grp ORDER BY grp;

SELECT id, CASE WHEN v IS NULL THEN 'missing' WHEN v >= 10 THEN 'big' ELSE 'small' END AS size,
       CAST(coalesce(v, 0) AS INTEGER) AS v0,
       row_number() OVER (PARTITION BY grp ORDER BY id) AS rn
FROM t ORDER BY id;

WITH totals AS (SELECT grp, sum(v) AS s FROM t GROUP BY grp)
SELECT t.id FROM t JOIN totals USING (grp) WHERE totals.s > 10 AND EXISTS (SELECT 1 FROM t t2 WHERE t2.grp = t.grp AND t2.id <> t.id)
ORDER BY t.id;

-- Where dialects differ, with the portable spelling when one exists:
--
--  Concept            SQLite                 PostgreSQL               MySQL
--  -----------------  ---------------------  -----------------------  ---------------------
--  Auto id            INTEGER PRIMARY KEY    GENERATED ... IDENTITY   AUTO_INCREMENT
--  String concat      a || b                 a || b                   CONCAT(a, b)
--  Limit rows         LIMIT n OFFSET m       LIMIT n OFFSET m         LIMIT m, n  /  LIMIT n OFFSET m
--  Top-1 SQL standard FETCH FIRST (no)       FETCH FIRST n ROWS ONLY  (no; use LIMIT)
--  Upsert             ON CONFLICT DO UPDATE  ON CONFLICT DO UPDATE    ON DUPLICATE KEY UPDATE
--  RETURNING          yes (3.35+)            yes                      no (MariaDB yes)
--  Boolean type       0/1 integers           boolean                  TINYINT(1)
--  Case-insens match  LIKE (ASCII)           ILIKE                    LIKE (default collation)
--  Current time       datetime('now')        now()                    NOW()
--  Add a day          date(x, '+1 day')      x + interval '1 day'     DATE_ADD(x, INTERVAL 1 DAY)
--  Date truncate      strftime('%Y-%m',x)    date_trunc('month', x)   DATE_FORMAT(x, '%Y-%m-01')
--  JSON get text      payload ->> '$.a'      payload ->> 'a'          payload ->> '$.a'
--  String agg         group_concat(x, ',')   string_agg(x, ',')       GROUP_CONCAT(x SEPARATOR ',')
--  Full outer join    yes (3.39+)            yes                      no
--  Types              dynamic (STRICT opt.)  strict                   strict
--  DDL in a tx        yes                    yes                      no (implicit commit)

-- Portable substitutes
SELECT coalesce(note, '-') AS note FROM t ORDER BY id;          -- not ifnull / nvl / isnull
SELECT CASE WHEN v IS NULL THEN 0 ELSE 1 END AS has_v FROM t;   -- not iif()
SELECT upper(note) FROM t WHERE note IS NOT NULL ORDER BY id;   -- lower()/upper() everywhere
SELECT substr(grp, 1, 1) AS first_letter FROM t ORDER BY id LIMIT 1;  -- substr: all three
```

```text output
grp|n|n_v|total|mean
a|2|2|30|15.0
b|2|1|5|5.0
id|size|v0|rn
1|big|10|1
2|big|20|2
3|small|5|1
4|missing|0|2
id
1
2
note
-
x
y
z
has_v
1
1
1
0
upper(note)
X
Y
Z
first_letter
a
```

## Details that bite

- **The ORM and the production database should be the same engine** as the
  one you test against. SQLite in tests and PostgreSQL in production hides
  type, collation, locking and date bugs until deploy day.
- PostgreSQL is strict about types and `GROUP BY`; SQLite and old MySQL are
  forgiving. Code that passes on the forgiving one can fail on the strict
  one, never the reverse. Develop against the strict one.
- `ORDER BY` NULL placement, string comparison case, and integer division
  differ. Spell out `NULLS LAST` (PostgreSQL), `COLLATE`, and
  `CAST(x AS NUMERIC)` where it matters.
- Identifiers: unquoted names are case-folded (PostgreSQL to lower case,
  MySQL depends on the OS). Quoted `"Name"` is case-sensitive in
  PostgreSQL; MySQL quotes with backticks.
- Parameters: `?` (SQLite, MySQL drivers), `$1` (PostgreSQL native), `%s`
  (Python psycopg). Always bind; never concatenate.
- Transactions and DDL: PostgreSQL and SQLite roll DDL back; MySQL commits
  implicitly. Plan migrations accordingly.
- Locking: SQLite has one writer at a time; PostgreSQL uses MVCC with
  row locks (`FOR UPDATE`, `SKIP LOCKED`); MySQL/InnoDB uses gap locks that
  can surprise you.
- Extensions: PostgreSQL has arrays, `jsonb`, ranges, full-text search,
  `LISTEN/NOTIFY`. Use them knowingly: each one is a lock-in decision.
- Where to practise the others: `docker run postgres` or `mysql` in one
  command, or an online playground. This track's habits transfer; only
  the table above changes.

## Exercises

```sql file=exercise.sql
CREATE TABLE t (id INTEGER PRIMARY KEY, grp TEXT, v INTEGER, note TEXT);
INSERT INTO t VALUES (1, 'a', 10, NULL), (2, 'a', 20, 'x'), (3, 'b', 5, 'y'), (4, 'b', NULL, 'z');

-- Each view below is written with SQLite-only features. Rewrite it with the
-- portable core so it also runs on PostgreSQL and MySQL, giving the same
-- rows. The checks look at your SQL text as well as its results.
--
--   q1: ifnull(note, '-')               -> use coalesce
--   q2: iif(v > 6, 'hi', 'lo')          -> use CASE WHEN
--   q3: group_concat is not portable: return columns grp, n (count(*)) and
--       top (max(v)) per group instead of a list of ids
--   q4: each group's row with the highest v (ties: lower id); NULL v ignored.
--       Return column id only. Use row_number() and filter rn = 1 (no LIMIT)
CREATE VIEW q1 AS SELECT id, ifnull(note, '-') AS note FROM t;
CREATE VIEW q2 AS SELECT id, iif(v > 6, 'hi', 'lo') AS size FROM t WHERE v IS NOT NULL;
CREATE VIEW q3 AS SELECT grp, group_concat(id) AS ids FROM t GROUP BY grp;
CREATE VIEW q4 AS SELECT id FROM t WHERE v IS NOT NULL ORDER BY v DESC LIMIT 1;

CREATE TEMP TABLE t_ (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t_ VALUES ('q1 rows', (SELECT group_concat(note) FROM (SELECT * FROM q1 ORDER BY id)) IS '-,x,y,z');
INSERT INTO t_ VALUES ('q1 portable', (SELECT sql NOT LIKE '%ifnull%' FROM sqlite_master WHERE name = 'q1') IS 1);
INSERT INTO t_ VALUES ('q2 rows', (SELECT group_concat(size) FROM (SELECT * FROM q2 ORDER BY id)) IS 'hi,hi,lo');
INSERT INTO t_ VALUES ('q2 portable', (SELECT sql NOT LIKE '%iif(%' FROM sqlite_master WHERE name = 'q2') IS 1);
INSERT INTO t_ VALUES ('q3 rows', (SELECT group_concat(grp || '=' || n || '/' || top) FROM (SELECT * FROM q3 ORDER BY grp)) IS 'a=2/20,b=2/5');
INSERT INTO t_ VALUES ('q3 portable', (SELECT sql NOT LIKE '%group_concat%' FROM sqlite_master WHERE name = 'q3') IS 1);
INSERT INTO t_ VALUES ('q4 rows', (SELECT group_concat(id) FROM (SELECT * FROM q4 ORDER BY id)) IS '2,3');
INSERT INTO t_ VALUES ('q4 portable', (SELECT sql LIKE '%row_number%' AND sql NOT LIKE '%LIMIT%' FROM sqlite_master WHERE name = 'q4') IS 1);
SELECT 'PASS ' || name FROM t_;
```

<details><summary>Solution</summary>

```sql file=solution.sql
CREATE TABLE t (id INTEGER PRIMARY KEY, grp TEXT, v INTEGER, note TEXT);
INSERT INTO t VALUES (1, 'a', 10, NULL), (2, 'a', 20, 'x'), (3, 'b', 5, 'y'), (4, 'b', NULL, 'z');

CREATE VIEW q1 AS SELECT id, coalesce(note, '-') AS note FROM t;
CREATE VIEW q2 AS
  SELECT id, CASE WHEN v > 6 THEN 'hi' ELSE 'lo' END AS size FROM t WHERE v IS NOT NULL;
CREATE VIEW q3 AS SELECT grp, count(*) AS n, max(v) AS top FROM t GROUP BY grp;
CREATE VIEW q4 AS
  SELECT id FROM (
    SELECT id, row_number() OVER (PARTITION BY grp ORDER BY v DESC, id) AS rn
    FROM t WHERE v IS NOT NULL
  ) ranked WHERE rn = 1;

CREATE TEMP TABLE t_ (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t_ VALUES ('q1 rows', (SELECT group_concat(note) FROM (SELECT * FROM q1 ORDER BY id)) IS '-,x,y,z');
INSERT INTO t_ VALUES ('q1 portable', (SELECT sql NOT LIKE '%ifnull%' FROM sqlite_master WHERE name = 'q1') IS 1);
INSERT INTO t_ VALUES ('q2 rows', (SELECT group_concat(size) FROM (SELECT * FROM q2 ORDER BY id)) IS 'hi,hi,lo');
INSERT INTO t_ VALUES ('q2 portable', (SELECT sql NOT LIKE '%iif(%' FROM sqlite_master WHERE name = 'q2') IS 1);
INSERT INTO t_ VALUES ('q3 rows', (SELECT group_concat(grp || '=' || n || '/' || top) FROM (SELECT * FROM q3 ORDER BY grp)) IS 'a=2/20,b=2/5');
INSERT INTO t_ VALUES ('q3 portable', (SELECT sql NOT LIKE '%group_concat%' FROM sqlite_master WHERE name = 'q3') IS 1);
INSERT INTO t_ VALUES ('q4 rows', (SELECT group_concat(id) FROM (SELECT * FROM q4 ORDER BY id)) IS '2,3');
INSERT INTO t_ VALUES ('q4 portable', (SELECT sql LIKE '%row_number%' AND sql NOT LIKE '%LIMIT%' FROM sqlite_master WHERE name = 'q4') IS 1);
SELECT 'PASS ' || name FROM t_;
```

</details>
