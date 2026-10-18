# Copilot instructions for nz-power-pipeline

## Project context
- Data engineering portfolio project using New Zealand Electricity Market (EMI) data: wholesale prices and generation.
- Stack: Snowflake (warehouse), dbt (transformations), Airflow (orchestration), Azure Data Lake Storage Gen2 (raw landing zone), Python. PySpark may be added later.
- Data flow: EMI files -> ADLS raw -> Snowflake RAW schema -> dbt staging -> intermediate -> marts.

## Domain rules
- EMI trading periods are half-hour intervals numbered from 1 each trading day (normally 1-48; daylight-saving change days have 46 or 50). Never assume 48 periods per day.
- All trading dates and times are in New Zealand time (Pacific/Auckland). Store timestamps as TIMESTAMP_TZ, or convert explicitly. Never mix UTC and NZ time silently.
- Prices are in NZD per MWh. Keep units in column names where helpful (e.g. `price_nzd_per_mwh`, `generation_mwh`).
- Nodes are identified by point-of-connection codes such as `BEN2201` and `OTA2201`. Keep them as strings.
- Source data can be revised and republished. When deduplicating, keep the latest version of a record, not an arbitrary one.

## dbt conventions
- Layers and prefixes: `stg_` (one model per source table, renaming and type casting only), `int_` (joins and business logic), `mart_` (analysis-ready, one clear grain per model).
- Every model has a YAML entry with a description, column descriptions, and a stated grain.
- Every model has tests: at minimum `unique` and `not_null` on the primary key (or `dbt_utils.unique_combination_of_columns` for composite keys). Add `accepted_values` and `relationships` where they apply.
- Use `ref()` and `source()`; never hard-code database or schema names.
- Prefer incremental models for large fact tables; state the `unique_key` and how late-arriving or revised data is handled.

## SQL style (Snowflake)
- Snowflake SQL dialect only.
- Structure queries with CTEs: import CTEs first, then logic CTEs, then a final `select`.
- Select explicit columns; no `select *` outside import CTEs.
- Lowercase keywords and snake_case identifiers.
- For deduplication, use `qualify row_number() over (partition by ... order by ... desc) = 1` and comment why that ordering picks the correct record.
- Do not invent column or table names. If a column is not visible in the project files, say so and ask.

## Airflow conventions
- Tasks must be idempotent: re-running a task for the same logical date gives the same result.
- Use the logical date (`ds` / `data_interval_start`) for partitioning, not the current time.
- No credentials in code. Use Airflow connections or environment variables.
- Set retries and clear task IDs; keep DAG files free of heavy top-level code.

## Python conventions
- Python 3.11+, type hints, small functions, `logging` instead of `print`.
- Configuration through environment variables or config files, never hard-coded secrets.

## How to respond
- When generating non-trivial SQL (window functions, subqueries, incremental logic), add a short explanation of what each step does. I am rebuilding my SQL skills and need to understand the code, not just receive it.
- State assumptions explicitly (grain, time zone, how duplicates are resolved).
- Suggest the dbt tests that would catch errors in the code you generate.
- If a request is ambiguous, ask a clarifying question instead of guessing.
