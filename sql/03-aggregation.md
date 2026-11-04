# SQL 03 — Aggregation and GROUP BY

An aggregate collapses many rows into one value: `count`, `sum`, `avg`,
`min`, `max`, `string_agg`. `GROUP BY` does that once per group. `HAVING`
filters groups. `WHERE` filters rows before they are grouped.

## Aggregates collapse the whole table

`count(*)` counts rows. `count(qty)` skips NULL. `sum` of `integer` is
`bigint`. `avg` of `integer` is `numeric`, so a whole-number average prints
at full scale.

```sql file=n01.sql
CREATE TABLE sale (
  id INTEGER PRIMARY KEY, region TEXT, product TEXT, qty INTEGER,
  unit_price NUMERIC, sold_on TEXT
);
INSERT INTO sale (id, region, product, qty, unit_price, sold_on) VALUES
  (1, 'north', 'widget', 10, 2.50, '2024-01-05'),
  (2, 'north', 'gadget',  3, 9.00, '2024-01-17'),
  (3, 'south', 'widget',  7, 2.50, '2024-02-02'),
  (4, 'south', 'widget',  5, 2.60, '2024-02-20'),
  (5, 'south', 'gizmo',   1, 40.00, '2024-03-01'),
  (6, 'east',  'gadget',  4, 9.00, '2024-03-09'),
  (7, 'east',  'gadget', NULL, 9.00, '2024-03-10');
.headers on
SELECT count(*) AS rows, count(qty) AS with_qty, sum(qty) AS units,
       min(sold_on) AS first, max(sold_on) AS last
FROM sale;
SELECT pg_typeof(sum(qty)) AS sum_type, pg_typeof(avg(qty)) AS avg_type, avg(qty)
FROM sale;
```

```text output
rows|with_qty|units|first|last
7|6|30|2024-01-05|2024-03-10
sum_type|avg_type|avg
bigint|numeric|5.0000000000000000
```

## sum and avg skip NULL

`avg` of `(10, NULL)` is 10, not 5. Use `avg(coalesce(x, 0))` when missing
means zero. `sum` over no rows is NULL, not 0. `count(*)` over no rows is 0.
Wrap an empty sum in `coalesce(sum(x), 0)`. Cast the average to `float8`
when you want a short float: a whole number then prints as `5`, not `5.0`.

```sql file=n02.sql
CREATE TABLE sale (
  id INTEGER PRIMARY KEY, region TEXT, product TEXT, qty INTEGER,
  unit_price NUMERIC, sold_on TEXT
);
INSERT INTO sale (id, region, product, qty, unit_price, sold_on) VALUES
  (1, 'north', 'widget', 10, 2.50, '2024-01-05'),
  (2, 'north', 'gadget',  3, 9.00, '2024-01-17'),
  (3, 'south', 'widget',  7, 2.50, '2024-02-02'),
  (4, 'south', 'widget',  5, 2.60, '2024-02-20'),
  (5, 'south', 'gizmo',   1, 40.00, '2024-03-01'),
  (6, 'east',  'gadget',  4, 9.00, '2024-03-09'),
  (7, 'east',  'gadget', NULL, 9.00, '2024-03-10');
.headers on
SELECT avg(qty) AS avg_qty, avg(qty)::float8 AS avg_float,
       sum(qty) FILTER (WHERE region = 'nowhere') AS none,
       count(*) FILTER (WHERE region = 'nowhere') AS zero
FROM sale;
```

```text output
avg_qty|avg_float|none|zero
5.0000000000000000|5||0
```

## GROUP BY makes one row per group

Every selected column must be in the `GROUP BY` or inside an aggregate.
Leaving one out is an error. Joining a one-to-many table before you
aggregate multiplies the numbers (lesson 04). Aggregate first, then join.
`unit_price` is `numeric`, so revenue keeps two decimal places.

```sql file=n03.sql
CREATE TABLE sale (
  id INTEGER PRIMARY KEY, region TEXT, product TEXT, qty INTEGER,
  unit_price NUMERIC, sold_on TEXT
);
INSERT INTO sale (id, region, product, qty, unit_price, sold_on) VALUES
  (1, 'north', 'widget', 10, 2.50, '2024-01-05'),
  (2, 'north', 'gadget',  3, 9.00, '2024-01-17'),
  (3, 'south', 'widget',  7, 2.50, '2024-02-02'),
  (4, 'south', 'widget',  5, 2.60, '2024-02-20'),
  (5, 'south', 'gizmo',   1, 40.00, '2024-03-01'),
  (6, 'east',  'gadget',  4, 9.00, '2024-03-09'),
  (7, 'east',  'gadget', NULL, 9.00, '2024-03-10');
-- expect-error
SELECT region, product, sum(qty) FROM sale GROUP BY region;
.headers on
SELECT region, count(*) AS n, sum(qty * unit_price) AS revenue
FROM sale GROUP BY region ORDER BY region;
```

