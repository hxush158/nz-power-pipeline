# AI-assisted development log

This log records how GitHub Copilot was used in nz-power-pipeline: what it helped with, where its output was wrong or incomplete, and how problems were caught and fixed.

**Working principle:** Copilot drafts, tests verify, I review and decide.

## How to use this log
- Add an entry when Copilot's output needed a meaningful correction, or when it saved notable time on a well-defined task. Routine autocomplete does not need an entry.
- Keep each entry short (about 5 minutes to write).
- Record how the problem was detected (test failure, code review, row-count check, comparison with source data). This is the most valuable part.
- Mark entries worth using as interview stories with ⭐.

## Summary

| # | Date | Area | Task | Issue found | Detected by | ⭐ |
|---|------|------|------|-------------|-------------|----|
| 1 | YYYY-MM-DD | dbt | | | | |

Areas: dbt / SQL / Airflow / Python / Snowflake / Azure / docs / tests

## Entry template

### #N — Short title
- **Date:**
- **Area:**
- **Task:** what I was trying to do
- **Prompt / context given:** short summary, plus which files were open or referenced
- **What Copilot produced:** one or two lines, or a small snippet
- **Problem:** what was wrong, missing or risky (write "none" if it was correct)
- **How I detected it:** test, review, data check, etc.
- **Fix:** what I changed and why
- **Verification:** how I confirmed the fix (tests passing, row counts, spot checks)
- **Lesson:** what I will do differently, or what to add to `copilot-instructions.md`
- **Time impact:** rough estimate (e.g. saved ~30 min, or cost ~15 min extra)

## Example entry (illustrative, delete once real entries exist)

### #0 — Deduplicating revised price records
- **Date:** YYYY-MM-DD
- **Area:** dbt / SQL
- **Task:** Build `stg_emi__final_prices` with one row per node per trading period.
- **Prompt / context given:** Asked Copilot to deduplicate the raw price table; source YAML was open.
- **What Copilot produced:** A `select distinct` over all columns.
- **Problem:** Revised records differ in price and publish timestamp, so `distinct` kept both versions and the grain was broken.
- **How I detected it:** `dbt_utils.unique_combination_of_columns` test on (`trading_date`, `trading_period`, `node`) failed.
- **Fix:** Replaced with `qualify row_number() over (partition by trading_date, trading_period, node order by published_at desc) = 1` to keep the latest revision.
- **Verification:** Test passes; row count equals distinct key count; spot-checked a revised period against the EMI source file.
- **Lesson:** Added a domain rule to `copilot-instructions.md`: source data can be revised, keep the latest version.
- **Time impact:** Saved ~20 min on boilerplate; the test caught the logic error before it reached the marts.
