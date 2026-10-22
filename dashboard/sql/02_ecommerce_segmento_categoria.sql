-- Dataset: unidades por segmento de cliente y categoría (E-commerce)
-- Tabla:   workspace.dev_gold.ecommerce_ventas_segmento_categoria   (prod: workspace.gold.…)
-- Visual:  heatmap (X = product_category, Y = customer_segment, valor = unidades_vendidas)
--          o barras agrupadas por segmento.
SELECT
  customer_segment,
  product_category,
  registros,
  unidades_vendidas,
  unidades_promedio,
  precio_promedio,
  gasto_marketing_total
FROM workspace.dev_gold.ecommerce_ventas_segmento_categoria
ORDER BY customer_segment, product_category
