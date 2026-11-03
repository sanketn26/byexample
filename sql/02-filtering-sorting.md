# SQL 02 — Filtering, Sorting and Paging

`SELECT` has a fixed shape: pick **columns**, from a **table**, keep rows
that match a **predicate**, put them in an **order**, take a **page**.
Learn the order the database *thinks* in, not the order you write:

`FROM` → `WHERE` → `GROUP BY` → `HAVING` → `SELECT` → `ORDER BY` → `LIMIT`

## Example

```sql file=example.sql
CREATE TABLE book (
  id INTEGER PRIMARY KEY, title TEXT, author TEXT, year INTEGER,
  price REAL, genre TEXT
);
INSERT INTO book VALUES
  (1, 'Dune',                  'Herbert',  1965, 9.99,  'scifi'),
  (2, 'Neuromancer',           'Gibson',   1984, 7.50,  'scifi'),
  (3, 'The Hobbit',            'Tolkien',  1937, 8.25,  'fantasy'),
  (4, 'Emma',                  'Austen',   1815, 5.00,  'classic'),
  (5, 'Persuasion',            'Austen',   1817, NULL,  'classic'),
  (6, 'The Left Hand of Darkness', 'Le Guin', 1969, 8.00, 'scifi'),
  (7, 'Piranesi',              'Clarke',   2020, 12.00, NULL);

-- WHERE with comparisons, AND / OR / NOT (use parentheses!)
SELECT title FROM book WHERE genre = 'scifi' AND year < 1980;
SELECT title FROM book WHERE (genre = 'scifi' OR genre = 'fantasy') AND price < 9;

-- IN, BETWEEN (inclusive), LIKE (% any run, _ one char)
SELECT title FROM book WHERE author IN ('Austen', 'Clarke');
SELECT title FROM book WHERE year BETWEEN 1960 AND 1990;
SELECT title FROM book WHERE title LIKE 'The %';
SELECT title FROM book WHERE title LIKE '_mma';

-- NULL: = never matches NULL; IS NULL does
SELECT title FROM book WHERE price IS NULL;
SELECT title FROM book WHERE genre <> 'scifi';              -- row 7 is NOT here
SELECT title FROM book WHERE genre <> 'scifi' OR genre IS NULL;

-- ORDER BY: ASC (default) / DESC, several keys, expressions, NULL position
SELECT title, price FROM book ORDER BY price DESC;
SELECT title, year FROM book ORDER BY author, year DESC;
SELECT title FROM book ORDER BY length(title), title;

-- LIMIT / OFFSET for paging (always with a stable ORDER BY)
SELECT id, title FROM book ORDER BY id LIMIT 3;
SELECT id, title FROM book ORDER BY id LIMIT 3 OFFSET 3;

-- DISTINCT removes duplicate result rows
SELECT DISTINCT author FROM book ORDER BY author;
SELECT DISTINCT genre FROM book ORDER BY genre;

-- Computed columns and aliases, which ORDER BY can use but WHERE cannot
SELECT title, round(price * 1.2, 2) AS with_tax
FROM book WHERE price IS NOT NULL ORDER BY with_tax DESC LIMIT 2;

-- Keyset paging: faster than a big OFFSET
SELECT id, title FROM book WHERE id > 3 ORDER BY id LIMIT 2;

-- Compare against several columns at once
SELECT title FROM book WHERE (author, genre) = ('Austen', 'classic') ORDER BY year;
```

```text output
Dune
The Left Hand of Darkness
Neuromancer
The Hobbit
The Left Hand of Darkness
Emma
Persuasion
Piranesi
Dune
Neuromancer
The Left Hand of Darkness
The Hobbit
The Left Hand of Darkness
Emma
Persuasion
The Hobbit
Emma
Persuasion
The Hobbit
Emma
Persuasion
Piranesi
Piranesi|12.0
Dune|9.99
The Hobbit|8.25
The Left Hand of Darkness|8.0
Neuromancer|7.5
Emma|5.0
Persuasion|
Persuasion|1817
Emma|1815
Piranesi|2020
Neuromancer|1984
Dune|1965
The Left Hand of Darkness|1969
The Hobbit|1937
Dune
Emma
Piranesi
Persuasion
The Hobbit
Neuromancer
The Left Hand of Darkness
1|Dune
2|Neuromancer
3|The Hobbit
4|Emma
5|Persuasion
6|The Left Hand of Darkness
Austen
Clarke
Gibson
Herbert
Le Guin
Tolkien

classic
fantasy
scifi
Piranesi|14.4
Dune|11.99
4|Emma
5|Persuasion
Emma
Persuasion
```

## Details that bite

- `AND` binds tighter than `OR`. `a OR b AND c` means `a OR (b AND c)`.
  Parenthesise.
- `NOT IN (1, NULL)` is never true: `x <> NULL` is unknown. Prefer
  `NOT EXISTS` when the list may contain NULL (lesson 05).
- Without `ORDER BY`, row order is **unspecified**. It may look sorted
  today and change after an index or an upgrade. Always sort what you page.
- `OFFSET n` still reads and discards `n` rows: deep pages get slow. Use
  keyset paging (`WHERE id > :last_id ... LIMIT n`).
- `LIKE` is case-insensitive for ASCII in SQLite and MySQL, case-sensitive
  in PostgreSQL (use `ILIKE`). A leading `%` cannot use an index.
