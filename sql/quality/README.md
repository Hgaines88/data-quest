# Repeatable quality checks

## Bronze-to-Silver reconciliation

Run `validate_bronze_to_silver.sql` after successful Bronze and Silver updates.
It is a read-only reconciliation report: every row is one named contract check,
and the validation passes only when every `passed` value is `true`.

The report distinguishes rejected-row deltas from conversion fidelity. It
compares normalized Bronze values to the corresponding Silver values in both
directions, so an added, omitted, or changed non-null value cannot pass merely
because the layer counts agree.

The query uses the project's default catalog and schema. Replace
`workspace.rearc_data_quest` when the deployment overrides those defaults.

## Gold SQL/PySpark reconciliation

Run `validate_gold_cross_implementation.sql` after a successful Gold update.
It independently reconstructs all three Spark SQL results from governed Silver
tables and compares them with the primary PySpark Gold materialized views.
Every output row is one named check, and the report passes only when every
`passed` value is `true`.

The report compares ordered schema signatures, row counts, business keys, null
behavior, and values. Question 1's `DOUBLE` mean and population-standard-
deviation values use an explicit absolute tolerance of `1e-6`; discrete,
`DECIMAL`, integer, string, and boolean fields use exact or null-safe equality.
It also verifies requested bounds, uniqueness, deterministic earliest-year tie
breaking, Question 3 left-join cardinality, and direct Silver-level spot checks.

Relational tables do not promise physical row order. The report therefore
validates that each documented ordering key is complete and unique; the tracked
SQL alternatives and reviewer-facing queries retain explicit `ORDER BY`
clauses.

The query is read-only and uses the project's default catalog and schema.
Replace `workspace.rearc_data_quest` when the deployment overrides those
defaults.

Intentional representation differences are limited and explicit:

- the PySpark results are governed materialized views, while the SQL versions
  are ephemeral CTEs reconstructed from the same Silver contracts;
- Question 1 uses `DOUBLE` aggregates, so equality is evaluated within `1e-6`;
- Questions 2 and 3 retain exact `DECIMAL`, integer, string, boolean, and
  null-safe comparisons;
- storage order is not treated as data. Deterministic keys are validated here,
  while reviewer-facing queries apply their documented `ORDER BY` clauses.

