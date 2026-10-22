# Esquemas detectados (inspección local, solo lectura)

Fecha de inspección: 2026-10-21. Herramienta: `python -I scripts/perfilar_csv.py datasets`, más comprobaciones puntuales.
Los archivos **no se modificaron**.

| Archivo | Bytes | SHA-256 |
|---|---|---|
| `datasets/automobiles/Automobile_data.csv` | 25 070 | `2c7c43bd00c53112d7766dd825b986b57aa15a0450815ef568d60216fbe5e587` |
| `datasets/ecommerce/Ecommerce_Sales_Prediction_Dataset.csv` | 52 879 | `db6b4ebe74af038cb0671b2cadb4f0ffcd69311e6ec999d1ee0265e4b51d7162` |

Formato común: ASCII sin BOM, separador `,`, cabecera en la primera línea, finales de línea `CRLF`, sin comillas,
sin filas con un número de columnas distinto y sin filas duplicadas exactas.

---

## 1. E-commerce: `Ecommerce_Sales_Prediction_Dataset.csv`

1000 filas de datos y 7 columnas. No hay valores vacíos ni marcadores de nulo.

| Columna | Tipo aparente | Nulos | Observaciones |
|---|---|---|---|
| `Date` | fecha `dd-MM-yyyy` | 0 | Va del 2023-01-01 al 2025-09-26. Hay 1000 fechas distintas y consecutivas (una fila por día). La primera parte llega a 31 y la segunda a 12, así que el formato es día-mes. |
| `Product_Category` | texto | 0 | 5 valores: Electronics (210), Fashion (190), Home Decor (190), Sports (206) y Toys (204). |
| `Price` | decimal | 0 | Va de 14.59 a 999.42. |
| `Discount` | decimal | 0 | Va de 0.01 a 49.92. **No se sabe la unidad (porcentaje o importe).** |
| `Customer_Segment` | texto | 0 | 3 valores: Occasional (339), Premium (316) y Regular (345). |
| `Marketing_Spend` | decimal | 0 | Va de 100.3 a 9995.62. |
| `Units_Sold` | entero | 0 | Va de 5 a 57. |

## 2. Automobiles: `Automobile_data.csv`

205 filas de datos y 26 columnas. **El marcador de nulo es `?`**, no la celda vacía (no hay celdas vacías).
Los nombres de columna llevan guiones (`fuel-type`), así que hay que renombrarlos a snake_case para Delta y Unity Catalog.

| Columna | Tipo aparente | `?` | Observaciones |
|---|---|---|---|
| `symboling` | entero | 0 | Valores de -2 a 3. |
| `normalized-losses` | entero | **41 (20 %)** | Va de 65 a 256. |
| `make` | texto | 0 | 22 marcas. Incluye la grafía `peugot` y `alfa-romero` tal como vienen en el origen. |
| `fuel-type` | texto | 0 | gas, diesel |
| `aspiration` | texto | 0 | std, turbo |
| `num-of-doors` | texto | 2 | two, four (número escrito en palabras) |
| `body-style` | texto | 0 | 5 valores |
| `drive-wheels` | texto | 0 | 4wd, fwd, rwd |
| `engine-location` | texto | 0 | front, rear |
| `wheel-base` | decimal | 0 | |
| `length` | decimal | 0 | |
| `width` | decimal | 0 | |
| `height` | decimal | 0 | |
| `curb-weight` | entero | 0 | |
| `engine-type` | texto | 0 | 7 valores |
| `num-of-cylinders` | texto | 0 | De two a twelve (número escrito en palabras) |
| `engine-size` | entero | 0 | |
| `fuel-system` | texto | 0 | 8 valores |
| `bore` | decimal | 4 | |
| `stroke` | decimal | 4 | |
| `compression-ratio` | decimal | 0 | Va de 7 a 23. |
| `horsepower` | entero | 2 | Va de 48 a 288. |
| `peak-rpm` | entero | 2 | |
| `city-mpg` | entero | 0 | |
| `highway-mpg` | entero | 0 | |
| `price` | entero | 4 | Va de 5118 a 45400. |

## 3. Hechos verificados y lo que NO se asume

- **No hay ninguna columna común entre las dos fuentes.** No se define ninguna relación ni join entre E-commerce y Automobiles; las dos se procesan como pipelines independientes hasta Gold.
- Automobiles **no tiene clave natural** (ninguna columna identifica cada fila de forma única). Si hace falta un ID, se genera en Silver y se documenta como clave técnica.
- En E-commerce, `Date` es única en este archivo. Eso no garantiza que sea una clave de negocio.
- No se infiere moneda para `Price` ni `price`, ni unidad para `Discount` o `Marketing_Spend`.
- Bronze: lectura con `header=true`, sin `inferSchema` (todo `string`) y con columnas de auditoría. En Automobiles los nombres
  se pasan a snake_case **ya en Bronze**, para no depender de comillas invertidas en SQL (mapeo 1:1 con
  `transformaciones.snake`). Los valores no se tocan (`?` se conserva).
- Silver: reglas de tipo explícitas en `proceso/transformaciones.py`: `?` → nulo en Automobiles y `dd-MM-yyyy` → `date` en E-commerce.

## Evidencia sobre `Discount`

Verificado en local (2026-10-21):

| Comprobación | Resultado |
|---|---|
| Rango | 0.01 – 49.92 (máximo 2 decimales) |
| Filas con `Discount > 100` | 0 |
| Filas con `Discount > Price` | **10** |

Si `Discount` fuera un importe absoluto, en 10 filas el precio neto saldría negativo. Eso **hace improbable** la
interpretación como importe, pero **no prueba** que sea un porcentaje. Por eso el pipeline usa `semantica_discount = desconocida`
y no calcula ningún precio neto. Solo se cambia cuando la fuente del dataset confirme la unidad.
