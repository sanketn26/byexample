# SQL 03 — Aggregation and GROUP BY

An **aggregate** collapses many rows into one value: `count`, `sum`, `avg`,
`min`, `max`, `group_concat`. `GROUP BY` does it once per group instead of
once for the whole table. `HAVING` filters the *groups*; `WHERE` filters the
*rows* before grouping.

## Example

```sql file=example.sql
CREATE TABLE sale (
  id INTEGER PRIMARY KEY, region TEXT, product TEXT, qty INTEGER, unit_price REAL, sold_on TEXT
);
INSERT INTO sale (region, product, qty, unit_price, sold_on) VALUES
  ('north', 'widget', 10, 2.50, '2024-01-05'),
  ('north', 'gadget',  3, 9.00, '2024-01-17'),
  ('south', 'widget',  7, 2.50, '2024-02-02'),
  ('south', 'widget',  5, 2.60, '2024-02-20'),
  ('south', 'gizmo',   1, 40.0, '2024-03-01'),
  ('east',  'gadget',  4, 9.00, '2024-03-09'),
  ('east',  'gadget', NULL, 9.00, '2024-03-10');

.headers on
-- Whole-table aggregates: one row out
SELECT count(*) AS rows, count(qty) AS with_qty, sum(qty) AS units,
       min(sold_on) AS first, max(sold_on) AS last
FROM sale;

-- avg ignores NULLs; sum of nothing is NULL, count of nothing is 0
SELECT avg(qty) AS avg_qty, sum(qty) FILTER (WHERE region = 'nowhere') AS none,
       count(*) FILTER (WHERE region = 'nowhere') AS zero
FROM sale;

-- GROUP BY: one row per group
SELECT region, count(*) AS n, sum(qty * unit_price) AS revenue
FROM sale GROUP BY region ORDER BY region;

-- Group by several columns, or by an expression
SELECT region, product, sum(qty) AS units
FROM sale GROUP BY region, product ORDER BY region, product;
SELECT substr(sold_on, 1, 7) AS month, count(*) AS n
FROM sale GROUP BY month ORDER BY month;

-- HAVING filters groups; WHERE filters rows first
SELECT product, sum(qty) AS units
FROM sale WHERE unit_price < 20
GROUP BY product HAVING sum(qty) >= 10 ORDER BY product;

-- group_concat builds a list per group
SELECT region, group_concat(DISTINCT product) AS products
FROM sale GROUP BY region ORDER BY region;

-- Conditional aggregation: pivot with CASE or FILTER
SELECT product,
       sum(CASE WHEN region = 'north' THEN qty ELSE 0 END) AS north,
       sum(qty) FILTER (WHERE region = 'south') AS south
FROM sale GROUP BY product ORDER BY product;

-- count(DISTINCT x)
SELECT count(DISTINCT product) AS products, count(DISTINCT region) AS regions FROM sale;

-- Percent of total: a scalar subquery inside the select list
SELECT region, round(100.0 * sum(qty * unit_price) /
       (SELECT sum(qty * unit_price) FROM sale), 1) AS pct
FROM sale GROUP BY region ORDER BY pct DESC;
```

```text output
rows|with_qty|units|first|last
7|6|30|2024-01-05|2024-03-10
avg_qty|none|zero
5.0||0
region|n|revenue
east|2|36.0
north|2|52.0
south|3|70.5
region|product|units
east|gadget|4
north|gadget|3
north|widget|10
south|gizmo|1
south|widget|12
month|n
2024-01|2
2024-02|2
2024-03|3
product|units
widget|22
region|products
east|gadget
north|widget,gadget
south|widget,gizmo
product|north|south
gadget|3|
gizmo|0|1
widget|10|12
products|regions
3|3
region|pct
south|44.5
north|32.8
east|22.7
```

## Details that bite

- Every selected column must be either in `GROUP BY` or inside an
  aggregate. PostgreSQL enforces this. SQLite and old MySQL quietly pick
  an arbitrary row's value, which is a bug waiting for a data change.
- `count(*)` vs `count(col)` vs `count(DISTINCT col)` are three different
  numbers once NULLs and duplicates exist.
- `sum`/`avg` skip NULLs; `avg` of `(10, NULL)` is 10, not 5. Use
  `avg(coalesce(x, 0))` when "missing" really means zero.
- `sum` over zero rows is **NULL**, not 0: wrap in `coalesce(sum(x), 0)`.
- `WHERE sum(x) > 5` is an error: aggregates are not available before
  grouping. That is what `HAVING` is for.
- Filtering in `WHERE` is cheaper than `HAVING` when the condition does
  not depend on an aggregate: it removes rows before they are grouped.
- Integer math: `avg` returns a real in SQLite; `sum` of integers stays an
  integer. In PostgreSQL `avg(int)` is `numeric`, `sum(int)` is `bigint`.
- Join first, then aggregate: aggregating after a one-to-many join
  multiplies the numbers (lesson 04).
- `FILTER (WHERE ...)` is standard SQL and PostgreSQL/SQLite support it;
  MySQL needs the `CASE` form.

