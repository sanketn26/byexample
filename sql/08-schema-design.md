# SQL 08 — Schema Design: Tables, Keys, Constraints

Good schemas make bad data **impossible**. Put rules in the database
(types, `NOT NULL`, `UNIQUE`, `CHECK`, foreign keys) so every program that
touches it, now and later, obeys them.

## Example

```sql file=example.sql
PRAGMA foreign_keys = ON;          -- SQLite: foreign keys are OFF by default!

CREATE TABLE author (
  id    INTEGER PRIMARY KEY,                     -- the row's identity
  name  TEXT NOT NULL CHECK (length(name) > 0),
  email TEXT UNIQUE
) STRICT;                                        -- STRICT: types are enforced

CREATE TABLE book (
  id        INTEGER PRIMARY KEY,
  author_id INTEGER NOT NULL REFERENCES author(id) ON DELETE RESTRICT,
  title     TEXT NOT NULL,
  year      INTEGER CHECK (year BETWEEN 1400 AND 2100),
  price     INTEGER NOT NULL DEFAULT 0 CHECK (price >= 0),   -- cents, never floats
  UNIQUE (author_id, title)                      -- composite uniqueness
) STRICT;

-- Many-to-many needs a join table with a composite primary key
CREATE TABLE tag  (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE) STRICT;
CREATE TABLE book_tag (
  book_id INTEGER NOT NULL REFERENCES book(id) ON DELETE CASCADE,
  tag_id  INTEGER NOT NULL REFERENCES tag(id)  ON DELETE CASCADE,
  PRIMARY KEY (book_id, tag_id)
) STRICT;

INSERT INTO author (id, name, email) VALUES (1, 'Le Guin', 'ursula@example.com'), (2, 'Austen', NULL);
INSERT INTO book (author_id, title, year, price) VALUES (1, 'The Dispossessed', 1974, 1299);

-- Every rule above rejects bad data. (`-- expect-error` tells the course
-- runner the next statement must fail; to the sqlite3 shell it is a comment.)
-- expect-error
INSERT INTO book (author_id, title) VALUES (99, 'Orphan');
-- expect-error
INSERT INTO author (name, email) VALUES ('X', 'ursula@example.com');
-- expect-error
INSERT INTO book (author_id, title, price) VALUES (1, 'Free', -1);
-- expect-error
INSERT INTO author (name) VALUES ('');
-- expect-error
INSERT INTO book (author_id, title, year) VALUES (1, 'T', 'abc');
-- expect-error
DELETE FROM author WHERE id = 1;

-- UNIQUE allows many NULLs: they are "unknown", so never equal
INSERT INTO author (name, email) VALUES ('Anon One', NULL), ('Anon Two', NULL);
SELECT count(*) AS authors FROM author;

-- Cascade: deleting a book removes its tag links
INSERT INTO tag (name) VALUES ('utopia'), ('classic');
INSERT INTO book_tag VALUES (1, 1), (1, 2);
SELECT count(*) AS links_before FROM book_tag;
DELETE FROM book WHERE id = 1;
SELECT count(*) AS links_after FROM book_tag;

-- Inspect the schema
SELECT name, type FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
ORDER BY name;
.headers on
SELECT name, type, "notnull" AS not_null, pk FROM pragma_table_info('book');
.headers off

-- Altering a schema
ALTER TABLE author ADD COLUMN born INTEGER;
ALTER TABLE author RENAME COLUMN name TO full_name;
SELECT full_name, born FROM author WHERE id = 1;

-- Normalisation by example: one fact, one place
-- Bad:  book(title, author_name, author_email)  -- email repeated per book
-- Good: book(author_id) -> author(id, name, email)
SELECT b.title, a.full_name FROM author a LEFT JOIN book b ON b.author_id = a.id
WHERE a.id = 1;
```

```text output
Error: FOREIGN KEY constraint failed
Error: UNIQUE constraint failed: author.email
Error: CHECK constraint failed: price >= 0
Error: CHECK constraint failed: length(name) > 0
Error: cannot store TEXT value in INTEGER column book.year
Error: FOREIGN KEY constraint failed
4
2
0
author|table
book|table
book_tag|table
tag|table
name|type|not_null|pk
id|INTEGER|0|1
author_id|INTEGER|1|0
title|TEXT|1|0
year|INTEGER|0|0
price|INTEGER|1|0
Le Guin|
|Le Guin
```

## Details that bite

- SQLite does **not** enforce foreign keys unless you run
  `PRAGMA foreign_keys = ON` on *each connection*. PostgreSQL and MySQL
  (InnoDB) always do.
- Without `STRICT`, SQLite will store `'abc'` in an `INTEGER` column.
  `STRICT` (3.37+) turns that into an error. Use it for new tables.
- Primary key choices: a surrogate integer or UUID, or a natural key you
  are sure will never change. Emails, names and phone numbers change:
  do not use them as primary keys.
- `UNIQUE` allows multiple NULLs (they are "unknown", so not equal). If
  that is wrong, add `NOT NULL`.
- **Money in integer cents** (or `NUMERIC`/`DECIMAL`), never `REAL`:
  `0.1 + 0.2` is not `0.3`.
