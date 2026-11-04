# SQL 02 — Filtering, Sorting and Paging

`SELECT` has a fixed shape: columns, a table, a predicate, an order, a
page. The database thinks in this order, not the order you write:

`FROM` → `WHERE` → `GROUP BY` → `HAVING` → `SELECT` → `ORDER BY` → `LIMIT`

## AND binds tighter than OR

`true OR false AND false` means `true OR (false AND false)`. Parenthesise
mixed `AND` and `OR` or the predicate will keep the wrong rows. These are
booleans, printed `t` and `f`.

```sql file=n01.sql
SELECT true OR false AND false, (true OR false) AND false;
```

```text output
t|f
```

## WHERE keeps rows that match

Both sides of `AND` must hold. `OR` needs parentheses when it is mixed
with another condition. A NULL price fails `price < 9`, so that row drops
out.

```sql file=n02.sql
CREATE TABLE book (
  id INTEGER PRIMARY KEY, title TEXT, author TEXT, year INTEGER,
  price NUMERIC, genre TEXT
);
INSERT INTO book VALUES
  (1, 'Dune',                  'Herbert',  1965, 9.99,  'scifi'),
  (2, 'Neuromancer',           'Gibson',   1984, 7.50,  'scifi'),
  (3, 'The Hobbit',            'Tolkien',  1937, 8.25,  'fantasy'),
  (4, 'Emma',                  'Austen',   1815, 5.00,  'classic'),
  (5, 'Persuasion',            'Austen',   1817, NULL,  'classic'),
  (6, 'The Left Hand of Darkness', 'Le Guin', 1969, 8.00, 'scifi'),
  (7, 'Piranesi',              'Clarke',   2020, 12.00, NULL);
SELECT title FROM book WHERE genre = 'scifi' AND year < 1980;
SELECT title FROM book WHERE (genre = 'scifi' OR genre = 'fantasy') AND price < 9;
```

```text output
Dune
The Left Hand of Darkness
Neuromancer
The Hobbit
The Left Hand of Darkness
```

## IN and BETWEEN test membership

`IN` is a list of equals. `BETWEEN` is inclusive on both ends.

```sql file=n03.sql
CREATE TABLE book (
  id INTEGER PRIMARY KEY, title TEXT, author TEXT, year INTEGER,
  price NUMERIC, genre TEXT
);
INSERT INTO book VALUES
  (1, 'Dune',                  'Herbert',  1965, 9.99,  'scifi'),
  (2, 'Neuromancer',           'Gibson',   1984, 7.50,  'scifi'),
  (3, 'The Hobbit',            'Tolkien',  1937, 8.25,  'fantasy'),
  (4, 'Emma',                  'Austen',   1815, 5.00,  'classic'),
  (5, 'Persuasion',            'Austen',   1817, NULL,  'classic'),
  (6, 'The Left Hand of Darkness', 'Le Guin', 1969, 8.00, 'scifi'),
  (7, 'Piranesi',              'Clarke',   2020, 12.00, NULL);
SELECT title FROM book WHERE author IN ('Austen', 'Clarke');
SELECT title FROM book WHERE year BETWEEN 1960 AND 1990;
```

```text output
Emma
Persuasion
Piranesi
Dune
Neuromancer
The Left Hand of Darkness
```

## LIKE is case-sensitive

`%` is any run of characters. `_` is one character. `LIKE` distinguishes
`Dune` from `dune`. `ILIKE` does not. A leading `%` cannot use a btree
index.

```sql file=n04.sql
CREATE TABLE book (
  id INTEGER PRIMARY KEY, title TEXT, author TEXT, year INTEGER,
  price NUMERIC, genre TEXT
);
INSERT INTO book VALUES
  (1, 'Dune',                  'Herbert',  1965, 9.99,  'scifi'),
  (2, 'Neuromancer',           'Gibson',   1984, 7.50,  'scifi'),
  (3, 'The Hobbit',            'Tolkien',  1937, 8.25,  'fantasy'),
  (4, 'Emma',                  'Austen',   1815, 5.00,  'classic'),
  (5, 'Persuasion',            'Austen',   1817, NULL,  'classic'),
  (6, 'The Left Hand of Darkness', 'Le Guin', 1969, 8.00, 'scifi'),
  (7, 'Piranesi',              'Clarke',   2020, 12.00, NULL);
.headers on
SELECT title FROM book WHERE title LIKE 'The %';
SELECT title FROM book WHERE title LIKE '_mma';
SELECT count(*) AS lower_like FROM book WHERE title LIKE 'dune';
SELECT title FROM book WHERE title ILIKE 'dune';
```

