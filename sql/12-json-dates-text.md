# SQL 12 — JSON, Dates and Text

Real data is semi-structured and full of timestamps. SQLite (like
PostgreSQL and MySQL) can query JSON documents, do date arithmetic, and
process text, but each database spells these differently. The ideas
carry over; the function names do not.

## Example

```sql file=example.sql
.headers on
-- ============ JSON ============
CREATE TABLE event (id INTEGER PRIMARY KEY, payload TEXT);   -- JSON stored as text
INSERT INTO event (payload) VALUES
  ('{"user":"ada","action":"login","meta":{"ip":"10.0.0.1","tags":["a","b"]}}'),
  ('{"user":"bob","action":"buy","amount":25.5,"meta":{"ip":"10.0.0.2","tags":[]}}'),
  ('{"user":"ada","action":"buy","amount":10,"meta":{"ip":"10.0.0.1","tags":["c"]}}');

SELECT json_valid(payload) AS valid FROM event LIMIT 1;

-- -> returns JSON, ->> returns an SQL value; paths start with $
SELECT id, payload ->> '$.user' AS user, payload ->> '$.meta.ip' AS ip,
       payload -> '$.meta.tags' AS tags
FROM event ORDER BY id;

-- Filter and aggregate on JSON fields
SELECT payload ->> '$.user' AS user, sum(payload ->> '$.amount') AS spent
FROM event WHERE payload ->> '$.action' = 'buy' GROUP BY user ORDER BY user;

-- Expand an array into rows with json_each
SELECT e.id, j.value AS tag
FROM event e, json_each(e.payload, '$.meta.tags') j ORDER BY e.id, j.key;

-- Build JSON from rows
SELECT json_object('user', payload ->> '$.user', 'n', count(*)) AS doc
FROM event GROUP BY payload ->> '$.user' ORDER BY 1;
SELECT json_group_array(payload ->> '$.user') AS users FROM event;

-- Modify JSON
SELECT json_set('{"a":1}', '$.b', 2) AS added, json_remove('{"a":1,"b":2}', '$.a') AS removed;

-- Index a JSON field with an expression index
CREATE INDEX event_user ON event (payload ->> '$.user');

-- ============ DATES ============
-- SQLite stores dates as text ('YYYY-MM-DD HH:MM:SS'), reals or integers.
.headers off
SELECT date('2024-03-15'), time('2024-03-15 13:45:10'), datetime('2024-03-15 13:45:10');
SELECT date('2024-01-31', '+1 month'), date('2024-03-15', '-7 days'),
       date('2024-03-15', 'start of month', '+1 month', '-1 day') AS month_end;
SELECT strftime('%Y', '2024-03-15') AS year, strftime('%m', '2024-03-15') AS month,
       strftime('%w', '2024-03-15') AS weekday, strftime('%j', '2024-03-15') AS day_of_year;
SELECT julianday('2024-03-15') - julianday('2024-01-01') AS days_between;
SELECT unixepoch('2024-01-01 00:00:00'), datetime(1704067200, 'unixepoch');

-- Group by month, and find "last 7 days" relative to a fixed "now"
CREATE TABLE login (id INTEGER PRIMARY KEY, at TEXT);
INSERT INTO login (at) VALUES ('2024-03-01'), ('2024-03-10'), ('2024-03-14'), ('2024-04-02');
SELECT strftime('%Y-%m', at) AS month, count(*) AS logins FROM login GROUP BY month ORDER BY month;
SELECT count(*) AS last7 FROM login WHERE at >= date('2024-03-15', '-7 days') AND at <= '2024-03-15';

-- ============ TEXT ============
SELECT substr('abcdef', 2, 3), instr('hello world', 'o'), replace('a-b-c', '-', '/'),
       trim('  pad  ') || '|', ltrim('xxabc', 'x'), lower('ÄB'), upper('ab'), length('héllo');
SELECT printf('%05d|%-6s|%.2f|%x', 42, 'ab', 3.14159, 255);
SELECT 'apple' < 'banana', 'a' = 'A', 'a' = 'A' COLLATE NOCASE, 'abc' GLOB 'a*', 'abc' LIKE 'A%';

-- Split a comma list into rows with a recursive CTE (lesson 13 explains how)
WITH RECURSIVE parts(word, rest) AS (
  SELECT '', 'red,green,blue,'
  UNION ALL
  SELECT substr(rest, 1, instr(rest, ',') - 1), substr(rest, instr(rest, ',') + 1)
  FROM parts WHERE rest <> ''
) SELECT word FROM parts WHERE word <> '';
```

