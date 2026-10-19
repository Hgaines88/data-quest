# Bronze-to-Silver quality checks

Run `validate_bronze_to_silver.sql` after successful Bronze and Silver updates.
It is a read-only reconciliation report: every row is one named contract check,
and the validation passes only when every `passed` value is `true`.

The report distinguishes rejected-row deltas from conversion fidelity. It
compares normalized Bronze values to the corresponding Silver values in both
directions, so an added, omitted, or changed non-null value cannot pass merely
because the layer counts agree.

The query uses the project's default catalog and schema. Replace
`workspace.rearc_data_quest` when the deployment overrides those defaults.

