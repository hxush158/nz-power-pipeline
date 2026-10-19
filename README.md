# nz-power-pipeline

NZ electricity market (EMI) wholesale price pipeline: download, store in Azure,
model with dbt, and (planned) load into Snowflake and schedule with Airflow.

Status: work in progress. Ingest, upload and the local dbt models with tests are done.

## Data flow

```
EMI website -> download (Python) -> data/raw/prices/*.csv
            -> upload (Python)   -> Azure ADLS Gen2 (raw container, monthly partitions)
            -> dbt (DuckDB locally) -> staging -> dimensions -> fact -> marts
```

Planned: Snowflake as the warehouse, Airflow for daily runs, GitHub Actions for CI.

## dbt models

| Layer | Model | Grain |
|---|---|---|
| staging | `stg_prices` | one CSV row |
| dimension | `dim_date`, `dim_trading_period`, `dim_node` | day / day x trading period / node |
| fact | `fact_electricity_price` | trading period x node x version (interim / final) |
| mart | `mart_current_price` | trading period x node (final if available, else interim) |
| mart | `mart_daily_price` | trading day x node |
| view | `v_dim_node` | node, with derived `first_seen_date` |

Design notes: `docs/model_design.md`. Source data: `docs/data_dictionary.md`.

## Run it

Requires [uv](https://docs.astral.sh/uv/). Raw files go in `data/raw/prices/`
(named `YYYYMMDD_final.csv` or `YYYYMMDD_interim.csv`); `data/` is not committed.

```bash
uv sync
uv run dbt build --project-dir dbt --profiles-dir dbt   # build models and run all tests
uv run pytest                                           # ingest and upload tests
uv run ruff check
```

Run dbt from the project root: the raw file path (`raw_prices_glob` in
`dbt/dbt_project.yml`) is relative to it.

## Tests

- dbt generic tests (unique, not_null, relationships, accepted_values) in the YAML files.
- dbt unit tests with hand-made input rows: `dbt/models/marts/_unit_tests.yml`.
- Singular SQL tests in `dbt/tests/`: reconciliation of stg and fact row counts,
  daylight-saving day period counts (46 / 48 / 50), period boundaries in UTC.