```text output
Error: column "sale.product" must appear in the GROUP BY clause or be used in an aggregate function
region|n|revenue
east|2|36.00
north|2|52.00
south|3|70.50
```

## Group by several columns, or by an expression

Each distinct combination is a group. `substr(sold_on, 1, 7)` groups by
month without a date type. `GROUP BY` may use that select alias.

```sql file=n04.sql
CREATE TABLE sale (
  id INTEGER PRIMARY KEY, region TEXT, product TEXT, qty INTEGER,
  unit_price NUMERIC, sold_on TEXT
);
INSERT INTO sale (id, region, product, qty, unit_price, sold_on) VALUES
  (1, 'north', 'widget', 10, 2.50, '2024-01-05'),
  (2, 'north', 'gadget',  3, 9.00, '2024-01-17'),
  (3, 'south', 'widget',  7, 2.50, '2024-02-02'),
  (4, 'south', 'widget',  5, 2.60, '2024-02-20'),
  (5, 'south', 'gizmo',   1, 40.00, '2024-03-01'),
  (6, 'east',  'gadget',  4, 9.00, '2024-03-09'),
  (7, 'east',  'gadget', NULL, 9.00, '2024-03-10');
.headers on
SELECT region, product, sum(qty) AS units
FROM sale GROUP BY region, product ORDER BY region, product;
SELECT substr(sold_on, 1, 7) AS month, count(*) AS n
FROM sale GROUP BY month ORDER BY month;
```

```text output
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
```

## HAVING filters groups, not rows

`WHERE` runs before grouping, so it cannot see `sum`. That condition is
an error in `WHERE` and legal in `HAVING`. Prefer `WHERE` when the test
does not need an aggregate: it throws rows away before they are grouped.

```sql file=n05.sql
CREATE TABLE sale (
  id INTEGER PRIMARY KEY, region TEXT, product TEXT, qty INTEGER,
  unit_price NUMERIC, sold_on TEXT
);
INSERT INTO sale (id, region, product, qty, unit_price, sold_on) VALUES
  (1, 'north', 'widget', 10, 2.50, '2024-01-05'),
  (2, 'north', 'gadget',  3, 9.00, '2024-01-17'),
  (3, 'south', 'widget',  7, 2.50, '2024-02-02'),
  (4, 'south', 'widget',  5, 2.60, '2024-02-20'),
  (5, 'south', 'gizmo',   1, 40.00, '2024-03-01'),
  (6, 'east',  'gadget',  4, 9.00, '2024-03-09'),
  (7, 'east',  'gadget', NULL, 9.00, '2024-03-10');
-- expect-error
SELECT product, sum(qty) FROM sale WHERE sum(qty) > 5 GROUP BY product;
.headers on
SELECT product, sum(qty) AS units
FROM sale WHERE unit_price < 20
GROUP BY product HAVING sum(qty) >= 10 ORDER BY product;
```

```text output
Error: aggregate functions are not allowed in WHERE
product|units
widget|22
```

## string_agg builds a list per group

The separator is required. `DISTINCT` keeps each product once. `string_agg`
skips NULL. The list order is unspecified unless you write `ORDER BY`
inside the aggregate.

```sql file=n06.sql
CREATE TABLE sale (
  id INTEGER PRIMARY KEY, region TEXT, product TEXT, qty INTEGER,
  unit_price NUMERIC, sold_on TEXT
);
INSERT INTO sale (id, region, product, qty, unit_price, sold_on) VALUES
  (1, 'north', 'widget', 10, 2.50, '2024-01-05'),
  (2, 'north', 'gadget',  3, 9.00, '2024-01-17'),
  (3, 'south', 'widget',  7, 2.50, '2024-02-02'),
  (4, 'south', 'widget',  5, 2.60, '2024-02-20'),
  (5, 'south', 'gizmo',   1, 40.00, '2024-03-01'),
  (6, 'east',  'gadget',  4, 9.00, '2024-03-09'),
  (7, 'east',  'gadget', NULL, 9.00, '2024-03-10');
.headers on
SELECT region, string_agg(DISTINCT product, ',' ORDER BY product) AS products
FROM sale GROUP BY region ORDER BY region;
```