- Where NULLs sort differs: SQLite and MySQL put them first in `ASC`;
  PostgreSQL puts them last. `ORDER BY price IS NULL, price` is portable.
- You cannot use a `SELECT` alias in `WHERE` (it runs earlier), but you
  can in `ORDER BY`.

## Exercises

```sql file=exercise.sql
CREATE TABLE book (
  id INTEGER PRIMARY KEY, title TEXT, author TEXT, year INTEGER,
  price REAL, genre TEXT
);
INSERT INTO book VALUES
  (1, 'Dune',                  'Herbert',  1965, 9.99,  'scifi'),
  (2, 'Neuromancer',           'Gibson',   1984, 7.50,  'scifi'),
  (3, 'The Hobbit',            'Tolkien',  1937, 8.25,  'fantasy'),
  (4, 'Emma',                  'Austen',   1815, 5.00,  'classic'),
  (5, 'Persuasion',            'Austen',   1817, NULL,  'classic'),
  (6, 'The Left Hand of Darkness', 'Le Guin', 1969, 8.00, 'scifi'),
  (7, 'Piranesi',              'Clarke',   2020, 12.00, NULL);

-- q1: titles published before 1950, oldest first. Column: title.
CREATE VIEW q1 AS SELECT NULL AS title WHERE 0;                 -- TODO

-- q2: titles whose genre is not 'scifi' INCLUDING books with no genre,
--     ordered by id. Column: title.
CREATE VIEW q2 AS SELECT NULL AS title WHERE 0;                 -- TODO

-- q3: the two most expensive books that have a price, most expensive first.
--     Column: title.
CREATE VIEW q3 AS SELECT NULL AS title WHERE 0;                 -- TODO

-- q4: titles that start with 'P' or contain 'Hand', ordered by title.
CREATE VIEW q4 AS SELECT NULL AS title WHERE 0;                 -- TODO

-- q5: books on "page 2" when ordered by id and the page size is 3
--     (ids 4, 5, 6). Column: id.
CREATE VIEW q5 AS SELECT NULL AS id WHERE 0;                    -- TODO

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('q1', (SELECT group_concat(title, '|') FROM q1) IS 'Emma|Persuasion|The Hobbit');
INSERT INTO t VALUES ('q2', (SELECT group_concat(title, '|') FROM q2) IS 'The Hobbit|Emma|Persuasion|Piranesi');
INSERT INTO t VALUES ('q3', (SELECT group_concat(title, '|') FROM q3) IS 'Piranesi|Dune');
INSERT INTO t VALUES ('q4', (SELECT group_concat(title, '|') FROM q4) IS 'Persuasion|Piranesi|The Left Hand of Darkness');
INSERT INTO t VALUES ('q5', (SELECT group_concat(id, ',') FROM q5) IS '4,5,6');
SELECT 'PASS ' || name FROM t;
```

<details><summary>Solution</summary>

```sql file=solution.sql
CREATE TABLE book (
  id INTEGER PRIMARY KEY, title TEXT, author TEXT, year INTEGER,
  price REAL, genre TEXT
);
INSERT INTO book VALUES
  (1, 'Dune',                  'Herbert',  1965, 9.99,  'scifi'),
  (2, 'Neuromancer',           'Gibson',   1984, 7.50,  'scifi'),
  (3, 'The Hobbit',            'Tolkien',  1937, 8.25,  'fantasy'),
  (4, 'Emma',                  'Austen',   1815, 5.00,  'classic'),
  (5, 'Persuasion',            'Austen',   1817, NULL,  'classic'),
  (6, 'The Left Hand of Darkness', 'Le Guin', 1969, 8.00, 'scifi'),
  (7, 'Piranesi',              'Clarke',   2020, 12.00, NULL);

CREATE VIEW q1 AS SELECT title FROM book WHERE year < 1950 ORDER BY year;
CREATE VIEW q2 AS SELECT title FROM book WHERE genre <> 'scifi' OR genre IS NULL ORDER BY id;
CREATE VIEW q3 AS SELECT title FROM book WHERE price IS NOT NULL ORDER BY price DESC LIMIT 2;
CREATE VIEW q4 AS SELECT title FROM book WHERE title LIKE 'P%' OR title LIKE '%Hand%' ORDER BY title;
CREATE VIEW q5 AS SELECT id FROM book ORDER BY id LIMIT 3 OFFSET 3;

CREATE TEMP TABLE t (name TEXT, ok INTEGER CHECK (ok = 1));
INSERT INTO t VALUES ('q1', (SELECT group_concat(title, '|') FROM q1) IS 'Emma|Persuasion|The Hobbit');
INSERT INTO t VALUES ('q2', (SELECT group_concat(title, '|') FROM q2) IS 'The Hobbit|Emma|Persuasion|Piranesi');
INSERT INTO t VALUES ('q3', (SELECT group_concat(title, '|') FROM q3) IS 'Piranesi|Dune');
INSERT INTO t VALUES ('q4', (SELECT group_concat(title, '|') FROM q4) IS 'Persuasion|Piranesi|The Left Hand of Darkness');
INSERT INTO t VALUES ('q5', (SELECT group_concat(id, ',') FROM q5) IS '4,5,6');
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [03 — Aggregation](03-aggregation.md)
