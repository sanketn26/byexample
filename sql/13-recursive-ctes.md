# SQL 13 — Recursive Queries: Trees, Graphs and Sequences

A recursive CTE is a loop in SQL. The anchor is the starting set. The step
turns rows found so far into new rows, `UNION ALL`, until the step returns
nothing. That walks org charts, category trees, bills of materials, and
graphs. The CTE must be introduced with `WITH RECURSIVE`.

Always have a stop condition. `UNION ALL` with no `WHERE` and no depth cap
runs until the statement is cancelled. Add `WHERE depth < N` as a backstop.
The recursive part may reference the CTE only once, in `FROM`. It may not
use aggregates, `DISTINCT`, or `ORDER BY`. The anchor fixes column names
and types, and the step has to match. Cast the anchor when the step
produces a wider type. Output order is undefined until an outer
`ORDER BY`. A `path` or `sortkey` column is the usual sort key.
`string_agg` needs its own `ORDER BY`: it does not follow the walk.

`SEARCH` and `CYCLE`, added in PostgreSQL 14, mark breadth-first order and
cycle rows. For a plain sequence of numbers or timestamps, use
`generate_series` instead of a recursive CTE.

## The anchor starts, the step walks, the WHERE stops

`SELECT 1` is the anchor. `i + 1` is the step. `WHERE i < 5` stops the
walk. The column name `i` comes from the anchor. The outer `ORDER BY`
makes the sequence stable.

```sql file=n01.sql
.headers on
SELECT i FROM (
  WITH RECURSIVE n(i) AS (
    SELECT 1
    UNION ALL
    SELECT i + 1 FROM n WHERE i < 5
  )
  SELECT i FROM n
) s ORDER BY i;
```

```text output
i
1
2
3
4
5
```

## generate_series builds a calendar

A run of days does not need recursion. `generate_series` steps from a
start timestamp to a stop timestamp by an `interval`. Cast to `date` for a
calendar column. `extract(dow FROM day)` is the weekday, 0 on Sunday, so
27 February 2024, a Tuesday, is 2. 2024 is a leap year, so 29 February is
in the series.

```sql file=n02.sql
.headers on
SELECT gs::date AS day, extract(dow FROM gs)::int AS weekday
FROM generate_series(
  timestamp '2024-02-27', timestamp '2024-03-02', interval '1 day'
) AS gs;
```

```text output
day|weekday
2024-02-27|2
2024-02-28|3
2024-02-29|4
2024-03-01|5
2024-03-02|6
```

## Walk down from a node, carrying depth and path

The anchor is Linus, depth 0. The step joins employees whose `boss_id` is
the current id. `path` is text built with `||`. `WHERE s.depth < 20` is
the backstop. `ORDER BY path` is what makes the print stable.

```sql file=n03.sql
CREATE TABLE emp (id integer PRIMARY KEY, name text, boss_id integer);
INSERT INTO emp VALUES
  (1, 'Ada', NULL), (2, 'Linus', 1), (3, 'Grace', 1),
  (4, 'Don', 2), (5, 'Peggy', 2), (6, 'Zed', 4);
.headers on
SELECT name, depth, path FROM (
  WITH RECURSIVE sub(id, name, depth, path) AS (
    SELECT id, name, 0, name FROM emp WHERE id = 2
    UNION ALL
    SELECT e.id, e.name, s.depth + 1, s.path || ' > ' || e.name
    FROM emp e JOIN sub s ON e.boss_id = s.id
    WHERE s.depth < 20
  )
  SELECT name, depth, path FROM sub
) s ORDER BY path;
```

```text output
name|depth|path
Linus|0|Linus
Don|1|Linus > Don
Zed|2|Linus > Don > Zed
Peggy|1|Linus > Peggy
```

## Walk up by joining the boss

The anchor is Zed. The step finds the employee whose id equals the current
`boss_id`. `n` counts steps so `string_agg` can print child, then boss,
then their boss. Without `ORDER BY n` the aggregate order is undefined.

```sql file=n04.sql
CREATE TABLE emp (id integer PRIMARY KEY, name text, boss_id integer);
INSERT INTO emp VALUES
  (1, 'Ada', NULL), (2, 'Linus', 1), (3, 'Grace', 1),
  (4, 'Don', 2), (5, 'Peggy', 2), (6, 'Zed', 4);
.headers on
SELECT string_agg(name, ' -> ' ORDER BY n) AS chain FROM (
  WITH RECURSIVE chain(id, name, boss_id, n) AS (
    SELECT id, name, boss_id, 1 FROM emp WHERE name = 'Zed'
    UNION ALL
    SELECT e.id, e.name, e.boss_id, c.n + 1
    FROM emp e JOIN chain c ON e.id = c.boss_id
  )
  SELECT name, n FROM chain
) s;
```

```text output
chain
Zed -> Don -> Linus -> Ada
```

## A sort key prints the tree in outline order

`lpad(id::text, 3, '0')` pads ids so text order matches numeric order.
Children append `'/'` and their key. `repeat` builds the indent from the
depth. Ada is the only root (`boss_id IS NULL`).

