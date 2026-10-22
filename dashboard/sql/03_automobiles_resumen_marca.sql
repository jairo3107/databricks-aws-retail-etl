-- Dataset: precio y rendimiento por marca (Automobiles)
-- Tabla:   workspace.dev_gold.automobiles_resumen_marca   (prod: workspace.gold.…)
-- Visual:  barras horizontales (Y = make, X = precio_promedio) y tabla con precio_min/precio_max.
-- Nota:    registros_sin_precio cuenta las filas cuyo price era '?' en origen; no se imputan.
--          La moneda de price no está documentada en la fuente.
SELECT
  make,
  registros,
  registros_sin_precio,
  precio_promedio,
  precio_min,
  precio_max,
  horsepower_promedio,
  city_mpg_promedio,
  highway_mpg_promedio
FROM workspace.dev_gold.automobiles_resumen_marca
ORDER BY precio_promedio DESC NULLS LAST, make
