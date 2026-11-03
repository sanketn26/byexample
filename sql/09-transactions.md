# SQL 09 — Transactions

A **transaction** groups statements so they succeed or fail together
(**atomicity**), leave the data valid (**consistency**), do not see each
other's half-done work (**isolation**), and survive a crash
(**durability**). The classic example is a bank transfer: debit and credit
must both happen, or neither.

## Example

```sql file=example.sql
PRAGMA foreign_keys = ON;
CREATE TABLE account (
  id INTEGER PRIMARY KEY, owner TEXT NOT NULL,
  balance INTEGER NOT NULL CHECK (balance >= 0)
);
CREATE TABLE ledger (id INTEGER PRIMARY KEY, from_id INTEGER, to_id INTEGER, amount INTEGER);
INSERT INTO account VALUES (1, 'ada', 100), (2, 'bob', 50);

.headers on
-- 1. COMMIT makes the changes permanent
BEGIN;
UPDATE account SET balance = balance - 30 WHERE id = 1;
UPDATE account SET balance = balance + 30 WHERE id = 2;
INSERT INTO ledger (from_id, to_id, amount) VALUES (1, 2, 30);
COMMIT;
SELECT owner, balance FROM account ORDER BY id;

-- 2. ROLLBACK undoes everything since BEGIN
BEGIN;
UPDATE account SET balance = 0;
SELECT sum(balance) AS inside_tx FROM account;
ROLLBACK;
SELECT sum(balance) AS after_rollback FROM account;

-- 3. A failed statement does not have to kill the transaction, so check!
--    Here the debit would make ada's balance negative: the CHECK rejects it.
BEGIN;
-- expect-error
UPDATE account SET balance = balance - 500 WHERE id = 1;
-- the credit side must not run alone; the application rolls back
ROLLBACK;
SELECT owner, balance FROM account ORDER BY id;

-- 4. SAVEPOINT: a partial rollback inside a transaction
BEGIN;
INSERT INTO ledger (from_id, to_id, amount) VALUES (1, 2, 1);
SAVEPOINT risky;
INSERT INTO ledger (from_id, to_id, amount) VALUES (1, 2, 999);
ROLLBACK TO risky;                           -- undo only the 999 row
RELEASE risky;
COMMIT;
SELECT amount FROM ledger ORDER BY id;

-- 5. Atomic "check then act": do it in one statement, not read-then-write
UPDATE account SET balance = balance - 60 WHERE id = 1 AND balance >= 60 RETURNING owner, balance;
UPDATE account SET balance = balance - 60 WHERE id = 1 AND balance >= 60 RETURNING owner, balance;
SELECT changes() AS rows_changed;            -- 0 means the guard refused

-- 6. Idempotent writes: a retry must not double-apply
CREATE TABLE payment (key TEXT PRIMARY KEY, amount INTEGER);
INSERT INTO payment VALUES ('order-77', 10) ON CONFLICT (key) DO NOTHING;
INSERT INTO payment VALUES ('order-77', 10) ON CONFLICT (key) DO NOTHING;
SELECT count(*) AS payments FROM payment;

-- 7. Transaction modes in SQLite
--    BEGIN DEFERRED   (default) locks when first read/write happens
--    BEGIN IMMEDIATE  takes the write lock now: no surprise "database is locked"
--    BEGIN EXCLUSIVE  also blocks readers (rarely needed)
BEGIN IMMEDIATE;
UPDATE account SET balance = balance + 1 WHERE id = 2;
COMMIT;
SELECT balance FROM account WHERE id = 2;

-- 8. DDL is transactional in SQLite (and PostgreSQL, not MySQL)
BEGIN;
CREATE TABLE temp_experiment (x INTEGER);
ROLLBACK;
SELECT count(*) AS tables_named_temp_experiment FROM sqlite_master WHERE name = 'temp_experiment';
```

```text output
owner|balance
ada|70
bob|80
inside_tx
0
after_rollback
150
Error: CHECK constraint failed: balance >= 0
owner|balance
ada|70
bob|80
amount
30
1
owner|balance
ada|10
owner|balance
rows_changed
0
payments
1
balance
81
tables_named_temp_experiment
0
```

