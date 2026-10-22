-- =============================================================================
-- Consultas para generar evidencias (SOLO LECTURA). Entorno dev: workspace.dev_*
-- Para prod, sustituye dev_bronze/dev_silver/dev_gold por bronze/silver/gold.
-- Los permisos se verifican con seguridad/verificar_permisos.sql (no se duplican aquí).
-- =============================================================================

-- E1. Conteo de las 8 tablas (captura: DEV_CONTEOS_TABLAS.png)
-- Es un listado de evidencia: no combina datos de las dos fuentes, solo pone sus conteos uno junto a otro.
-- Esperado según las pruebas locales: 1000, 205, 1000, 205, 165, 15, 22, 9.
SELECT 'dev_bronze.ecommerce_ventas'                         AS tabla, COUNT(*) AS filas FROM workspace.dev_bronze.ecommerce_ventas
UNION ALL SELECT 'dev_bronze.automobiles_specs',                         COUNT(*) FROM workspace.dev_bronze.automobiles_specs
UNION ALL SELECT 'dev_silver.ecommerce_ventas',                          COUNT(*) FROM workspace.dev_silver.ecommerce_ventas
UNION ALL SELECT 'dev_silver.automobiles_specs',                         COUNT(*) FROM workspace.dev_silver.automobiles_specs
UNION ALL SELECT 'dev_gold.ecommerce_ventas_mensuales_categoria',        COUNT(*) FROM workspace.dev_gold.ecommerce_ventas_mensuales_categoria
UNION ALL SELECT 'dev_gold.ecommerce_ventas_segmento_categoria',         COUNT(*) FROM workspace.dev_gold.ecommerce_ventas_segmento_categoria
UNION ALL SELECT 'dev_gold.automobiles_resumen_marca',                   COUNT(*) FROM workspace.dev_gold.automobiles_resumen_marca
UNION ALL SELECT 'dev_gold.automobiles_resumen_carroceria_combustible',  COUNT(*) FROM workspace.dev_gold.automobiles_resumen_carroceria_combustible;

-- E2. Tipo de tabla (captura: DEV_TIPO_TABLAS.png). Se espera EXTERNAL en las 8.
SELECT table_schema, table_name, table_type
FROM workspace.information_schema.tables
WHERE table_schema IN ('dev_bronze', 'dev_silver', 'dev_gold')
ORDER BY table_schema, table_name;

-- E3. Ubicación Delta (captura: DEV_UBICACIONES_DELTA.png).
-- Se espera s3://databricks-retail-etl-2026-smart/lakehouse/dev/<capa>/<tabla>.
DESCRIBE DETAIL workspace.dev_bronze.ecommerce_ventas;
DESCRIBE DETAIL workspace.dev_bronze.automobiles_specs;
DESCRIBE DETAIL workspace.dev_silver.ecommerce_ventas;
DESCRIBE DETAIL workspace.dev_silver.automobiles_specs;
DESCRIBE DETAIL workspace.dev_gold.ecommerce_ventas_mensuales_categoria;
DESCRIBE DETAIL workspace.dev_gold.ecommerce_ventas_segmento_categoria;
DESCRIBE DETAIL workspace.dev_gold.automobiles_resumen_marca;
DESCRIBE DETAIL workspace.dev_gold.automobiles_resumen_carroceria_combustible;