```text output
title
The Hobbit
The Left Hand of Darkness
title
Emma
lower_like
0
title
Dune
```

## A comparison with NULL is unknown

`IS NULL` finds unknown values. `<>` does not: unknown is not true, so
`WHERE` drops the row. Put `OR col IS NULL` on the predicate when the
unknown rows belong in the result.

```sql file=n05.sql
CREATE TABLE book (
  id INTEGER PRIMARY KEY, title TEXT, author TEXT, year INTEGER,
  price NUMERIC, genre TEXT
);
INSERT INTO book VALUES
  (1, 'Dune',                  'Herbert',  1965, 9.99,  'scifi'),
  (2, 'Neuromancer',           'Gibson',   1984, 7.50,  'scifi'),
  (3, 'The Hobbit',            'Tolkien',  1937, 8.25,  'fantasy'),
  (4, 'Emma',                  'Austen',   1815, 5.00,  'classic'),
  (5, 'Persuasion',            'Austen',   1817, NULL,  'classic'),
  (6, 'The Left Hand of Darkness', 'Le Guin', 1969, 8.00, 'scifi'),
  (7, 'Piranesi',              'Clarke',   2020, 12.00, NULL);
SELECT title FROM book WHERE price IS NULL;
SELECT title FROM book WHERE genre <> 'scifi';
SELECT title FROM book WHERE genre <> 'scifi' OR genre IS NULL;
```

```text output
Persuasion
The Hobbit
Emma
Persuasion
The Hobbit
Emma
Persuasion
Piranesi
```

## NOT IN is never true if the list has NULL

`x NOT IN (1, NULL)` means `x <> 1 AND x <> NULL`. The second part is
unknown, so the whole predicate is unknown for every x. Prefer
`NOT EXISTS` when the list may contain NULL (lesson 05).

```sql file=n06.sql
CREATE TABLE book (
  id INTEGER PRIMARY KEY, title TEXT, author TEXT, year INTEGER,
  price NUMERIC, genre TEXT
);
INSERT INTO book VALUES
  (1, 'Dune',                  'Herbert',  1965, 9.99,  'scifi'),
  (2, 'Neuromancer',           'Gibson',   1984, 7.50,  'scifi'),
  (3, 'The Hobbit',            'Tolkien',  1937, 8.25,  'fantasy'),
  (4, 'Emma',                  'Austen',   1815, 5.00,  'classic'),
  (5, 'Persuasion',            'Austen',   1817, NULL,  'classic'),
  (6, 'The Left Hand of Darkness', 'Le Guin', 1969, 8.00, 'scifi'),
  (7, 'Piranesi',              'Clarke',   2020, 12.00, NULL);
SELECT count(*) AS with_null FROM book WHERE id NOT IN (1, NULL);
SELECT count(*) AS without_null FROM book WHERE id NOT IN (1);
```

```text output
0
6
```

## ORDER BY is the only order you can rely on

Without `ORDER BY`, row order is unspecified. It can change after an index
or an upgrade. `ASC` is the default. You can sort by several keys, or by
an expression. A NULL price sorts first in `DESC`; the next section shows
why, and how to move it.

