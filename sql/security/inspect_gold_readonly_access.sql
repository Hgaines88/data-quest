-- Run as an owner or access administrator. The SHOW GRANTS statements are
-- object-specific checks. The final union is the required complete inventory
-- across every securable currently present in the project schema.

SHOW GRANTS `data_quest_readonly_analysts` ON CATALOG workspace;

SHOW GRANTS `data_quest_readonly_analysts`
ON SCHEMA workspace.rearc_data_quest;

SHOW GRANTS `data_quest_readonly_analysts` ON TABLE
  workspace.rearc_data_quest.gold_population_summary_2013_2018;

SHOW GRANTS `data_quest_readonly_analysts` ON TABLE
  workspace.rearc_data_quest.gold_bls_best_year_by_series;

SHOW GRANTS `data_quest_readonly_analysts` ON TABLE
  workspace.rearc_data_quest.gold_bls_q01_population;

-- This must return exactly five rows for data_quest_readonly_analysts:
-- USE_CATALOG, USE_SCHEMA, and SELECT on the three named Gold contracts.
-- It intentionally inventories every table/view, Volume, and routine in the
-- project schema so an unexpected lower-layer grant cannot remain invisible.
-- Repeat with grantee = 'users' and with every other group inherited by the
-- validation identity. Separately confirm that the new validation identity has
-- no direct grants and no additional group memberships.
SELECT
  'CATALOG' AS object_type,
  catalog_name AS object_name,
  privilege_type
FROM system.information_schema.catalog_privileges
WHERE grantee = 'data_quest_readonly_analysts'
  AND catalog_name = 'workspace'

UNION ALL

SELECT
  'SCHEMA' AS object_type,
  CONCAT(catalog_name, '.', schema_name) AS object_name,
  privilege_type
FROM system.information_schema.schema_privileges
WHERE grantee = 'data_quest_readonly_analysts'
  AND catalog_name = 'workspace'
  AND schema_name = 'rearc_data_quest'

UNION ALL

SELECT
  'TABLE' AS object_type,
  CONCAT(table_catalog, '.', table_schema, '.', table_name) AS object_name,
  privilege_type
FROM system.information_schema.table_privileges
WHERE grantee = 'data_quest_readonly_analysts'
  AND table_catalog = 'workspace'
  AND table_schema = 'rearc_data_quest'

UNION ALL

SELECT
  'VOLUME' AS object_type,
  CONCAT(volume_catalog, '.', volume_schema, '.', volume_name) AS object_name,
  privilege_type
FROM system.information_schema.volume_privileges
WHERE grantee = 'data_quest_readonly_analysts'
  AND volume_catalog = 'workspace'
  AND volume_schema = 'rearc_data_quest'

UNION ALL

SELECT
  'ROUTINE' AS object_type,
  CONCAT(routine_catalog, '.', routine_schema, '.', routine_name) AS object_name,
  privilege_type
FROM system.information_schema.routine_privileges
WHERE grantee = 'data_quest_readonly_analysts'
  AND routine_catalog = 'workspace'
  AND routine_schema = 'rearc_data_quest'

ORDER BY object_type, object_name, privilege_type;

