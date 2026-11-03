# SQL 13 — Recursive Queries: Trees, Graphs and Sequences

A **recursive CTE** is a loop in SQL: a starting set (the *anchor*), then a
step that repeatedly turns the rows found so far into new rows
(`UNION ALL`), until nothing new appears. It is how you walk org charts,
category trees, bills of materials, and graphs, and how you generate
sequences and calendars.

## Example

```sql file=example.sql
.headers on
-- 1. Counting: anchor 1, step +1, stop with a WHERE
WITH RECURSIVE n(i) AS (
  SELECT 1                              -- anchor
  UNION ALL
  SELECT i + 1 FROM n WHERE i < 5       -- step; the WHERE is the stop condition
)
SELECT i FROM n;

-- 2. Generate a calendar
WITH RECURSIVE d(day) AS (
  SELECT '2024-02-27' UNION ALL SELECT date(day, '+1 day') FROM d WHERE day < '2024-03-02'
)
SELECT day, strftime('%w', day) AS weekday FROM d;

-- 3. Walk a tree: an org chart
CREATE TABLE emp (id INTEGER PRIMARY KEY, name TEXT, boss_id INTEGER);
INSERT INTO emp VALUES
  (1, 'Ada', NULL), (2, 'Linus', 1), (3, 'Grace', 1),
  (4, 'Don', 2), (5, 'Peggy', 2), (6, 'Zed', 4);

-- everyone under Linus, with depth and the path from the top
WITH RECURSIVE sub(id, name, depth, path) AS (
  SELECT id, name, 0, name FROM emp WHERE id = 2
  UNION ALL
  SELECT e.id, e.name, s.depth + 1, s.path || ' > ' || e.name
  FROM emp e JOIN sub s ON e.boss_id = s.id
)
SELECT name, depth, path FROM sub ORDER BY path;

-- 4. Walk UP: the chain of command for Zed
WITH RECURSIVE chain(id, name, boss_id) AS (
  SELECT id, name, boss_id FROM emp WHERE name = 'Zed'
  UNION ALL
  SELECT e.id, e.name, e.boss_id FROM emp e JOIN chain c ON e.id = c.boss_id
)
SELECT group_concat(name, ' -> ') AS chain FROM chain;

-- 5. Indented tree print
WITH RECURSIVE t(id, name, depth, sortkey) AS (
  SELECT id, name, 0, printf('%03d', id) FROM emp WHERE boss_id IS NULL
  UNION ALL
  SELECT e.id, e.name, t.depth + 1, t.sortkey || '/' || printf('%03d', e.id)
  FROM emp e JOIN t ON e.boss_id = t.id
)
SELECT printf('%s%s', substr('          ', 1, depth * 2), name) AS tree FROM t ORDER BY sortkey;

-- 6. Count descendants per person
WITH RECURSIVE sub(root, id) AS (
  SELECT id, id FROM emp
  UNION ALL
  SELECT s.root, e.id FROM emp e JOIN sub s ON e.boss_id = s.id
)
SELECT e.name, count(*) - 1 AS reports FROM sub s JOIN emp e ON e.id = s.root
GROUP BY s.root ORDER BY reports DESC, e.name LIMIT 3;

-- 7. Graphs: UNION (not ALL) removes repeats, so cycles terminate
CREATE TABLE edge (src TEXT, dst TEXT);
INSERT INTO edge VALUES ('a', 'b'), ('b', 'c'), ('c', 'a'), ('c', 'd');
WITH RECURSIVE reach(node) AS (
  SELECT 'a' UNION SELECT dst FROM edge JOIN reach ON src = node
)
SELECT group_concat(node) AS reachable_from_a FROM (SELECT node FROM reach ORDER BY node);

-- 8. Shortest path length (breadth-first), with a depth cap as a safety net
WITH RECURSIVE walk(node, hops) AS (
  SELECT 'a', 0
  UNION
  SELECT dst, hops + 1 FROM edge JOIN walk ON src = node WHERE hops < 10
)
SELECT node, min(hops) AS hops FROM walk GROUP BY node ORDER BY hops, node;

-- 9. Fibonacci: carry two values
WITH RECURSIVE fib(a, b) AS (
  SELECT 0, 1 UNION ALL SELECT b, a + b FROM fib WHERE b < 100
)
SELECT group_concat(a, ' ') AS fib FROM fib;
```

```text output
i
1
2
3
4
5
day|weekday
2024-02-27|2
2024-02-28|3
2024-02-29|4
2024-03-01|5
2024-03-02|6
name|depth|path
Linus|0|Linus
Don|1|Linus > Don
Zed|2|Linus > Don > Zed
Peggy|1|Linus > Peggy
chain
Zed -> Don -> Linus -> Ada
tree
Ada
  Linus
    Don
      Zed
    Peggy
  Grace
name|reports
Ada|5
Linus|3
Don|1
reachable_from_a
a,b,c,d
node|hops
a|0
b|1
c|2
d|3
fib
0 1 1 2 3 5 8 13 21 34 55 89
```

