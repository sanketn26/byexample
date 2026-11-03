# SQL 14 — Capstone: A Bookstore, End to End

Everything in one place: design a schema with constraints, load it through
migrations, enforce rules with triggers, and answer business questions with
joins, aggregates, windows and CTEs. Money is integer cents; foreign keys
are on.

## Example

```sql file=example.sql
PRAGMA foreign_keys = ON;

-- ---------- Migration 1: schema ----------
CREATE TABLE customer (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, country TEXT NOT NULL, joined TEXT NOT NULL
) STRICT;
CREATE TABLE book (
  id INTEGER PRIMARY KEY, title TEXT NOT NULL UNIQUE, genre TEXT NOT NULL,
  price_cents INTEGER NOT NULL CHECK (price_cents > 0), stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0)
) STRICT;
CREATE TABLE orders (
  id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customer(id),
  placed TEXT NOT NULL, status TEXT NOT NULL CHECK (status IN ('open', 'paid', 'shipped', 'cancelled'))
) STRICT;
CREATE TABLE order_line (
  order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  book_id  INTEGER NOT NULL REFERENCES book(id),
  qty INTEGER NOT NULL CHECK (qty > 0),
  unit_price_cents INTEGER NOT NULL,           -- snapshot of the price at sale time
  PRIMARY KEY (order_id, book_id)
) STRICT;
CREATE INDEX order_customer ON orders (customer_id);
CREATE INDEX line_book ON order_line (book_id);

-- ---------- Migration 2: stock control by trigger ----------
CREATE TRIGGER line_takes_stock AFTER INSERT ON order_line
BEGIN
  UPDATE book SET stock = stock - NEW.qty WHERE id = NEW.book_id;   -- CHECK blocks overselling
END;

-- ---------- Seed data ----------
INSERT INTO customer VALUES
  (1, 'Ada', 'UK', '2023-01-10'), (2, 'Bob', 'US', '2023-05-02'),
  (3, 'Cy',  'US', '2024-02-14'), (4, 'Di',  'DE', '2024-03-01');
INSERT INTO book VALUES
  (1, 'Dune', 'scifi', 1200, 10), (2, 'Emma', 'classic', 800, 5),
  (3, 'Hobbit', 'fantasy', 1000, 8), (4, 'Neuromancer', 'scifi', 900, 3);
INSERT INTO orders VALUES
  (1, 1, '2024-01-05', 'shipped'), (2, 1, '2024-02-11', 'shipped'),
  (3, 2, '2024-02-20', 'paid'),    (4, 3, '2024-03-03', 'shipped'),
  (5, 2, '2024-03-15', 'cancelled'), (6, 4, '2024-03-20', 'open');
INSERT INTO order_line VALUES
  (1, 1, 1, 1200), (1, 2, 2, 800),  (2, 3, 1, 1000), (3, 1, 2, 1200),
  (4, 4, 1, 900),  (4, 3, 1, 1000), (5, 1, 5, 1200), (6, 2, 1, 800);

-- Overselling is rejected by the CHECK on stock (the trigger fires, the update fails)
-- expect-error
INSERT INTO order_line VALUES (6, 4, 99, 900);

.headers on
-- ---------- Questions ----------
-- Q1. Revenue by genre (cancelled orders do not count), best first
SELECT b.genre, sum(l.qty * l.unit_price_cents) / 100.0 AS revenue
FROM order_line l JOIN orders o ON o.id = l.order_id JOIN book b ON b.id = l.book_id
WHERE o.status <> 'cancelled' GROUP BY b.genre ORDER BY revenue DESC, b.genre;

-- Q2. Customers by lifetime spend, with rank, and their share of all revenue
WITH spend AS (
  SELECT c.name, c.country, coalesce(sum(l.qty * l.unit_price_cents), 0) AS cents
  FROM customer c
  LEFT JOIN orders o ON o.customer_id = c.id AND o.status <> 'cancelled'
  LEFT JOIN order_line l ON l.order_id = o.id
  GROUP BY c.id
)
SELECT name, cents / 100.0 AS spend,
       rank() OVER (ORDER BY cents DESC) AS place,
       round(100.0 * cents / sum(cents) OVER (), 1) AS pct
FROM spend ORDER BY place, name;

-- Q3. Best-selling book per country (top 1 per group)
WITH sold AS (
  SELECT c.country, b.title, sum(l.qty) AS units
  FROM order_line l JOIN orders o ON o.id = l.order_id AND o.status <> 'cancelled'
  JOIN customer c ON c.id = o.customer_id JOIN book b ON b.id = l.book_id
  GROUP BY c.country, b.id
), ranked AS (
  SELECT *, row_number() OVER (PARTITION BY country ORDER BY units DESC, title) AS rn FROM sold
)
SELECT country, title, units FROM ranked WHERE rn = 1 ORDER BY country;

-- Q4. Month-over-month revenue change
WITH monthly AS (
  SELECT substr(o.placed, 1, 7) AS month, sum(l.qty * l.unit_price_cents) AS cents
  FROM orders o JOIN order_line l ON l.order_id = o.id
  WHERE o.status <> 'cancelled' GROUP BY month
)
SELECT month, cents, cents - lag(cents) OVER (ORDER BY month) AS change FROM monthly ORDER BY month;

-- Q5. Customers who never bought sci-fi (anti-join with NOT EXISTS)
SELECT name FROM customer c WHERE NOT EXISTS (
  SELECT 1 FROM orders o JOIN order_line l ON l.order_id = o.id JOIN book b ON b.id = l.book_id
  WHERE o.customer_id = c.id AND b.genre = 'scifi' AND o.status <> 'cancelled'
) ORDER BY name;

-- Q6. Books that need restocking: low stock relative to the last 90 days of sales
SELECT b.title, b.stock, coalesce(sum(l.qty), 0) AS sold_recent
FROM book b
LEFT JOIN order_line l ON l.book_id = b.id
LEFT JOIN orders o ON o.id = l.order_id AND o.status <> 'cancelled' AND o.placed >= date('2024-03-31', '-90 days')
GROUP BY b.id HAVING b.stock <= 5 ORDER BY b.stock, b.title;

-- Q7. Integrity check: ledger of prices versus the current catalogue
SELECT count(*) AS lines_not_at_list_price
FROM order_line l JOIN book b ON b.id = l.book_id WHERE l.unit_price_cents <> b.price_cents;

-- Q8. Cancel an order and restore stock in one transaction
BEGIN;
UPDATE orders SET status = 'cancelled' WHERE id = 6 AND status = 'open';
UPDATE book SET stock = stock + (SELECT qty FROM order_line WHERE order_id = 6 AND book_id = book.id)
WHERE id IN (SELECT book_id FROM order_line WHERE order_id = 6);
COMMIT;
SELECT title, stock FROM book WHERE id = 2;
```