```text output
region|products
east|gadget
north|gadget,widget
south|gizmo,widget
```

## CASE or FILTER pivots a group

`FILTER (WHERE ...)` limits which rows an aggregate sees. `ELSE 0` turns a
missing region into zero; `FILTER` leaves it NULL.

```sql file=n07.sql
CREATE TABLE sale (
  id INTEGER PRIMARY KEY, region TEXT, product TEXT, qty INTEGER,
  unit_price NUMERIC, sold_on TEXT
);
INSERT INTO sale (id, region, product, qty, unit_price, sold_on) VALUES
  (1, 'north', 'widget', 10, 2.50, '2024-01-05'),
  (2, 'north', 'gadget',  3, 9.00, '2024-01-17'),
  (3, 'south', 'widget',  7, 2.50, '2024-02-02'),
  (4, 'south', 'widget',  5, 2.60, '2024-02-20'),
  (5, 'south', 'gizmo',   1, 40.00, '2024-03-01'),
  (6, 'east',  'gadget',  4, 9.00, '2024-03-09'),
  (7, 'east',  'gadget', NULL, 9.00, '2024-03-10');
.headers on
SELECT product,
       sum(CASE WHEN region = 'north' THEN qty ELSE 0 END) AS north,
       sum(qty) FILTER (WHERE region = 'south') AS south
FROM sale GROUP BY product ORDER BY product;
```

```text output
product|north|south
gadget|3|
gizmo|0|1
widget|10|12
```

## count(DISTINCT col) counts values, not rows

Three different questions: how many rows, how many non-NULL values, how
many different values. The east region has two gadget rows and one product.

```sql file=n08.sql
CREATE TABLE sale (
  id INTEGER PRIMARY KEY, region TEXT, product TEXT, qty INTEGER,
  unit_price NUMERIC, sold_on TEXT
);
INSERT INTO sale (id, region, product, qty, unit_price, sold_on) VALUES
  (1, 'north', 'widget', 10, 2.50, '2024-01-05'),
  (2, 'north', 'gadget',  3, 9.00, '2024-01-17'),
  (3, 'south', 'widget',  7, 2.50, '2024-02-02'),
  (4, 'south', 'widget',  5, 2.60, '2024-02-20'),
  (5, 'south', 'gizmo',   1, 40.00, '2024-03-01'),
  (6, 'east',  'gadget',  4, 9.00, '2024-03-09'),
  (7, 'east',  'gadget', NULL, 9.00, '2024-03-10');
.headers on
SELECT count(DISTINCT product) AS products, count(DISTINCT region) AS regions FROM sale;
```

```text output
products|regions
3|3
```

## A scalar subquery can be the denominator

The inner `sum` runs once and is one number. Divide by it to get a share
of the total. `100.0` makes the division `numeric`. `round(..., 1)` keeps
one decimal place.

```sql file=n09.sql
CREATE TABLE sale (
  id INTEGER PRIMARY KEY, region TEXT, product TEXT, qty INTEGER,
  unit_price NUMERIC, sold_on TEXT
);
INSERT INTO sale (id, region, product, qty, unit_price, sold_on) VALUES
  (1, 'north', 'widget', 10, 2.50, '2024-01-05'),
  (2, 'north', 'gadget',  3, 9.00, '2024-01-17'),
  (3, 'south', 'widget',  7, 2.50, '2024-02-02'),
  (4, 'south', 'widget',  5, 2.60, '2024-02-20'),
  (5, 'south', 'gizmo',   1, 40.00, '2024-03-01'),
  (6, 'east',  'gadget',  4, 9.00, '2024-03-09'),
  (7, 'east',  'gadget', NULL, 9.00, '2024-03-10');
.headers on
SELECT region, round(100.0 * sum(qty * unit_price) /
       (SELECT sum(qty * unit_price) FROM sale), 1) AS pct
FROM sale GROUP BY region ORDER BY pct DESC;
```

```text output
region|pct
south|44.5
north|32.8
east|22.7
```

## Exercises