```sql file=n07.sql
CREATE TABLE book (
  id INTEGER PRIMARY KEY, title TEXT, author TEXT, year INTEGER,
  price NUMERIC, genre TEXT
);
INSERT INTO book VALUES
  (1, 'Dune',                  'Herbert',  1965, 9.99,  'scifi'),
  (2, 'Neuromancer',           'Gibson',   1984, 7.50,  'scifi'),
  (3, 'The Hobbit',            'Tolkien',  1937, 8.25,  'fantasy'),
  (4, 'Emma',                  'Austen',   1815, 5.00,  'classic'),
  (5, 'Persuasion',            'Austen',   1817, NULL,  'classic'),
  (6, 'The Left Hand of Darkness', 'Le Guin', 1969, 8.00, 'scifi'),
  (7, 'Piranesi',              'Clarke',   2020, 12.00, NULL);
SELECT title, price FROM book ORDER BY price DESC;
SELECT title, year FROM book ORDER BY author, year DESC;
SELECT title FROM book ORDER BY length(title), title;
```

```text output
Persuasion|
Piranesi|12.00
Dune|9.99
The Hobbit|8.25
The Left Hand of Darkness|8.00
Neuromancer|7.50
Emma|5.00
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
```

## NULL sorts last in ascending order

`ASC` defaults to `NULLS LAST`. `DESC` defaults to `NULLS FIRST`. Write
`NULLS FIRST` or `NULLS LAST` when the default is not the order you want.

```sql file=n08.sql
CREATE TABLE book (
  id INTEGER PRIMARY KEY, title TEXT, author TEXT, year INTEGER,
  price NUMERIC, genre TEXT
);
INSERT INTO book VALUES
  (1, 'Dune',                  'Herbert',  1965, 9.99,  'scifi'),
  (2, 'Neuromancer',           'Gibson',   1984, 7.50,  'scifi'),
  (3, 'The Hobbit',            'Tolkien',  1937, 8.25,  'fantasy'),
  (4, 'Emma',                  'Austen',   1815, 5.00,  'classic'),
  (5, 'Persuasion',            'Austen',   1817, NULL,  'classic'),
  (6, 'The Left Hand of Darkness', 'Le Guin', 1969, 8.00, 'scifi'),
  (7, 'Piranesi',              'Clarke',   2020, 12.00, NULL);
SELECT title FROM book ORDER BY price;
SELECT title FROM book ORDER BY price NULLS FIRST;
```

```text output
Emma
Neuromancer
The Left Hand of Darkness
The Hobbit
Dune
Piranesi
Persuasion
Persuasion
Emma
Neuromancer
The Left Hand of Darkness
The Hobbit
Dune
Piranesi
```

## LIMIT and OFFSET take a page

Always pair them with a stable `ORDER BY`. `OFFSET n` still reads and
throws away `n` rows, so deep pages get slow.

```sql file=n09.sql
CREATE TABLE book (
  id INTEGER PRIMARY KEY, title TEXT, author TEXT, year INTEGER,
  price NUMERIC, genre TEXT
);
INSERT INTO book VALUES
  (1, 'Dune',                  'Herbert',  1965, 9.99,  'scifi'),
  (2, 'Neuromancer',           'Gibson',   1984, 7.50,  'scifi'),
  (3, 'The Hobbit',            'Tolkien',  1937, 8.25,  'fantasy'),
  (4, 'Emma',                  'Austen',   1815, 5.00,  'classic'),
  (5, 'Persuasion',            'Austen',   1817, NULL,  'classic'),
  (6, 'The Left Hand of Darkness', 'Le Guin', 1969, 8.00, 'scifi'),
  (7, 'Piranesi',              'Clarke',   2020, 12.00, NULL);
SELECT id, title FROM book ORDER BY id LIMIT 3;
SELECT id, title FROM book ORDER BY id LIMIT 3 OFFSET 3;
```

```text output
1|Dune
2|Neuromancer
3|The Hobbit
4|Emma
5|Persuasion
6|The Left Hand of Darkness
```

## Keyset paging does not discard rows

Remember the last id you returned. The next page is `WHERE id > :last ORDER BY id LIMIT n`.

