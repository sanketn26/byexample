# SQL 06 — Window Functions

`GROUP BY` collapses rows. A **window function** computes over a set of
related rows but **keeps every row**. That solves rankings, running totals,
"previous row" comparisons and "top N per group" without self-joins.

Shape: `function(...) OVER (PARTITION BY ... ORDER BY ... frame)`

## Example

```sql file=example.sql
CREATE TABLE sale (id INTEGER PRIMARY KEY, rep TEXT, region TEXT, day TEXT, amount INTEGER);
INSERT INTO sale (rep, region, day, amount) VALUES
  ('ann', 'east', '2024-01-01', 100), ('ann', 'east', '2024-01-02', 150),
  ('bob', 'east', '2024-01-01',  90), ('bob', 'east', '2024-01-03', 150),
  ('cat', 'west', '2024-01-01', 200), ('cat', 'west', '2024-01-02',  50),
  ('dan', 'west', '2024-01-02', 120);

.headers on
-- 1. Aggregate over a window: the total next to every row
SELECT rep, amount, sum(amount) OVER () AS grand_total,
       sum(amount) OVER (PARTITION BY region) AS region_total
FROM sale ORDER BY id;

-- 2. Ranking: row_number, rank (ties share, gaps), dense_rank (no gaps)
SELECT rep, amount,
       row_number() OVER (ORDER BY amount DESC, id) AS rn,
       rank()       OVER (ORDER BY amount DESC)     AS rnk,
       dense_rank() OVER (ORDER BY amount DESC)     AS dense
FROM sale ORDER BY amount DESC, id;

-- 3. Top N per group: rank inside a partition, then filter in an outer query
SELECT region, rep, amount FROM (
  SELECT region, rep, amount,
         row_number() OVER (PARTITION BY region ORDER BY amount DESC, id) AS rn
  FROM sale
) WHERE rn <= 1 ORDER BY region;

-- 4. Running total: ORDER BY inside OVER makes the window grow row by row
SELECT day, amount, sum(amount) OVER (ORDER BY day, id) AS running
FROM sale WHERE region = 'east' ORDER BY day, id;

-- 5. lag / lead: look at the previous / next row
SELECT day, amount,
       lag(amount)  OVER (ORDER BY day, id) AS prev,
       amount - lag(amount, 1, amount) OVER (ORDER BY day, id) AS change
FROM sale WHERE region = 'west' ORDER BY day, id;

-- 6. Moving average with an explicit frame
SELECT day, amount,
       round(avg(amount) OVER (ORDER BY day, id ROWS BETWEEN 1 PRECEDING AND CURRENT ROW), 1) AS avg2
FROM sale WHERE region = 'east' ORDER BY day, id;

-- 7. first_value / last_value, and a named window reused twice
SELECT rep, amount,
       first_value(rep) OVER w AS top_rep,
       round(100.0 * amount / sum(amount) OVER (PARTITION BY region), 1) AS pct
FROM sale
WINDOW w AS (PARTITION BY region ORDER BY amount DESC, id)
ORDER BY region, amount DESC, id;

-- 8. ntile: split into buckets; percent of rows
SELECT rep, amount, ntile(2) OVER (ORDER BY amount, id) AS half FROM sale ORDER BY amount, id;

-- 9. Window functions run AFTER WHERE/GROUP BY: aggregate first, then rank
SELECT region, total, rank() OVER (ORDER BY total DESC) AS place
FROM (SELECT region, sum(amount) AS total FROM sale GROUP BY region)
ORDER BY place;

-- 10. Gaps and islands: de-duplicate consecutive repeats with lag
SELECT day, amount FROM (
  SELECT day, amount, lag(amount) OVER (ORDER BY day, id) AS p FROM sale WHERE region = 'east'
) WHERE p IS NULL OR p <> amount ORDER BY day;
```

