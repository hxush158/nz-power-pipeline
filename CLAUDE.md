# Collaboration rules for this repo

This is a learning portfolio project. The owner is building data engineering skills.
Help in a way that keeps the owner in control of design and verification.

## Before writing code
- Only implement functions that already have a spec in comments (inputs, outputs, edge cases).
  If the spec is missing or unclear, ask questions instead of guessing.
- Keep each change small: one function or one model at a time.

## Tests
- The owner designs test cases and expected values. You may write test code for cases
  the owner listed, but never invent or change expected values without asking.

## After writing code
- Explain what each new function does and why, in plain language.
- Point out edge cases the spec did not cover.
- Do not run git commit or push. The owner commits.

## Stack
- Python managed by uv (`uv run ...`), DuckDB, pytest, ruff. Later: dbt, Terraform, AWS.
- Data under data/ is never committed.
