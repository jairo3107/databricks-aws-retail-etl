-- =============================================================================
-- PrepAmb · Preparación del ambiente: catálogo, esquemas y External Location
-- =============================================================================
-- DOCUMENTAL. El job NO ejecuta este archivo. Separa:
--   [ADMIN]   lo que ejecuta a mano un admin u owner, una sola vez
--   [JOB]     lo que ya hace automáticamente proceso/00_prep_amb.py (aquí solo como referencia)
--
-- No es destructivo: no hay DROP, REPLACE ni recreación de recursos.
-- YA EXISTEN y NO se recrean: bucket s3://databricks-retail-etl-2026-smart, IAM Role,
-- Storage Credential y External Location sobre la raíz del bucket.
--
-- Workspace: Databricks Free Edition (un único workspace). dev y prod son una separación
-- lógica dentro del mismo catálogo:
--   dev  -> esquemas dev_bronze, dev_silver, dev_gold | datos en s3://…/lakehouse/dev/
--   prod -> esquemas bronze, silver, gold             | datos en s3://…/lakehouse/prod/
--   RAW compartido (los notebooks solo lo leen)       | s3://…/raw/
--   La External Location cubre la raíz del bucket con lectura, escritura y borrado probados:
--   el almacenamiento NO está restringido a solo lectura en raw/. Ver seguridad/README.md.
--
-- Marcadores que hay que sustituir antes de ejecutar en el SQL editor:
--   <catalogo>           catálogo de UC existente: workspace (confirmado)
--   <external_location>  nombre de la External Location existente (SHOW EXTERNAL LOCATIONS)
--   <identidad_job>      service principal (application ID) o usuario con el que despliega CI
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0) [ADMIN] Comprobaciones de solo lectura
-- -----------------------------------------------------------------------------
SHOW CATALOGS;
SHOW EXTERNAL LOCATIONS;
DESCRIBE EXTERNAL LOCATION `<external_location>`;      -- url debe ser s3://databricks-retail-etl-2026-smart/
SHOW GRANTS ON EXTERNAL LOCATION `<external_location>`;
LIST 's3://databricks-retail-etl-2026-smart/raw/';     -- deben aparecer ecommerce/ y automobiles/

-- -----------------------------------------------------------------------------
-- 1) [ADMIN] Catálogo. El job nunca crea ni borra catálogos. Solo si no existe:
-- -----------------------------------------------------------------------------
-- CREATE CATALOG IF NOT EXISTS `<catalogo>`;

-- -----------------------------------------------------------------------------
-- 2) [ADMIN] Privilegios mínimos de la identidad del job.
--    No hace falta si <identidad_job> es la owner del catálogo y de la External Location
--    (habitual en Free Edition cuando despliega el mismo usuario que los creó).
-- -----------------------------------------------------------------------------
GRANT USE CATALOG, CREATE SCHEMA ON CATALOG `<catalogo>` TO `<identidad_job>`;
GRANT READ FILES, CREATE EXTERNAL TABLE ON EXTERNAL LOCATION `<external_location>` TO `<identidad_job>`;
-- Opcional, para que proceso/04_grants.py pueda conceder USE CATALOG al grupo lector:
-- GRANT MANAGE ON CATALOG `<catalogo>` TO `<identidad_job>`;

-- -----------------------------------------------------------------------------
-- 3) [JOB] Esquemas. Los crea proceso/00_prep_amb.py si no existen (con CREATE SCHEMA).
--    Solo si el admin NO concede CREATE SCHEMA, debe crearlos a mano y delegar su uso:
-- -----------------------------------------------------------------------------
-- CREATE SCHEMA IF NOT EXISTS `<catalogo>`.`dev_bronze`;
-- CREATE SCHEMA IF NOT EXISTS `<catalogo>`.`dev_silver`;
-- CREATE SCHEMA IF NOT EXISTS `<catalogo>`.`dev_gold`;
-- CREATE SCHEMA IF NOT EXISTS `<catalogo>`.`bronze`;
-- CREATE SCHEMA IF NOT EXISTS `<catalogo>`.`silver`;
-- CREATE SCHEMA IF NOT EXISTS `<catalogo>`.`gold`;
-- GRANT USE SCHEMA, CREATE TABLE, MODIFY, SELECT ON SCHEMA `<catalogo>`.`<esquema>` TO `<identidad_job>`;

-- -----------------------------------------------------------------------------
-- 4) [JOB] Tablas Delta externas. Las crean 01_extract_*, 02_transform_* y 03_load_gold
--    en s3://databricks-retail-etl-2026-smart/lakehouse/<entorno>/<capa>/<tabla>. Aquí no se hace nada.
-- -----------------------------------------------------------------------------

-- -----------------------------------------------------------------------------
-- 5) [ADMIN] Verificación final
-- -----------------------------------------------------------------------------
SHOW GRANTS `<identidad_job>` ON CATALOG `<catalogo>`;
SHOW GRANTS `<identidad_job>` ON EXTERNAL LOCATION `<external_location>`;
SHOW SCHEMAS IN `<catalogo>`;