## Details that bite

- **Always have a stop condition.** A recursive CTE with `UNION ALL` and no
  `WHERE`/depth limit runs forever (or until the database gives up).
  Add `WHERE depth < N` as a belt-and-braces cap.
- Cyclic data (A → B → C → A) loops with `UNION ALL`. Use `UNION` to
  dedupe rows, or carry the visited path and test `path NOT LIKE '%' || id || '%'`.
- The recursive part may reference the CTE only once, in `FROM`, and
  (in most databases) cannot use aggregates, `DISTINCT` or `ORDER BY`
  inside the step.
- The anchor decides the column names and types. Make them wide enough:
  a `path` that starts as 1 char but grows will be truncated in strict
  engines (cast the anchor, or use `TEXT`).
- Output order is undefined: add `ORDER BY` outside (a `path` or
  `sortkey` column is the usual trick).
- PostgreSQL has `SEARCH` and `CYCLE` clauses to do depth/breadth-first and
  cycle detection for you (14+). MySQL 8 supports `WITH RECURSIVE`;
  older versions do not.
- Hierarchies stored with a `boss_id` pointer are easy to write and need a
  recursive query to read. Alternatives (materialised path, nested sets,
  closure tables) trade write complexity for read speed.
- For plain sequences, SQLite has the `generate_series()` table function
  when compiled in, and PostgreSQL always does.

## Exercises

```sql file=exercise.sql
CREATE TABLE cat (id INTEGER PRIMARY KEY, name TEXT, parent_id INTEGER);
INSERT INTO cat VALUES
  (1, 'Electronics', NULL), (2, 'Computers', 1), (3, 'Laptops', 2),
  (4, 'Phones', 1), (5, 'Gaming', 3), (6, 'Books', NULL);

-- q1: every category under 'Electronics' (not itself), with its depth below it
--     (children = 1). Columns: name, depth; ordered by depth, name.
CREATE VIEW q1 AS SELECT NULL AS name, NULL AS depth WHERE 0;           -- TODO

-- q2: the full path of 'Gaming' from the root, e.g. 'A / B / C'.
--     One row, column: path.
CREATE VIEW q2 AS SELECT NULL AS path;                                  -- TODO

-- q3: the numbers 1..10 squared, as a single comma-separated string.
--     One row, column: squares.
CREATE VIEW q3 AS SELECT NULL AS squares;                               -- TODO

-- q4: the depth of the deepest category in the whole table (a root = 0).
--     One row, column: max_depth.
CREATE VIEW q4 AS SELECT NULL AS max_depth;                             -- TODO

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('q1', (SELECT group_concat(name || depth) FROM q1) IS 'Computers1,Phones1,Laptops2,Gaming3');
INSERT INTO t VALUES ('q2', (SELECT path FROM q2) IS 'Electronics / Computers / Laptops / Gaming');
INSERT INTO t VALUES ('q3', (SELECT squares FROM q3) IS '1,4,9,16,25,36,49,64,81,100');
INSERT INTO t VALUES ('q4', (SELECT max_depth FROM q4) IS 3);
SELECT 'PASS ' || name FROM t;
```

<details><summary>Solution</summary>

```sql file=solution.sql
CREATE TABLE cat (id INTEGER PRIMARY KEY, name TEXT, parent_id INTEGER);
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
    SELECT c.id, c.parent_id, c.name || ' / ' || u.path FROM cat c JOIN up u ON c.id = u.parent_id
  )
  SELECT path FROM up WHERE parent_id IS NULL;
CREATE VIEW q3 AS
  WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 10)
  SELECT group_concat(i * i) AS squares FROM n;
CREATE VIEW q4 AS
  WITH RECURSIVE d(id, depth) AS (
    SELECT id, 0 FROM cat WHERE parent_id IS NULL
    UNION ALL
    SELECT c.id, d.depth + 1 FROM cat c JOIN d ON c.parent_id = d.id
  )
  SELECT max(depth) AS max_depth FROM d;

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('q1', (SELECT group_concat(name || depth) FROM q1) IS 'Computers1,Phones1,Laptops2,Gaming3');
INSERT INTO t VALUES ('q2', (SELECT path FROM q2) IS 'Electronics / Computers / Laptops / Gaming');
INSERT INTO t VALUES ('q3', (SELECT squares FROM q3) IS '1,4,9,16,25,36,49,64,81,100');
INSERT INTO t VALUES ('q4', (SELECT max_depth FROM q4) IS 3);
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [14 — Capstone: bookstore analytics](14-capstone-bookstore.md)