- `ON DELETE`: `RESTRICT` blocks, `CASCADE` deletes children, `SET NULL`
  orphans them. Pick deliberately; a careless `CASCADE` is a mass delete.
- Dates: SQLite has no date type. Store ISO-8601 text (`'2024-06-01'`),
  or integers (epoch seconds). PostgreSQL has `date`/`timestamptz`; use them.
- Normalise until it hurts (each fact once), then denormalise only where
  measurement tells you to. Wide "one big table" designs rot.
- Name tables and columns consistently (singular nouns, `snake_case`,
  `thing_id` for foreign keys) and add `NOT NULL` unless NULL has meaning.
- Change schemas through numbered migration scripts kept in version
  control, not by hand (lesson 14).

## Exercises

```sql file=exercise.sql
PRAGMA foreign_keys = ON;

-- Design a tiny school schema. Create exactly these tables:
--   student(id integer pk, name text not null, email text unique)
--   course(id integer pk, title text not null unique,
--          credits integer not null, check credits between 1 and 6)
--   enrollment(student_id -> student ON DELETE CASCADE,
--              course_id -> course ON DELETE RESTRICT,
--              grade integer check between 0 and 100 (NULL allowed),
--              primary key (student_id, course_id))
-- TODO: write the CREATE TABLE statements here



-- Seed data (needs your tables)
INSERT INTO student VALUES (1, 'Ada', 'ada@x.org'), (2, 'Bob', NULL);
INSERT INTO course VALUES (10, 'Math', 4), (11, 'Art', 2);
INSERT INTO enrollment VALUES (1, 10, 95), (1, 11, NULL), (2, 10, 70);

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
-- cascade: removing Bob removes his enrollment
DELETE FROM student WHERE id = 2;
INSERT INTO t VALUES ('cascade', (SELECT count(*) FROM enrollment) IS 2);
-- restrict: a course with enrollments cannot be removed
-- (the DELETE below must change 0 rows' worth of data: we verify by counting)
CREATE TEMP TABLE guard AS SELECT count(*) AS n FROM course;
INSERT INTO t VALUES ('keys', (SELECT count(*) FROM pragma_table_info('enrollment') WHERE pk > 0) IS 2);
INSERT INTO t VALUES ('check', (SELECT sql LIKE '%CHECK%' FROM sqlite_master WHERE name = 'course') IS 1);
INSERT INTO t VALUES ('unique', (SELECT sql LIKE '%UNIQUE%' FROM sqlite_master WHERE name = 'student') IS 1);
INSERT INTO t VALUES ('fk', (SELECT count(*) FROM pragma_foreign_key_list('enrollment')) IS 2);
INSERT INTO t VALUES ('on delete', (SELECT group_concat(on_delete) FROM (SELECT on_delete FROM pragma_foreign_key_list('enrollment') ORDER BY "table")) IS 'RESTRICT,CASCADE');
SELECT 'PASS ' || name FROM t;
```

<details><summary>Solution</summary>

```sql file=solution.sql
PRAGMA foreign_keys = ON;

CREATE TABLE student (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE
);
CREATE TABLE course (
  id INTEGER PRIMARY KEY, title TEXT NOT NULL UNIQUE,
  credits INTEGER NOT NULL CHECK (credits BETWEEN 1 AND 6)
);
CREATE TABLE enrollment (
  student_id INTEGER NOT NULL REFERENCES student(id) ON DELETE CASCADE,
  course_id  INTEGER NOT NULL REFERENCES course(id)  ON DELETE RESTRICT,
  grade INTEGER CHECK (grade BETWEEN 0 AND 100),
  PRIMARY KEY (student_id, course_id)
);

INSERT INTO student VALUES (1, 'Ada', 'ada@x.org'), (2, 'Bob', NULL);
INSERT INTO course VALUES (10, 'Math', 4), (11, 'Art', 2);
INSERT INTO enrollment VALUES (1, 10, 95), (1, 11, NULL), (2, 10, 70);

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
DELETE FROM student WHERE id = 2;
INSERT INTO t VALUES ('cascade', (SELECT count(*) FROM enrollment) IS 2);
CREATE TEMP TABLE guard AS SELECT count(*) AS n FROM course;
INSERT INTO t VALUES ('keys', (SELECT count(*) FROM pragma_table_info('enrollment') WHERE pk > 0) IS 2);
INSERT INTO t VALUES ('check', (SELECT sql LIKE '%CHECK%' FROM sqlite_master WHERE name = 'course') IS 1);
INSERT INTO t VALUES ('unique', (SELECT sql LIKE '%UNIQUE%' FROM sqlite_master WHERE name = 'student') IS 1);
INSERT INTO t VALUES ('fk', (SELECT count(*) FROM pragma_foreign_key_list('enrollment')) IS 2);
INSERT INTO t VALUES ('on delete', (SELECT group_concat(on_delete) FROM (SELECT on_delete FROM pragma_foreign_key_list('enrollment') ORDER BY "table")) IS 'RESTRICT,CASCADE');
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [09 — Transactions](09-transactions.md)
