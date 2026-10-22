# dashboard/

Carpeta de entrega **requerida** por la estructura del enunciado.

> **Estado: el dashboard todavía no existe en Databricks.** Esta carpeta contiene las consultas y las instrucciones para
> construirlo. Las capturas se añadirán cuando se haya montado de verdad. No hay capturas ficticias.

## Consultas (datasets)

Cada archivo de [`sql/`](sql/) es un dataset del dashboard. Las consultas leen **solo Gold** y no combinan las dos fuentes.

| Archivo | Tabla Gold | Filas esperadas* | Visualización sugerida |
|---|---|---|---|
| [`01_ecommerce_ventas_mensuales.sql`](sql/01_ecommerce_ventas_mensuales.sql) | `ecommerce_ventas_mensuales_categoria` | 165 | Línea o barras apiladas: mes × unidades, color por categoría |
| [`02_ecommerce_segmento_categoria.sql`](sql/02_ecommerce_segmento_categoria.sql) | `ecommerce_ventas_segmento_categoria` | 15 | Heatmap: segmento × categoría, valor = unidades |
| [`03_automobiles_resumen_marca.sql`](sql/03_automobiles_resumen_marca.sql) | `automobiles_resumen_marca` | 22 | Barras horizontales: precio medio por marca, más una tabla de mínimo y máximo |
| [`04_automobiles_carroceria_combustible.sql`](sql/04_automobiles_carroceria_combustible.sql) | `automobiles_resumen_carroceria_combustible` | 9 | Barras agrupadas: carrocería × combustible, y dispersión potencia frente a precio |
| [`05_kpi_ecommerce.sql`](sql/05_kpi_ecommerce.sql) | `ecommerce_ventas_mensuales_categoria` | 1 | Contadores: unidades totales (29 631), gasto en marketing, meses, categorías |
| [`06_kpi_automobiles.sql`](sql/06_kpi_automobiles.sql) | `automobiles_resumen_marca` | 1 | Contadores: vehículos (205), sin precio (4), marcas (22), rango de precio |

\* Calculadas en local con los CSV de `datasets/`. `tests/test_dashboard_sql.py` ejecuta cada consulta contra las tablas Gold
generadas en local y comprueba estas cifras. Es una prueba local, **no** una ejecución en Databricks.

Las consultas apuntan a **`workspace.dev_gold`**, el único entorno ejecutado hasta ahora. Cuando prod esté desplegado y
ejecutado, sustituye `workspace.dev_gold.` por `workspace.gold.` en cada dataset.

Cautelas al presentar los datos (ver [docs/esquemas_detectados.md](../docs/esquemas_detectados.md)):
- `discount_promedio_valor_original`: la unidad de `Discount` **no está verificada**. No lo rotules como porcentaje.
- `precio_*`: la moneda no está documentada en las fuentes.
- `registros_sin_precio`: vehículos cuyo `price` era `?` en origen. No se imputan.

## Montar el dashboard en Databricks (AI/BI Dashboard)

1. En el workspace: **New → Dashboard**. Elige como cómputo el SQL warehouse disponible (Free Edition ofrece uno).
2. Pestaña **Data → Create from SQL**: crea un dataset por cada archivo de `sql/` y pega su contenido. Nómbralo como el archivo, sin `.sql`.
3. Pestaña **Canvas**: añade las visualizaciones sugeridas en la tabla anterior. Separa las páginas o secciones
   «E-commerce» y «Automobiles» para que no parezca que las fuentes se combinan.
4. La identidad que consulta necesita `SELECT` sobre las tablas Gold. `proceso/04_grants.py` lo concede a `grant_principal` (`retail_etl_readers`).
5. **Publish**. Revisa si el dashboard se publica con las credenciales del autor o con las del lector, y que los lectores sean
   miembros de `retail_etl_readers`.
6. Opcional: exporta la definición del dashboard (menú ⋮ → Export) y guárdala aquí, **solo después de revisar que no contenga
   identificadores del workspace, URLs ni correos**.

La herramienta de visualización la fija el enunciado. El repositorio de referencia usaba Power BI (`.pbix`); si el PDF exige
Power BI, estas mismas consultas sirven como origen.

## Capturas que hay que guardar

Guárdalas en esta carpeta. Están pendientes porque todavía no hay un dashboard real.

| Archivo sugerido | Contenido | Estado |
|---|---|---|
| `DASHBOARD_ECOMMERCE.png` | Página E-commerce: serie mensual, heatmap por segmento y contadores | Pendiente |
| `DASHBOARD_AUTOMOBILES.png` | Página Automobiles: precio por marca, carrocería × combustible y contadores | Pendiente |
| `DASHBOARD_DATASETS.png` | Pestaña Data con los 6 datasets apuntando a `workspace.<esquema_gold>` | Pendiente |

Antes de añadir una captura al repositorio público, **oculta** la URL del workspace, los correos, nombres y avatares de usuarios,
los identificadores de cuenta o workspace y cualquier dato que no haga falta para la evidencia.