## Exercises

```sql file=exercise.sql
CREATE TABLE sale (
  id INTEGER PRIMARY KEY, region TEXT, product TEXT, qty INTEGER, unit_price REAL, sold_on TEXT
);
INSERT INTO sale (region, product, qty, unit_price, sold_on) VALUES
  ('north', 'widget', 10, 2.50, '2024-01-05'),
  ('north', 'gadget',  3, 9.00, '2024-01-17'),
  ('south', 'widget',  7, 2.50, '2024-02-02'),
  ('south', 'widget',  5, 2.60, '2024-02-20'),
  ('south', 'gizmo',   1, 40.0, '2024-03-01'),
  ('east',  'gadget',  4, 9.00, '2024-03-09'),
  ('east',  'gadget', NULL, 9.00, '2024-03-10');

-- q1: total revenue (qty * unit_price) per region, only regions with revenue
--     over 50, ordered by revenue descending. Columns: region, revenue.
CREATE VIEW q1 AS SELECT NULL AS region, NULL AS revenue WHERE 0;       -- TODO

-- q2: the number of sales rows that have NO quantity. Column: n.
CREATE VIEW q2 AS SELECT NULL AS n;                                     -- TODO

-- q3: per product, the average unit_price rounded to 2 decimals, for
--     products sold more than once. Columns: product, avg_price (by product).
CREATE VIEW q3 AS SELECT NULL AS product, NULL AS avg_price WHERE 0;    -- TODO

-- q4: per month ('2024-01' style), total units, treating missing qty as 0.
--     Columns: month, units, ordered by month.
CREATE VIEW q4 AS SELECT NULL AS month, NULL AS units WHERE 0;          -- TODO

-- q5: the region with the highest total units. One row, column: region.
CREATE VIEW q5 AS SELECT NULL AS region WHERE 0;                        -- TODO

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('q1', (SELECT group_concat(region || '=' || revenue, ',') FROM q1) IS 'south=70.5,north=52.0');
INSERT INTO t VALUES ('q2', (SELECT n FROM q2) IS 1);
INSERT INTO t VALUES ('q3', (SELECT group_concat(product || '=' || avg_price, ',') FROM (SELECT * FROM q3 ORDER BY product)) IS 'gadget=9.0,widget=2.53');
INSERT INTO t VALUES ('q4', (SELECT group_concat(month || '=' || units, ',') FROM q4) IS '2024-01=13,2024-02=12,2024-03=5');
INSERT INTO t VALUES ('q5', (SELECT region FROM q5) IS 'south');
SELECT 'PASS ' || name FROM t;
```

<details><summary>Solution</summary>

```sql file=solution.sql
CREATE TABLE sale (
  id INTEGER PRIMARY KEY, region TEXT, product TEXT, qty INTEGER, unit_price REAL, sold_on TEXT
);
INSERT INTO sale (region, product, qty, unit_price, sold_on) VALUES
  ('north', 'widget', 10, 2.50, '2024-01-05'),
  ('north', 'gadget',  3, 9.00, '2024-01-17'),
  ('south', 'widget',  7, 2.50, '2024-02-02'),
  ('south', 'widget',  5, 2.60, '2024-02-20'),
  ('south', 'gizmo',   1, 40.0, '2024-03-01'),
  ('east',  'gadget',  4, 9.00, '2024-03-09'),
  ('east',  'gadget', NULL, 9.00, '2024-03-10');

CREATE VIEW q1 AS
  SELECT region, sum(qty * unit_price) AS revenue FROM sale
  GROUP BY region HAVING sum(qty * unit_price) > 50 ORDER BY revenue DESC;
CREATE VIEW q2 AS SELECT count(*) AS n FROM sale WHERE qty IS NULL;
CREATE VIEW q3 AS
  SELECT product, round(avg(unit_price), 2) AS avg_price FROM sale
  GROUP BY product HAVING count(*) > 1;
CREATE VIEW q4 AS
  SELECT substr(sold_on, 1, 7) AS month, sum(coalesce(qty, 0)) AS units FROM sale
  GROUP BY month ORDER BY month;
CREATE VIEW q5 AS
  SELECT region FROM sale GROUP BY region ORDER BY sum(qty) DESC LIMIT 1;

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('q1', (SELECT group_concat(region || '=' || revenue, ',') FROM q1) IS 'south=70.5,north=52.0');
INSERT INTO t VALUES ('q2', (SELECT n FROM q2) IS 1);
INSERT INTO t VALUES ('q3', (SELECT group_concat(product || '=' || avg_price, ',') FROM (SELECT * FROM q3 ORDER BY product)) IS 'gadget=9.0,widget=2.53');
INSERT INTO t VALUES ('q4', (SELECT group_concat(month || '=' || units, ',') FROM q4) IS '2024-01=13,2024-02=12,2024-03=5');
INSERT INTO t VALUES ('q5', (SELECT region FROM q5) IS 'south');
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [04 — Joins](04-joins.md)