```text output
rep|amount|grand_total|region_total
ann|100|860|490
ann|150|860|490
bob|90|860|490
bob|150|860|490
cat|200|860|370
cat|50|860|370
dan|120|860|370
rep|amount|rn|rnk|dense
cat|200|1|1|1
ann|150|2|2|2
bob|150|3|2|2
dan|120|4|4|3
ann|100|5|5|4
bob|90|6|6|5
cat|50|7|7|6
region|rep|amount
east|ann|150
west|cat|200
day|amount|running
2024-01-01|100|100
2024-01-01|90|190
2024-01-02|150|340
2024-01-03|150|490
day|amount|prev|change
2024-01-01|200||0
2024-01-02|50|200|-150
2024-01-02|120|50|70
day|amount|avg2
2024-01-01|100|100.0
2024-01-01|90|95.0
2024-01-02|150|120.0
2024-01-03|150|150.0
rep|amount|top_rep|pct
ann|150|ann|30.6
bob|150|ann|30.6
ann|100|ann|20.4
bob|90|ann|18.4
cat|200|cat|54.1
dan|120|cat|32.4
cat|50|cat|13.5
rep|amount|half
cat|50|1
bob|90|1
ann|100|1
dan|120|1
ann|150|2
bob|150|2
cat|200|2
region|total|place
east|490|1
west|370|2
day|amount
2024-01-01|100
2024-01-01|90
2024-01-02|150
```

## Details that bite

- You cannot use a window function in `WHERE` or `HAVING` (it runs after
  them). Wrap it in a subquery or CTE and filter outside, as in example 3.
- `ORDER BY` inside `OVER` changes the **default frame** to "start up to
  the current row (and its peers)". Without it the frame is the whole
  partition. That is why `sum() OVER (ORDER BY ...)` is a running total.
- Default frame is `RANGE`, so **ties are peers** and share the same
  running total. Add a unique tie-breaker (`ORDER BY day, id`) or say
  `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`.
- `last_value()` with the default frame returns the *current* row, not the
  partition's last. Specify `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`.
- `row_number()` over ties picks arbitrarily: add a tie-breaker to make the
  result deterministic.
- `rank` leaves gaps (1,1,3), `dense_rank` does not (1,1,2).
- Window functions need SQLite 3.25+, MySQL 8+, any modern PostgreSQL.

## Exercises

```sql file=exercise.sql
CREATE TABLE sale (id INTEGER PRIMARY KEY, rep TEXT, region TEXT, day TEXT, amount INTEGER);
INSERT INTO sale (rep, region, day, amount) VALUES
  ('ann', 'east', '2024-01-01', 100), ('ann', 'east', '2024-01-02', 150),
  ('bob', 'east', '2024-01-01',  90), ('bob', 'east', '2024-01-03', 150),
  ('cat', 'west', '2024-01-01', 200), ('cat', 'west', '2024-01-02',  50),
  ('dan', 'west', '2024-01-02', 120);

-- q1: each sale's amount and its share of its REGION's total as a whole
--     percent (round). Columns: id, pct; ordered by id.
CREATE VIEW q1 AS SELECT NULL AS id, NULL AS pct WHERE 0;               -- TODO

-- q2: the two biggest sales in each region (ties broken by lower id).
--     Columns: region, rep, amount; ordered by region, amount DESC, id.
CREATE VIEW q2 AS SELECT NULL AS region, NULL AS rep, NULL AS amount WHERE 0;  -- TODO

-- q3: a running total of amount over ALL sales ordered by day then id.
--     Columns: id, running; ordered by day, id.
CREATE VIEW q3 AS SELECT NULL AS id, NULL AS running WHERE 0;           -- TODO

-- q4: for each rep, how much more (or less) their sale was than that same
--     rep's previous sale (by day); NULL for a rep's first sale.
--     Columns: id, delta; only rows where delta is not NULL, by id.
CREATE VIEW q4 AS SELECT NULL AS id, NULL AS delta WHERE 0;             -- TODO

-- q5: dense rank of each distinct amount, highest amount = 1.
--     Columns: amount, place; distinct amounts only, ordered by place.
CREATE VIEW q5 AS SELECT NULL AS amount, NULL AS place WHERE 0;         -- TODO

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('q1', (SELECT group_concat(id || ':' || pct, ',') FROM q1) IS '1:20,2:31,3:18,4:31,5:54,6:14,7:32');
INSERT INTO t VALUES ('q2', (SELECT group_concat(region || '/' || rep || '/' || amount, ',') FROM q2) IS 'east/ann/150,east/bob/150,west/cat/200,west/dan/120');
INSERT INTO t VALUES ('q3', (SELECT group_concat(id || ':' || running, ',') FROM q3) IS '1:100,3:190,5:390,2:540,6:590,7:710,4:860');
INSERT INTO t VALUES ('q4', (SELECT group_concat(id || ':' || delta, ',') FROM q4) IS '2:50,4:60,6:-150');
INSERT INTO t VALUES ('q5', (SELECT group_concat(amount || '=' || place, ',') FROM q5) IS '200=1,150=2,120=3,100=4,90=5,50=6');
SELECT 'PASS ' || name FROM t;
```

