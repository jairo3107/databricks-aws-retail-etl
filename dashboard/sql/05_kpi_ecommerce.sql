-- Dataset: indicadores de E-commerce (una fila). Solo usa tablas de E-commerce: las fuentes no se combinan.
-- Visual:  contadores (counter) para cada columna.
SELECT
  SUM(unidades_vendidas)      AS unidades_vendidas_total,
  SUM(gasto_marketing_total)  AS gasto_marketing_total,
  SUM(dias_con_registro)      AS registros_silver,
  COUNT(DISTINCT anio_mes)    AS meses,
  COUNT(DISTINCT product_category) AS categorias
FROM workspace.dev_gold.ecommerce_ventas_mensuales_categoria
