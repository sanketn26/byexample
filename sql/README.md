# SQL by Example (practice edition)

Runs on **PostgreSQL 16** in the Docker container `byexample-pg`. Start it
with `make pg-up` before `make verify-sql`, and stop it with `make pg-down`.
Each lesson is a series of tiny scripts, one concept each. The course runner
creates a throwaway database, prints rows as `a|b|c`, and prints booleans
as `t` and `f`:

```sh
python3 tools/sqlrun.py n01.sql
```

Exercises are views you fill in. The comment `-- expect-error` marks a
statement that must fail. Lesson 15 is the PostgreSQL queries people look
up: `DISTINCT ON`, `ON CONFLICT`, `jsonb`, `generate_series`, `FILTER`,
and `LATERAL`.

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
| 15 | [PostgreSQL patterns](15-postgres.md) | `DISTINCT ON`, upsert, `jsonb`, `LATERAL`, `FILTER` |