```sql file=n05.sql
CREATE TABLE emp (id integer PRIMARY KEY, name text, boss_id integer);
INSERT INTO emp VALUES
  (1, 'Ada', NULL), (2, 'Linus', 1), (3, 'Grace', 1),
  (4, 'Don', 2), (5, 'Peggy', 2), (6, 'Zed', 4);
.headers on
SELECT repeat(' ', depth * 2) || name AS tree FROM (
  WITH RECURSIVE t(id, name, depth, sortkey) AS (
    SELECT id, name, 0, lpad(id::text, 3, '0') FROM emp WHERE boss_id IS NULL
    UNION ALL
    SELECT e.id, e.name, t.depth + 1, t.sortkey || '/' || lpad(e.id::text, 3, '0')
    FROM emp e JOIN t ON e.boss_id = t.id
  )
  SELECT name, depth, sortkey FROM t
) s ORDER BY sortkey;
```

```text output
tree
Ada
  Linus
    Don
      Zed
    Peggy
  Grace
```

## Count descendants by carrying the root

Every person is a root of their own walk, including themselves. `count(*) - 1`
drops that self row, which leaves the number of reports. `GROUP BY` must
include `e.name`: selecting it is not free unless you group by the primary
key of `emp` itself. The `LIMIT` is only for the display.

```sql file=n06.sql
CREATE TABLE emp (id integer PRIMARY KEY, name text, boss_id integer);
INSERT INTO emp VALUES
  (1, 'Ada', NULL), (2, 'Linus', 1), (3, 'Grace', 1),
  (4, 'Don', 2), (5, 'Peggy', 2), (6, 'Zed', 4);
.headers on
SELECT e.name, count(*) - 1 AS reports FROM (
  WITH RECURSIVE sub(root, id) AS (
    SELECT id, id FROM emp
    UNION ALL
    SELECT s.root, e.id FROM emp e JOIN sub s ON e.boss_id = s.id
  )
  SELECT root, id FROM sub
) s JOIN emp e ON e.id = s.root
GROUP BY s.root, e.name
ORDER BY reports DESC, e.name
LIMIT 3;
```

```text output
name|reports
Ada|5
Linus|3
Don|1
```

## UNION drops rows already seen; CYCLE marks a loop

`a → b → c → a` never ends if the step keeps duplicates. `UNION` removes
a row that is already in the result, so the walk terminates. You can
instead carry the path and reject a node already in it.

`CYCLE node SET is_cycle USING path` lets the step stay `UNION ALL`. The
row that repeats `node` comes back with `is_cycle` true, and the walk does
not continue from it. `f` is false, `t` is true. The second `a` is that
cycle row.

```sql file=n07.sql
CREATE TABLE edge (src text, dst text);
INSERT INTO edge VALUES ('a', 'b'), ('b', 'c'), ('c', 'a'), ('c', 'd');
.headers on
SELECT string_agg(node, ',' ORDER BY node) AS reachable_from_a FROM (
  WITH RECURSIVE reach(node) AS (
    SELECT 'a' UNION SELECT dst FROM edge JOIN reach ON src = node
  )
  SELECT node FROM reach
) s;
SELECT node, is_cycle FROM (
  WITH RECURSIVE search(node) AS (
    SELECT 'a'
    UNION ALL
    SELECT e.dst FROM edge e JOIN search s ON e.src = s.node
  ) CYCLE node SET is_cycle USING path
  SELECT node, is_cycle FROM search
) s ORDER BY node, is_cycle;
```

```text output
reachable_from_a
a,b,c,d
node|is_cycle
a|f
a|t
b|f
c|f
d|f
```

## Shortest path is breadth-first with a hop cap

`UNION` drops a `(node, hops)` pair already produced. The same node at a
new distance is a different pair, so it stays. `min(hops)` is the smallest
distance, which is the shortest path in an unweighted graph.
`WHERE hops < 10` is the safety cap if the dedupe ever fails.

```sql file=n08.sql
CREATE TABLE edge (src text, dst text);
INSERT INTO edge VALUES ('a', 'b'), ('b', 'c'), ('c', 'a'), ('c', 'd');
.headers on
SELECT node, min(hops) AS hops FROM (
  WITH RECURSIVE walk(node, hops) AS (
    SELECT 'a', 0
    UNION
    SELECT dst, hops + 1 FROM edge JOIN walk ON src = node WHERE hops < 10
  )
  SELECT node, hops FROM walk
) s GROUP BY node ORDER BY hops, node;
```

```text output
node|hops
a|0
b|1
c|2
d|3
```

## The step can carry two values

Fibonacci needs the current pair. The next row is `(b, a + b)`. The
`WHERE` is tested on the row that produces the next one, so `b = 89` still
emits a successor and `b = 144` does not. `string_agg` prints `a`, so 144
never appears. `n` is only there to order the aggregate.