```text output
Error: CHECK constraint failed: stock >= 0
genre|revenue
scifi|45.0
classic|24.0
fantasy|20.0
name|spend|place|pct
Ada|38.0|1|42.7
Bob|24.0|2|27.0
Cy|19.0|3|21.3
Di|8.0|4|9.0
country|title|units
DE|Emma|1
UK|Emma|2
US|Dune|2
month|cents|change
2024-01|2800|
2024-02|3400|600
2024-03|2700|-700
name
Di
title|stock|sold_recent
Dune|2|8
Emma|2|3
Neuromancer|2|1
lines_not_at_list_price
0
title|stock
Emma|3
```

## Details that bite

- **Snapshot prices** into the order line (`unit_price_cents`). Join back to
  `book.price_cents` and old orders change when the catalogue does.
- Decide what "revenue" means once (here: not cancelled) and put it in a
  view so every report agrees.
- `LEFT JOIN` + a filter on the right table belongs in `ON`, or customers
  with no orders vanish (lesson 04).
- Constraints do the policing: `CHECK (stock >= 0)` plus one trigger
  prevents overselling under any client, with no application code.
- Migrations are numbered scripts that only move forward. Record which
  have run (a `schema_migrations` table), never edit one already applied.
- Reports that join many tables belong in views or CTEs with names that
  say what they mean; copy-pasted subqueries drift apart.
- Tests for SQL are queries with known answers on a small, fixed dataset,
  exactly like the checks in the exercises.

## Exercises