```sql file=exercise.sql
CREATE TABLE sale (
  id INTEGER PRIMARY KEY, region TEXT, product TEXT, qty INTEGER,
  unit_price NUMERIC, sold_on TEXT
);
INSERT INTO sale (id, region, product, qty, unit_price, sold_on) VALUES
  (1, 'north', 'widget', 10, 2.50, '2024-01-05'),
  (2, 'north', 'gadget',  3, 9.00, '2024-01-17'),
  (3, 'south', 'widget',  7, 2.50, '2024-02-02'),
  (4, 'south', 'widget',  5, 2.60, '2024-02-20'),
  (5, 'south', 'gizmo',   1, 40.00, '2024-03-01'),
  (6, 'east',  'gadget',  4, 9.00, '2024-03-09'),
  (7, 'east',  'gadget', NULL, 9.00, '2024-03-10');

-- q1: total revenue (qty * unit_price) per region, only regions with revenue
--     over 50, ordered by revenue descending. Columns: region, revenue.
CREATE VIEW q1 AS SELECT NULL::TEXT AS region, NULL::NUMERIC AS revenue WHERE false;  -- TODO

-- q2: the number of sales rows that have NO quantity. Column: n.
CREATE VIEW q2 AS SELECT NULL::BIGINT AS n;                          -- TODO

-- q3: per product, the average unit_price rounded to 2 decimals, for
--     products sold more than once. Columns: product, avg_price (by product).
CREATE VIEW q3 AS SELECT NULL::TEXT AS product, NULL::NUMERIC AS avg_price WHERE false;  -- TODO

-- q4: per month ('2024-01' style), total units, treating missing qty as 0.
--     Columns: month, units, ordered by month.
CREATE VIEW q4 AS SELECT NULL::TEXT AS month, NULL::BIGINT AS units WHERE false;  -- TODO

-- q5: the region with the highest total units. North and south tie;
--     pick the name that sorts last. One row, column: region.
CREATE VIEW q5 AS SELECT NULL::TEXT AS region WHERE false;           -- TODO

CREATE TABLE t (name TEXT, ok BOOLEAN CHECK (ok));
INSERT INTO t VALUES ('q1', (SELECT string_agg(region || '=' || revenue, ',' ORDER BY revenue DESC) FROM q1) IS NOT DISTINCT FROM 'south=70.50,north=52.00');
INSERT INTO t VALUES ('q2', (SELECT n FROM q2) IS NOT DISTINCT FROM 1);
INSERT INTO t VALUES ('q3', (SELECT string_agg(product || '=' || avg_price, ',' ORDER BY product) FROM q3) IS NOT DISTINCT FROM 'gadget=9.00,widget=2.53');
INSERT INTO t VALUES ('q4', (SELECT string_agg(month || '=' || units, ',' ORDER BY month) FROM q4) IS NOT DISTINCT FROM '2024-01=13,2024-02=12,2024-03=5');
INSERT INTO t VALUES ('q5', (SELECT region FROM q5) IS NOT DISTINCT FROM 'south');
SELECT 'PASS ' || name FROM t;
```

<details><summary>Solution</summary>

```sql file=solution.sql
CREATE TABLE sale (
  id INTEGER PRIMARY KEY, region TEXT, product TEXT, qty INTEGER,
  unit_price NUMERIC, sold_on TEXT
);
INSERT INTO sale (id, region, product, qty, unit_price, sold_on) VALUES
  (1, 'north', 'widget', 10, 2.50, '2024-01-05'),
  (2, 'north', 'gadget',  3, 9.00, '2024-01-17'),
  (3, 'south', 'widget',  7, 2.50, '2024-02-02'),
  (4, 'south', 'widget',  5, 2.60, '2024-02-20'),
  (5, 'south', 'gizmo',   1, 40.00, '2024-03-01'),
  (6, 'east',  'gadget',  4, 9.00, '2024-03-09'),
  (7, 'east',  'gadget', NULL, 9.00, '2024-03-10');

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
  SELECT region FROM sale GROUP BY region
  ORDER BY sum(qty) DESC, region DESC LIMIT 1;

CREATE TABLE t (name TEXT, ok BOOLEAN CHECK (ok));
INSERT INTO t VALUES ('q1', (SELECT string_agg(region || '=' || revenue, ',' ORDER BY revenue DESC) FROM q1) IS NOT DISTINCT FROM 'south=70.50,north=52.00');
INSERT INTO t VALUES ('q2', (SELECT n FROM q2) IS NOT DISTINCT FROM 1);
INSERT INTO t VALUES ('q3', (SELECT string_agg(product || '=' || avg_price, ',' ORDER BY product) FROM q3) IS NOT DISTINCT FROM 'gadget=9.00,widget=2.53');
INSERT INTO t VALUES ('q4', (SELECT string_agg(month || '=' || units, ',' ORDER BY month) FROM q4) IS NOT DISTINCT FROM '2024-01=13,2024-02=12,2024-03=5');
INSERT INTO t VALUES ('q5', (SELECT region FROM q5) IS NOT DISTINCT FROM 'south');
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [04 — Joins](04-joins.md)