```sql file=n10.sql
CREATE TABLE book (
  id INTEGER PRIMARY KEY, title TEXT, author TEXT, year INTEGER,
  price NUMERIC, genre TEXT
);
INSERT INTO book VALUES
  (1, 'Dune',                  'Herbert',  1965, 9.99,  'scifi'),
  (2, 'Neuromancer',           'Gibson',   1984, 7.50,  'scifi'),
  (3, 'The Hobbit',            'Tolkien',  1937, 8.25,  'fantasy'),
  (4, 'Emma',                  'Austen',   1815, 5.00,  'classic'),
  (5, 'Persuasion',            'Austen',   1817, NULL,  'classic'),
  (6, 'The Left Hand of Darkness', 'Le Guin', 1969, 8.00, 'scifi'),
  (7, 'Piranesi',              'Clarke',   2020, 12.00, NULL);
SELECT id, title FROM book WHERE id > 3 ORDER BY id LIMIT 2;
```

```text output
4|Emma
5|Persuasion
```

## DISTINCT removes duplicate result rows

It applies to the whole row you selected. A NULL genre is one of the
values. It sorts last in `ASC`. The second column is `genre IS NULL`.

```sql file=n11.sql
CREATE TABLE book (
  id INTEGER PRIMARY KEY, title TEXT, author TEXT, year INTEGER,
  price NUMERIC, genre TEXT
);
INSERT INTO book VALUES
  (1, 'Dune',                  'Herbert',  1965, 9.99,  'scifi'),
  (2, 'Neuromancer',           'Gibson',   1984, 7.50,  'scifi'),
  (3, 'The Hobbit',            'Tolkien',  1937, 8.25,  'fantasy'),
  (4, 'Emma',                  'Austen',   1815, 5.00,  'classic'),
  (5, 'Persuasion',            'Austen',   1817, NULL,  'classic'),
  (6, 'The Left Hand of Darkness', 'Le Guin', 1969, 8.00, 'scifi'),
  (7, 'Piranesi',              'Clarke',   2020, 12.00, NULL);
SELECT DISTINCT author FROM book ORDER BY author;
.headers on
SELECT DISTINCT genre, genre IS NULL AS unknown FROM book ORDER BY genre;
```

```text output
Austen
Clarke
Gibson
Herbert
Le Guin
Tolkien
genre|unknown
classic|f
fantasy|f
scifi|f
|t
```

## ORDER BY can use a SELECT alias

`ORDER BY` runs after `SELECT`, so it can use `with_tax`. `WHERE` runs
first, so the same alias is an error there. Repeat the expression in
`WHERE`, or filter in an outer query.

```sql file=n12.sql
CREATE TABLE book (
  id INTEGER PRIMARY KEY, title TEXT, author TEXT, year INTEGER,
  price NUMERIC, genre TEXT
);
INSERT INTO book VALUES
  (1, 'Dune',                  'Herbert',  1965, 9.99,  'scifi'),
  (2, 'Neuromancer',           'Gibson',   1984, 7.50,  'scifi'),
  (3, 'The Hobbit',            'Tolkien',  1937, 8.25,  'fantasy'),
  (4, 'Emma',                  'Austen',   1815, 5.00,  'classic'),
  (5, 'Persuasion',            'Austen',   1817, NULL,  'classic'),
  (6, 'The Left Hand of Darkness', 'Le Guin', 1969, 8.00, 'scifi'),
  (7, 'Piranesi',              'Clarke',   2020, 12.00, NULL);
-- expect-error
SELECT title, round(price * 1.2, 2) AS with_tax FROM book WHERE with_tax > 10;
SELECT title, round(price * 1.2, 2) AS with_tax
FROM book WHERE price IS NOT NULL ORDER BY with_tax DESC LIMIT 2;
```

```text output
Error: column "with_tax" does not exist
Piranesi|14.40
Dune|11.99
```

## A row can be compared with a row

`(author, genre) = ('Austen', 'classic')` matches both columns. It is
still one predicate.

```sql file=n13.sql
CREATE TABLE book (
  id INTEGER PRIMARY KEY, title TEXT, author TEXT, year INTEGER,
  price NUMERIC, genre TEXT
);
INSERT INTO book VALUES
  (1, 'Dune',                  'Herbert',  1965, 9.99,  'scifi'),
  (2, 'Neuromancer',           'Gibson',   1984, 7.50,  'scifi'),
  (3, 'The Hobbit',            'Tolkien',  1937, 8.25,  'fantasy'),
  (4, 'Emma',                  'Austen',   1815, 5.00,  'classic'),
  (5, 'Persuasion',            'Austen',   1817, NULL,  'classic'),
  (6, 'The Left Hand of Darkness', 'Le Guin', 1969, 8.00, 'scifi'),
  (7, 'Piranesi',              'Clarke',   2020, 12.00, NULL);
SELECT title FROM book WHERE (author, genre) = ('Austen', 'classic') ORDER BY year;
```