## Details that bite

- Outside a `BEGIN`, **every statement is its own transaction**
  (autocommit). Ten separate inserts mean ten syncs to disk: wrap bulk
  work in one transaction and it can be 100× faster.
- After an error mid-transaction, you must decide: `ROLLBACK`, or
  continue knowing earlier statements still stand. In PostgreSQL the
  whole transaction is aborted until you roll back or use a savepoint.
- Isolation levels (PostgreSQL/MySQL): `READ COMMITTED` sees newly
  committed rows between statements; `REPEATABLE READ` and `SERIALIZABLE`
  see a stable snapshot. SQLite is effectively serializable: one writer
  at a time.
- **Read-modify-write races**: reading a balance in the app, computing,
  then writing back loses updates when two clients interleave. Do the math
  in the statement (`balance = balance - 60 WHERE balance >= 60`) or lock
  the row (`SELECT ... FOR UPDATE` in PostgreSQL/MySQL).
- Keep transactions **short**. A transaction waiting on a human, an HTTP
  call or a sleep holds locks and blocks everyone else.
- Retries: `database is locked` (SQLite) and serialization failures
  (PostgreSQL `40001`) are normal under contention. Retry the whole
  transaction, and make it idempotent (example 6).
- MySQL silently commits before DDL statements; PostgreSQL and SQLite let
  you roll DDL back, which makes migrations safer.

## Exercises

```sql file=exercise.sql
CREATE TABLE account (
  id INTEGER PRIMARY KEY, owner TEXT NOT NULL,
  balance INTEGER NOT NULL CHECK (balance >= 0)
);
INSERT INTO account VALUES (1, 'ada', 100), (2, 'bob', 50), (3, 'cy', 0);

-- 1. Transfer 40 from ada (1) to cy (3) in ONE transaction.
-- 2. Try to transfer 500 from bob (2) to cy (3) in a transaction: the debit
--    violates the CHECK. (Mark the failing statement with -- expect-error,
--    then ROLLBACK so the credit never happens.)
-- 3. Take 10 from bob (2) with ONE guarded UPDATE that only succeeds if bob
--    has at least 10 (no separate SELECT).
-- TODO: write the statements here



CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('ada',  (SELECT balance FROM account WHERE id = 1) IS 60);
INSERT INTO t VALUES ('cy',   (SELECT balance FROM account WHERE id = 3) IS 40);
INSERT INTO t VALUES ('bob',  (SELECT balance FROM account WHERE id = 2) IS 40);
INSERT INTO t VALUES ('sum',  (SELECT sum(balance) FROM account) IS 140);
INSERT INTO t VALUES ('no open tx', (SELECT 1) IS 1);
SELECT 'PASS ' || name FROM t;
```

<details><summary>Solution</summary>

```sql file=solution.sql
CREATE TABLE account (
  id INTEGER PRIMARY KEY, owner TEXT NOT NULL,
  balance INTEGER NOT NULL CHECK (balance >= 0)
);
INSERT INTO account VALUES (1, 'ada', 100), (2, 'bob', 50), (3, 'cy', 0);

BEGIN;
UPDATE account SET balance = balance - 40 WHERE id = 1;
UPDATE account SET balance = balance + 40 WHERE id = 3;
COMMIT;

BEGIN;
-- expect-error
UPDATE account SET balance = balance - 500 WHERE id = 2;
ROLLBACK;

UPDATE account SET balance = balance - 10 WHERE id = 2 AND balance >= 10;

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('ada',  (SELECT balance FROM account WHERE id = 1) IS 60);
INSERT INTO t VALUES ('cy',   (SELECT balance FROM account WHERE id = 3) IS 40);
INSERT INTO t VALUES ('bob',  (SELECT balance FROM account WHERE id = 2) IS 40);
INSERT INTO t VALUES ('sum',  (SELECT sum(balance) FROM account) IS 140);
INSERT INTO t VALUES ('no open tx', (SELECT 1) IS 1);
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [10 — Indexes and query plans](10-indexes.md)
