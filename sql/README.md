# SQL by Example (practice edition)

Runs on **SQLite 3.35+** (window functions, `RETURNING`, JSON). It needs no
server. Each lesson is one `.sql` script. Run it with the course runner (it
behaves like `sqlite3 -bail :memory:` and needs only Python 3.12):

```sh
python3 tools/sqlrun.py example.sql
```

or paste it into any `sqlite3` shell. Exercises are views you fill in; the
checks at the bottom stop at the first wrong answer and name it. The comment
`-- expect-error` marks a statement that must fail (plain comment elsewhere).
Lesson 15 shows where PostgreSQL and MySQL differ.

| # | Lesson | You will practise |
|---|--------|-------------------|
| 01 | [Values](01-values.md) | types, `NULL` and three-valued logic, `CASE`, `coalesce` |
| 02 | [Filtering and sorting](02-filtering-sorting.md) | `WHERE`, `IN`, `LIKE`, `ORDER BY`, `LIMIT`, paging |
| 03 | [Aggregation](03-aggregation.md) | `GROUP BY`, `HAVING`, `FILTER`, conditional aggregates |
| 04 | [Joins](04-joins.md) | inner, left, self, anti-joins, set operations |
| 05 | [Subqueries and CTEs](05-subqueries-ctes.md) | scalar, `EXISTS`, correlated, `WITH` |
| 06 | [Window functions](06-window-functions.md) | ranking, running totals, `lag`, top-N per group |
| 07 | [Changing data](07-changing-data.md) | `INSERT`, `UPDATE`, `DELETE`, upsert, `RETURNING` |
| 08 | [Schema design](08-schema-design.md) | keys, constraints, foreign keys, normalisation |
| 09 | [Transactions](09-transactions.md) | `BEGIN`/`COMMIT`, savepoints, guarded updates, idempotency |
| 10 | [Indexes and query plans](10-indexes.md) | `EXPLAIN QUERY PLAN`, composite, partial, expression indexes |
| 11 | [Views and triggers](11-views-triggers.md) | views, audit trails, `RAISE`, `INSTEAD OF` |
| 12 | [JSON, dates and text](12-json-dates-text.md) | `->>`, `json_each`, `strftime`, `printf` |
| 13 | [Recursive queries](13-recursive-ctes.md) | trees, graphs, sequences, cycle safety |
| 14 | [Capstone: bookstore](14-capstone-bookstore.md) | schema + migrations + analytics end to end |
| 15 | [Dialects](15-dialects.md) | SQLite vs PostgreSQL vs MySQL, the portable core |
