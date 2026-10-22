-- Dataset: ventas mensuales por categoría (E-commerce)
-- Tabla:   workspace.dev_gold.ecommerce_ventas_mensuales_categoria   (prod: workspace.gold.…)
-- Visual:  línea o barras apiladas. X = mes, Y = unidades_vendidas, color = product_category
-- Nota:    "discount_promedio_valor_original" conserva la unidad original de Discount, que no está verificada
--          (porcentaje o importe); no se presenta como porcentaje.
SELECT
  to_date(concat(anio_mes, '-01'))  AS mes,
  product_category,
  dias_con_registro,
  unidades_vendidas,
  precio_promedio,
  discount_promedio_valor_original,
  gasto_marketing_total
FROM workspace.dev_gold.ecommerce_ventas_mensuales_categoria
ORDER BY mes, product_category
