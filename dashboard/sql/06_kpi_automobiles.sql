-- Dataset: indicadores de Automobiles (una fila). Solo usa tablas de Automobiles: las fuentes no se combinan.
-- Visual:  contadores (counter) para cada columna.
SELECT
  SUM(registros)             AS vehiculos,
  SUM(registros_sin_precio)  AS vehiculos_sin_precio,
  COUNT(*)                   AS marcas,
  MIN(precio_min)            AS precio_minimo,
  MAX(precio_max)            AS precio_maximo
FROM workspace.dev_gold.automobiles_resumen_marca