```sql file=n09.sql
.headers on
SELECT string_agg(a::text, ' ' ORDER BY n) AS fib FROM (
  WITH RECURSIVE fib(a, b, n) AS (
    SELECT 0, 1, 1
    UNION ALL
    SELECT b, a + b, n + 1 FROM fib WHERE b < 100
  )
  SELECT a, n FROM fib
) s;
```

```text output
fib
0 1 1 2 3 5 8 13 21 34 55 89
```
## Exercises

```sql file=exercise.sql
CREATE TABLE cat (id integer PRIMARY KEY, name text, parent_id integer);
INSERT INTO cat VALUES
  (1, 'Electronics', NULL), (2, 'Computers', 1), (3, 'Laptops', 2),
  (4, 'Phones', 1), (5, 'Gaming', 3), (6, 'Books', NULL);

-- q1: every category under 'Electronics' (not itself), with its depth below it
--     (children = 1). Columns: name, depth; ordered by depth, name.
--     Use WITH RECURSIVE.
CREATE VIEW q1 AS SELECT NULL::text AS name, NULL::integer AS depth WHERE false;  -- TODO

-- q2: the full path of 'Gaming' from the root, e.g. 'A / B / C'.
--     One row, column: path.
CREATE VIEW q2 AS SELECT NULL::text AS path;  -- TODO

-- q3: the numbers 1..10 squared, as a single comma-separated string.
--     One row, column: squares. Build 1..10 with WITH RECURSIVE, not generate_series.
CREATE VIEW q3 AS SELECT NULL::text AS squares;  -- TODO

-- q4: the depth of the deepest category in the whole table (a root = 0).
--     One row, column: max_depth.
CREATE VIEW q4 AS SELECT NULL::integer AS max_depth;  -- TODO

CREATE TABLE t (name text, ok boolean CHECK (ok));
INSERT INTO t VALUES ('q1', (SELECT string_agg(name || depth::text, ',' ORDER BY depth, name) FROM q1) IS NOT DISTINCT FROM 'Computers1,Phones1,Laptops2,Gaming3');
INSERT INTO t VALUES ('q2', (SELECT path FROM q2) IS NOT DISTINCT FROM 'Electronics / Computers / Laptops / Gaming');
INSERT INTO t VALUES ('q3', (SELECT squares FROM q3) IS NOT DISTINCT FROM '1,4,9,16,25,36,49,64,81,100');
INSERT INTO t VALUES ('q4', (SELECT max_depth FROM q4) IS NOT DISTINCT FROM 3);
SELECT 'PASS ' || name FROM t ORDER BY name;
```

<details><summary>Solution</summary>

```sql file=solution.sql
CREATE TABLE cat (id integer PRIMARY KEY, name text, parent_id integer);
INSERT INTO cat VALUES
  (1, 'Electronics', NULL), (2, 'Computers', 1), (3, 'Laptops', 2),
  (4, 'Phones', 1), (5, 'Gaming', 3), (6, 'Books', NULL);

CREATE VIEW q1 AS
  WITH RECURSIVE sub(id, name, depth) AS (
    SELECT id, name, 0 FROM cat WHERE name = 'Electronics'
    UNION ALL
    SELECT c.id, c.name, s.depth + 1 FROM cat c JOIN sub s ON c.parent_id = s.id
  )
  SELECT name, depth FROM sub WHERE depth > 0 ORDER BY depth, name;
CREATE VIEW q2 AS
  WITH RECURSIVE up(id, parent_id, path) AS (
    SELECT id, parent_id, name FROM cat WHERE name = 'Gaming'
    UNION ALL
    SELECT c.id, c.parent_id, c.name || ' / ' || u.path
    FROM cat c JOIN up u ON c.id = u.parent_id
  )
  SELECT path FROM up WHERE parent_id IS NULL;
CREATE VIEW q3 AS
  WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 10)
  SELECT string_agg((i * i)::text, ',' ORDER BY i) AS squares FROM n;
CREATE VIEW q4 AS
  WITH RECURSIVE d(id, depth) AS (
    SELECT id, 0 FROM cat WHERE parent_id IS NULL
    UNION ALL
    SELECT c.id, d.depth + 1 FROM cat c JOIN d ON c.parent_id = d.id
  )
  SELECT max(depth) AS max_depth FROM d;

CREATE TABLE t (name text, ok boolean CHECK (ok));
INSERT INTO t VALUES ('q1', (SELECT string_agg(name || depth::text, ',' ORDER BY depth, name) FROM q1) IS NOT DISTINCT FROM 'Computers1,Phones1,Laptops2,Gaming3');
INSERT INTO t VALUES ('q2', (SELECT path FROM q2) IS NOT DISTINCT FROM 'Electronics / Computers / Laptops / Gaming');
INSERT INTO t VALUES ('q3', (SELECT squares FROM q3) IS NOT DISTINCT FROM '1,4,9,16,25,36,49,64,81,100');
INSERT INTO t VALUES ('q4', (SELECT max_depth FROM q4) IS NOT DISTINCT FROM 3);
SELECT 'PASS ' || name FROM t ORDER BY name;
```

</details>

Next: [14 — Capstone: bookstore analytics](14-capstone-bookstore.md)
