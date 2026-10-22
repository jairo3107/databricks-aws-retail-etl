# datasets/

Carpeta **requerida** por el enunciado. Contiene los CSV de entrada del proyecto, igual que el ejemplo del profesor.
El pipeline **no** los lee desde aquí: se suben a `s3://databricks-retail-etl-2026-smart/raw/` y se leen directamente desde S3.
Aquí sirven para las pruebas locales (`tests/`) y como referencia del esquema ([docs/esquemas_detectados.md](../docs/esquemas_detectados.md)).

| Archivo | Filas × columnas | Bytes | SHA-256 |
|---|---|---|---|
| `automobiles/Automobile_data.csv` | 205 × 26 | 25 070 | `2c7c43bd00c53112d7766dd825b986b57aa15a0450815ef568d60216fbe5e587` |
| `ecommerce/Ecommerce_Sales_Prediction_Dataset.csv` | 1000 × 7 | 52 879 | `db6b4ebe74af038cb0671b2cadb4f0ffcd69311e6ec999d1ee0265e4b51d7162` |

## Fuentes, atribución y estado de las licencias

Actualizado el 2026-10-21. Estas licencias son las que **declaran las fuentes**, no el resultado de una revisión legal independiente.

| Archivo | Procedencia | Licencia declarada por la fuente | Pendiente |
|---|---|---|---|
| E-commerce | **Confirmada** (descarga de Kaggle y SHA-256 idéntico) | CC0: Public Domain (ficha de Kaggle) | Captura de la ficha con la licencia |
| Automobiles | Obra de UCI **verificada por contenido**; **intermediario sin identificar** | CC BY 4.0 (página de UCI), que exige atribución | Identificar el intermediario y que no añada condiciones propias |

### Automobiles: `Automobile_data.csv`

| | |
|---|---|
| Obra original | *Automobile* (1985 Ward's Automotive Yearbook), UCI Machine Learning Repository. Creador: Jeffrey Schlimmer. [archive.ics.uci.edu/dataset/10/automobile](https://archive.ics.uci.edu/dataset/10/automobile) |
| Licencia de la obra original | **CC BY 4.0**, según la página de UCI ("This dataset is licensed under a Creative Commons Attribution 4.0 International (CC BY 4.0) license") |
| Relación con esta copia | **Verificada por contenido**: las 205 filas tienen los mismos valores que `imports-85.data` de UCI, campo a campo. Diferencias: esta copia añade una fila de cabecera y escribe los números sin ceros finales (`88.60` → `88.6`, `9.00` → `9`) |
| Intermediario | **No identificado.** El nombre `Automobile_data.csv` corresponde a redistribuciones de terceros (p. ej. en Kaggle), no a UCI |
| Estado | CC BY 4.0 permite redistribuir con atribución e indicando los cambios. **Pendiente:** confirmar el intermediario y que no añade condiciones propias |

Atribución requerida (CC BY 4.0):

> Schlimmer, J. (1985). *Automobile* [Dataset]. UCI Machine Learning Repository. <https://doi.org/10.24432/C5B01C>.
> Licencia CC BY 4.0 (<https://creativecommons.org/licenses/by/4.0/>). Cambios en esta copia: se añadió una fila de cabecera
> y los valores numéricos aparecen sin ceros finales. El proyecto no modifica el archivo.

### E-commerce: `Ecommerce_Sales_Prediction_Dataset.csv`

| | |
|---|---|
| Fuente | *E-commerce Sales Prediction Dataset*, de Nevil Dhinoja, en Kaggle: [kaggle.com/datasets/nevildhinoja/e-commerce-sales-prediction-dataset](https://www.kaggle.com/datasets/nevildhinoja/e-commerce-sales-prediction-dataset) |
| Procedencia | **Confirmada por descarga y coincidencia de SHA-256.** El propietario del proyecto descargó el CSV directamente de esa ficha de Kaggle y calculó su SHA-256 en Windows 11 con `Get-FileHash -Algorithm SHA256`. Obtuvo exactamente `db6b4ebe74af038cb0671b2cadb4f0ffcd69311e6ec999d1ee0265e4b51d7162`, el mismo hash que esta copia. Los metadatos públicos de Kaggle también coinciden en tamaño (52 879 bytes) y fecha de actualización (2024-12-14) |
| Licencia | **CC0: Public Domain, tal como la declara la ficha de Kaggle.** Se atribuye a esa fuente: es la declaración de quien publicó el dataset y **no** una verificación legal independiente de los derechos sobre los datos |
| Naturaleza | **No verificada.** Un espejo de terceros (Baselight, ya cerrado) describía el dataset como datos sintéticos de ventas, pero no se ha confirmado en la ficha de Kaggle |
| Pendiente | Guardar una captura de la ficha de Kaggle que muestre la licencia declarada, sin datos de la cuenta de quien descarga |

Atribución (CC0 no la exige; se incluye como referencia de la fuente):

> Dhinoja, N. (2024). *E-commerce Sales Prediction Dataset*. Kaggle. Licencia declarada en la fuente: CC0: Public Domain.

## Antes de publicar

1. ~~E-commerce: confirmar la fuente comparando el SHA-256.~~ **Hecho:** descarga de Kaggle con hash idéntico. Falta solo la captura de la licencia declarada.
2. Automobiles: el propietario identifica de dónde descargó la copia (la URL del intermediario) y comprueba que no añade condiciones a CC BY 4.0.
3. Si el intermediario de Automobiles no se puede identificar: decidir si se publica igualmente con la atribución a UCI (el enunciado
   exige `datasets/`) o se sustituye por el archivo original de UCI. Esa decisión es humana y no la toma este repositorio.