```text output
valid
1
id|user|ip|tags
1|ada|10.0.0.1|["a","b"]
2|bob|10.0.0.2|[]
3|ada|10.0.0.1|["c"]
user|spent
ada|10
bob|25.5
id|tag
1|a
1|b
3|c
doc
{"user":"ada","n":2}
{"user":"bob","n":1}
users
["ada","bob","ada"]
added|removed
{"a":1,"b":2}|{"b":2}
2024-03-15|13:45:10|2024-03-15 13:45:10
2024-03-02|2024-03-08|2024-03-31
2024|03|5|075
74.0
1704067200|2024-01-01 00:00:00
2024-03|3
2024-04|1
2
bcd|5|a/b/c|pad||abc|Äb|AB|5
00042|ab    |3.14|ff
1|0|1|1|1
red
green
blue
```

## Details that bite

- **Dates are the biggest portability trap.** SQLite: text +
  `date()`/`strftime()`. PostgreSQL: real `date`, `timestamptz`, `interval`,
  `date_trunc`, `+ interval '1 month'`. MySQL: `DATE_ADD`, `DATE_FORMAT`.
  Store UTC, convert at the edge, and always keep the time zone explicit.
- ISO-8601 strings (`'2024-03-15'`) sort and compare correctly as text:
  that is why `at >= '2024-03-01'` works. Other formats (`03/15/2024`) do not.
- `date('2024-01-31', '+1 month')` is `2024-03-02` (it overflows). Month
  arithmetic on month ends needs care in every database.
- JSON in SQLite is **text** plus functions. PostgreSQL has `jsonb`
  (binary, indexable with GIN); MySQL has `JSON`. Use JSON for genuinely
  schemaless parts, and real columns for things you filter, join and
  constrain on.
- `->` returns JSON (strings keep quotes); `->>` returns a plain SQL value.
  Compare with `->>`.
- A missing JSON path gives NULL, not an error, so typos hide.
- Text comparison and sorting follow a **collation**. `'a' = 'A'` is false
  by default in SQLite, `COLLATE NOCASE` fixes ASCII only. PostgreSQL's
  behaviour depends on the database locale; MySQL's default is
  case-insensitive. Test with your own data.
- `lower`/`upper` in SQLite only fold ASCII unless ICU is loaded.
- Do not build SQL strings by concatenating user text. Use bound
  parameters (`?` or `:name`) in your driver. That is how SQL injection
  is prevented.

## Exercises