```text output
Emma
Persuasion
```

## Exercises

```sql file=exercise.sql
CREATE TABLE book (
  id INTEGER PRIMARY KEY, title TEXT, author TEXT, year INTEGER,
  price NUMERIC, genre TEXT
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
CREATE VIEW q1 AS SELECT NULL::TEXT AS title WHERE false;       -- TODO

-- q2: titles whose genre is not 'scifi' INCLUDING books with no genre,
--     ordered by id. Column: title.
CREATE VIEW q2 AS SELECT NULL::TEXT AS title WHERE false;       -- TODO

-- q3: the two most expensive books that have a price, most expensive first.
--     Column: title.
CREATE VIEW q3 AS SELECT NULL::TEXT AS title WHERE false;       -- TODO

-- q4: titles that start with 'P' or contain 'Hand', ordered by title.
CREATE VIEW q4 AS SELECT NULL::TEXT AS title WHERE false;       -- TODO

-- q5: books on "page 2" when ordered by id and the page size is 3
--     (ids 4, 5, 6). Column: id.
CREATE VIEW q5 AS SELECT NULL::INTEGER AS id WHERE false;       -- TODO

CREATE TABLE t (name TEXT, ok BOOLEAN CHECK (ok));
INSERT INTO t VALUES ('q1', (SELECT string_agg(title, '|') FROM q1) IS NOT DISTINCT FROM 'Emma|Persuasion|The Hobbit');
INSERT INTO t VALUES ('q2', (SELECT string_agg(title, '|') FROM q2) IS NOT DISTINCT FROM 'The Hobbit|Emma|Persuasion|Piranesi');
INSERT INTO t VALUES ('q3', (SELECT string_agg(title, '|') FROM q3) IS NOT DISTINCT FROM 'Piranesi|Dune');
INSERT INTO t VALUES ('q4', (SELECT string_agg(title, '|' ORDER BY title) FROM q4) IS NOT DISTINCT FROM 'Persuasion|Piranesi|The Left Hand of Darkness');
INSERT INTO t VALUES ('q5', (SELECT string_agg(id::TEXT, ',' ORDER BY id) FROM q5) IS NOT DISTINCT FROM '4,5,6');
SELECT 'PASS ' || name FROM t;
```

<details><summary>Solution</summary>

```sql file=solution.sql
CREATE TABLE book (
  id INTEGER PRIMARY KEY, title TEXT, author TEXT, year INTEGER,
  price NUMERIC, genre TEXT
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

CREATE TABLE t (name TEXT, ok BOOLEAN CHECK (ok));
INSERT INTO t VALUES ('q1', (SELECT string_agg(title, '|') FROM q1) IS NOT DISTINCT FROM 'Emma|Persuasion|The Hobbit');
INSERT INTO t VALUES ('q2', (SELECT string_agg(title, '|') FROM q2) IS NOT DISTINCT FROM 'The Hobbit|Emma|Persuasion|Piranesi');
INSERT INTO t VALUES ('q3', (SELECT string_agg(title, '|') FROM q3) IS NOT DISTINCT FROM 'Piranesi|Dune');
INSERT INTO t VALUES ('q4', (SELECT string_agg(title, '|' ORDER BY title) FROM q4) IS NOT DISTINCT FROM 'Persuasion|Piranesi|The Left Hand of Darkness');
INSERT INTO t VALUES ('q5', (SELECT string_agg(id::TEXT, ',' ORDER BY id) FROM q5) IS NOT DISTINCT FROM '4,5,6');
SELECT 'PASS ' || name FROM t;
```

</details>

Next: [03 — Aggregation](03-aggregation.md)
