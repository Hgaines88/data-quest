# Gold access-control SQL

These scripts implement and validate the DQ-26 data-plane portion of the
`data_quest_readonly_analysts` access model.

| File | Run as | Purpose |
| --- | --- | --- |
| `apply_gold_readonly_access.sql` | Catalog/schema owner or access administrator | Grant only parent usage and exact-table reads |
| `inspect_gold_readonly_access.sql` | Object owner or access administrator | Display effective grants on each governed object |
| `analyst_positive_checks.sql` | Dedicated non-admin analyst | Prove all three intended Gold reads succeed |
| `analyst_negative_checks.sql` | Dedicated non-admin analyst, one statement at a time | Prove writes and unauthorized-layer reads fail |
| `revoke_gold_readonly_access.sql` | Catalog/schema owner or access administrator | Remove the data grants during teardown |

Warehouse **Can use**, dashboard **Can view**, group creation/membership, and
the dashboard's individual data permission mode are workspace/account controls;
apply them through the reviewed administrative UI or API steps in
[`docs/GOLD_ACCESS_CONTROL.md`](../../docs/GOLD_ACCESS_CONTROL.md).

The default deployment is `workspace.rearc_data_quest`. Retarget every object
reference consistently for another environment. Never replace the three table
grants with schema-wide `SELECT`.