```sql file=exercise.sql
CREATE TABLE order_doc (id INTEGER PRIMARY KEY, doc TEXT);
INSERT INTO order_doc (doc) VALUES
  ('{"customer":"ada","placed":"2024-03-02","items":[{"sku":"A","qty":2,"price":5},{"sku":"B","qty":1,"price":20}]}'),
  ('{"customer":"bob","placed":"2024-03-20","items":[{"sku":"A","qty":5,"price":5}]}'),
  ('{"customer":"ada","placed":"2024-04-01","items":[{"sku":"C","qty":3,"price":4}]}');

-- q1: each order's total (sum of qty * price over its items).
--     Columns: id, total; ordered by id. Use json_each.
CREATE VIEW q1 AS SELECT NULL AS id, NULL AS total WHERE 0;             -- TODO

-- q2: total spent per customer. Columns: customer, spent; by customer.
CREATE VIEW q2 AS SELECT NULL AS customer, NULL AS spent WHERE 0;       -- TODO

-- q3: number of orders placed per month ('2024-03' style). Columns:
--     month, orders; by month.
CREATE VIEW q3 AS SELECT NULL AS month, NULL AS orders WHERE 0;         -- TODO

-- q4: the date 30 days after each order was placed. Columns: id, due; by id.
CREATE VIEW q4 AS SELECT NULL AS id, NULL AS due WHERE 0;               -- TODO

-- q5: the distinct SKUs ordered, as one comma-separated, sorted string.
--     Column: skus.
CREATE VIEW q5 AS SELECT NULL AS skus;                                  -- TODO

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('q1', (SELECT group_concat(id || ':' || total) FROM q1) IS '1:30,2:25,3:12');
INSERT INTO t VALUES ('q2', (SELECT group_concat(customer || '=' || spent) FROM q2) IS 'ada=42,bob=25');
INSERT INTO t VALUES ('q3', (SELECT group_concat(month || '=' || orders) FROM q3) IS '2024-03=2,2024-04=1');
INSERT INTO t VALUES ('q4', (SELECT group_concat(id || ':' || due) FROM q4) IS '1:2024-04-01,2:2024-04-19,3:2024-05-01');
INSERT INTO t VALUES ('q5', (SELECT skus FROM q5) IS 'A,B,C');
SELECT 'PASS ' || name FROM t;
```

<details><summary>Solution</summary>

```sql file=solution.sql
CREATE TABLE order_doc (id INTEGER PRIMARY KEY, doc TEXT);
INSERT INTO order_doc (doc) VALUES
  ('{"customer":"ada","placed":"2024-03-02","items":[{"sku":"A","qty":2,"price":5},{"sku":"B","qty":1,"price":20}]}'),
  ('{"customer":"bob","placed":"2024-03-20","items":[{"sku":"A","qty":5,"price":5}]}'),
  ('{"customer":"ada","placed":"2024-04-01","items":[{"sku":"C","qty":3,"price":4}]}');

CREATE VIEW q1 AS
  SELECT o.id, sum(i.value ->> '$.qty' * (i.value ->> '$.price')) AS total
  FROM order_doc o, json_each(o.doc, '$.items') i GROUP BY o.id ORDER BY o.id;
CREATE VIEW q2 AS
  SELECT o.doc ->> '$.customer' AS customer,
         sum(i.value ->> '$.qty' * (i.value ->> '$.price')) AS spent
  FROM order_doc o, json_each(o.doc, '$.items') i GROUP BY customer ORDER BY customer;
CREATE VIEW q3 AS
  SELECT strftime('%Y-%m', doc ->> '$.placed') AS month, count(*) AS orders
  FROM order_doc GROUP BY month ORDER BY month;
CREATE VIEW q4 AS
  SELECT id, date(doc ->> '$.placed', '+30 days') AS due FROM order_doc ORDER BY id;
CREATE VIEW q5 AS
  SELECT group_concat(sku) AS skus FROM (
    SELECT DISTINCT i.value ->> '$.sku' AS sku
    FROM order_doc o, json_each(o.doc, '$.items') i ORDER BY sku);

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('q1', (SELECT group_concat(id || ':' || total) FROM q1) IS '1:30,2:25,3:12');
INSERT INTO t VALUES ('q2', (SELECT group_concat(customer || '=' || spent) FROM q2) IS 'ada=42,bob=25');
INSERT INTO t VALUES ('q3', (SELECT group_concat(month || '=' || orders) FROM q3) IS '2024-03=2,2024-04=1');
INSERT INTO t VALUES ('q4', (SELECT group_concat(id || ':' || due) FROM q4) IS '1:2024-04-01,2:2024-04-19,3:2024-05-01');
INSERT INTO t VALUES ('q5', (SELECT skus FROM q5) IS 'A,B,C');
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [13 — Recursive queries](13-recursive-ctes.md)
