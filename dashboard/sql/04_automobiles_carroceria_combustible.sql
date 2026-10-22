-- Dataset: carrocería × combustible (Automobiles)
-- Tabla:   workspace.dev_gold.automobiles_resumen_carroceria_combustible   (prod: workspace.gold.…)
-- Visual:  barras agrupadas (X = body_style, Y = registros, color = fuel_type) y
--          dispersión horsepower_promedio frente a precio_promedio.
SELECT
  body_style,
  fuel_type,
  registros,
  precio_promedio,
  horsepower_promedio,
  engine_size_promedio,
  city_mpg_promedio
FROM workspace.dev_gold.automobiles_resumen_carroceria_combustible
ORDER BY body_style, fuel_type