<details><summary>Solution</summary>

```sql file=solution.sql
CREATE TABLE sale (id INTEGER PRIMARY KEY, rep TEXT, region TEXT, day TEXT, amount INTEGER);
INSERT INTO sale (rep, region, day, amount) VALUES
  ('ann', 'east', '2024-01-01', 100), ('ann', 'east', '2024-01-02', 150),
  ('bob', 'east', '2024-01-01',  90), ('bob', 'east', '2024-01-03', 150),
  ('cat', 'west', '2024-01-01', 200), ('cat', 'west', '2024-01-02',  50),
  ('dan', 'west', '2024-01-02', 120);

CREATE VIEW q1 AS
  SELECT id, CAST(round(100.0 * amount / sum(amount) OVER (PARTITION BY region)) AS INTEGER) AS pct
  FROM sale ORDER BY id;
CREATE VIEW q2 AS
  SELECT region, rep, amount FROM (
    SELECT region, rep, amount, id,
           row_number() OVER (PARTITION BY region ORDER BY amount DESC, id) AS rn
    FROM sale)
  WHERE rn <= 2 ORDER BY region, amount DESC, id;
CREATE VIEW q3 AS
  SELECT id, sum(amount) OVER (ORDER BY day, id) AS running FROM sale ORDER BY day, id;
CREATE VIEW q4 AS
  SELECT id, delta FROM (
    SELECT id, amount - lag(amount) OVER (PARTITION BY rep ORDER BY day, id) AS delta FROM sale)
  WHERE delta IS NOT NULL ORDER BY id;
CREATE VIEW q5 AS
  SELECT amount, dense_rank() OVER (ORDER BY amount DESC) AS place
  FROM (SELECT DISTINCT amount FROM sale) ORDER BY place;

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('q1', (SELECT group_concat(id || ':' || pct, ',') FROM q1) IS '1:20,2:31,3:18,4:31,5:54,6:14,7:32');
INSERT INTO t VALUES ('q2', (SELECT group_concat(region || '/' || rep || '/' || amount, ',') FROM q2) IS 'east/ann/150,east/bob/150,west/cat/200,west/dan/120');
INSERT INTO t VALUES ('q3', (SELECT group_concat(id || ':' || running, ',') FROM q3) IS '1:100,3:190,5:390,2:540,6:590,7:710,4:860');
INSERT INTO t VALUES ('q4', (SELECT group_concat(id || ':' || delta, ',') FROM q4) IS '2:50,4:60,6:-150');
INSERT INTO t VALUES ('q5', (SELECT group_concat(amount || '=' || place, ',') FROM q5) IS '200=1,150=2,120=3,100=4,90=5,50=6');
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [07 — Changing data](07-changing-data.md)