```sql file=exercise.sql
PRAGMA foreign_keys = ON;
CREATE TABLE customer (id INTEGER PRIMARY KEY, name TEXT NOT NULL, country TEXT NOT NULL);
CREATE TABLE book (id INTEGER PRIMARY KEY, title TEXT NOT NULL, genre TEXT NOT NULL, price_cents INTEGER NOT NULL);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customer(id),
                     placed TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE order_line (order_id INTEGER REFERENCES orders(id), book_id INTEGER REFERENCES book(id),
                         qty INTEGER NOT NULL, unit_price_cents INTEGER NOT NULL, PRIMARY KEY (order_id, book_id));
INSERT INTO customer VALUES (1, 'Ada', 'UK'), (2, 'Bob', 'US'), (3, 'Cy', 'US');
INSERT INTO book VALUES (1, 'Dune', 'scifi', 1200), (2, 'Emma', 'classic', 800), (3, 'Hobbit', 'fantasy', 1000);
INSERT INTO orders VALUES (1, 1, '2024-01-05', 'shipped'), (2, 2, '2024-01-20', 'shipped'),
                          (3, 2, '2024-02-02', 'cancelled'), (4, 3, '2024-02-10', 'paid');
INSERT INTO order_line VALUES (1, 1, 2, 1200), (1, 2, 1, 800), (2, 3, 3, 1000),
                              (3, 1, 9, 1200), (4, 2, 4, 800);

-- Define the view revenue_orders: one row per NON-cancelled order with
--   columns order_id, customer, total_cents (sum of qty * unit_price_cents).
-- TODO: CREATE VIEW revenue_orders ...
CREATE VIEW revenue_orders AS SELECT NULL AS order_id, NULL AS customer, NULL AS total_cents WHERE 0;

-- q1: revenue (in cents) per country over revenue_orders, highest first.
--     Columns: country, cents.
CREATE VIEW q1 AS SELECT NULL AS country, NULL AS cents WHERE 0;        -- TODO

-- q2: customers who have NO non-cancelled orders. Column: name.
CREATE VIEW q2 AS SELECT NULL AS name WHERE 0;                          -- TODO

-- q3: each customer's FIRST order date ('first_order'), NULL if none, by name.
--     Columns: name, first_order.
CREATE VIEW q3 AS SELECT NULL AS name, NULL AS first_order WHERE 0;     -- TODO

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('view', (SELECT group_concat(order_id || ':' || total_cents) FROM (SELECT * FROM revenue_orders ORDER BY order_id)) IS '1:3200,2:3000,4:3200');
INSERT INTO t VALUES ('q1', (SELECT group_concat(country || '=' || cents) FROM q1) IS 'US=6200,UK=3200');
INSERT INTO t VALUES ('q2', (SELECT count(*) FROM q2) IS 0);
INSERT INTO t VALUES ('q3', (SELECT group_concat(name || '@' || first_order) FROM q3) IS 'Ada@2024-01-05,Bob@2024-01-20,Cy@2024-02-10');
SELECT 'PASS ' || name FROM t;
```

<details><summary>Solution</summary>

```sql file=solution.sql
PRAGMA foreign_keys = ON;
CREATE TABLE customer (id INTEGER PRIMARY KEY, name TEXT NOT NULL, country TEXT NOT NULL);
CREATE TABLE book (id INTEGER PRIMARY KEY, title TEXT NOT NULL, genre TEXT NOT NULL, price_cents INTEGER NOT NULL);
CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customer(id),
                     placed TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE order_line (order_id INTEGER REFERENCES orders(id), book_id INTEGER REFERENCES book(id),
                         qty INTEGER NOT NULL, unit_price_cents INTEGER NOT NULL, PRIMARY KEY (order_id, book_id));
INSERT INTO customer VALUES (1, 'Ada', 'UK'), (2, 'Bob', 'US'), (3, 'Cy', 'US');
INSERT INTO book VALUES (1, 'Dune', 'scifi', 1200), (2, 'Emma', 'classic', 800), (3, 'Hobbit', 'fantasy', 1000);
INSERT INTO orders VALUES (1, 1, '2024-01-05', 'shipped'), (2, 2, '2024-01-20', 'shipped'),
                          (3, 2, '2024-02-02', 'cancelled'), (4, 3, '2024-02-10', 'paid');
INSERT INTO order_line VALUES (1, 1, 2, 1200), (1, 2, 1, 800), (2, 3, 3, 1000),
                              (3, 1, 9, 1200), (4, 2, 4, 800);

CREATE VIEW revenue_orders AS
  SELECT o.id AS order_id, c.name AS customer, sum(l.qty * l.unit_price_cents) AS total_cents
  FROM orders o JOIN customer c ON c.id = o.customer_id JOIN order_line l ON l.order_id = o.id
  WHERE o.status <> 'cancelled' GROUP BY o.id;

CREATE VIEW q1 AS
  SELECT c.country, sum(r.total_cents) AS cents
  FROM revenue_orders r JOIN customer c ON c.name = r.customer
  GROUP BY c.country ORDER BY cents DESC;
CREATE VIEW q2 AS
  SELECT name FROM customer c WHERE NOT EXISTS (
    SELECT 1 FROM orders o WHERE o.customer_id = c.id AND o.status <> 'cancelled')
  ORDER BY name;
CREATE VIEW q3 AS
  SELECT c.name, min(o.placed) AS first_order
  FROM customer c LEFT JOIN orders o ON o.customer_id = c.id
  GROUP BY c.id ORDER BY c.name;

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('view', (SELECT group_concat(order_id || ':' || total_cents) FROM (SELECT * FROM revenue_orders ORDER BY order_id)) IS '1:3200,2:3000,4:3200');
INSERT INTO t VALUES ('q1', (SELECT group_concat(country || '=' || cents) FROM q1) IS 'US=6200,UK=3200');
INSERT INTO t VALUES ('q2', (SELECT count(*) FROM q2) IS 0);
INSERT INTO t VALUES ('q3', (SELECT group_concat(name || '@' || first_order) FROM q3) IS 'Ada@2024-01-05,Bob@2024-01-20,Cy@2024-02-10');
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [15 — Dialects: SQLite, PostgreSQL and MySQL](15-dialects.md)
