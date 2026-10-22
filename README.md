# databricks-aws-retail-etl

Pipeline ETL académico de extremo a extremo con **arquitectura Medallion (Bronze → Silver → Gold)** sobre
**Databricks + Unity Catalog en AWS**. RAW está en **Amazon S3** y se lee directamente con una External Location.
Las transformaciones usan la **API DataFrame de PySpark**, las tablas son Delta y el despliegue usa **Declarative Automation Bundles**.
La ejecución de producción está preparada para lanzarse a mano desde **GitHub Actions**, pero todavía no se ha ejecutado.

El flujo sigue el del repositorio de referencia del curso
([Enrykiel/databricks_project](https://github.com/Enrykiel/databricks_project)), adaptado a AWS:

| Referencia (Azure) | Este proyecto (AWS) |
|---|---|
| ADLS Gen2, contenedor `raw` | Bucket `databricks-retail-etl-2026-smart`, prefijo `raw/` |
| Access Connector (Managed Identity) | IAM Role → Storage Credential → External Location (ya existentes). No es el mismo mecanismo; ver [D1](docs/decisiones_y_pendientes.md#d1-acceso-a-raw-managed-identity-enunciado-frente-a-iam-role-de-aws-implementación) |
| Notebooks exportados de un workspace origen | Notebooks versionados en Git y sincronizados por el bundle |
| Borrar y recrear el job con `curl` | `databricks bundle deploy`, que actualiza el job y conserva su historial |
| Despliegue en cada push a `main` | Despliegue solo manual (`workflow_dispatch`) en un environment protegido |
| Acciones de GitHub por tag mutable | Acciones fijadas a SHA de commit |
| Cluster buscado por nombre, catálogo `catalog_dev` fijo en prod | Serverless y parámetros por variable |

## Estado del proyecto (2026-10-21)

### Comprobado en el workspace de Databricks

Lo ha confirmado el propietario del workspace:

- Free Edition con cómputo serverless.
- External Location sobre la raíz del bucket, con lectura, escritura y borrado probados.
- Lectura de los dos CSV de RAW desde S3: 1000 y 205 filas.
- Escritura Delta y registro en Unity Catalog.
- Catálogo `workspace`, y grupo `retail_etl_readers` con origen Account.
- **Target dev:**
  - `databricks bundle validate -t dev --var="grant_principal=retail_etl_readers" --strict` → `Validation OK`;
  - `databricks bundle deploy -t dev`;
  - run del job `WF_DEV_ETL_RETAIL` (recurso `wf_prod_etl_retail`) → `TERMINATED SUCCESS`, con **las 7 tareas** terminadas sin errores reportados;
  - **8 tablas Delta externas** en `workspace.dev_bronze`, `workspace.dev_silver` y `workspace.dev_gold`, con los **conteos de las 8 tablas comprobados**;
  - concesiones a `retail_etl_readers` comprobadas: `USE CATALOG`, `USE SCHEMA` sobre `dev_gold` y `SELECT` sobre las 4 tablas Gold.

### Validado únicamente en local (sin Databricks)

- Pruebas PySpark sobre los CSV de `datasets/`, incluidos los conteos 1000/205 y la conciliación Gold con Silver.
- Ejecución de los 7 notebooks con un `dbutils` simulado y el catálogo local de Spark. Se hizo con un arnés temporal que **no está en
  el repositorio**, así que no se puede reproducir desde aquí; las pruebas reproducibles son las de `tests/`.
- Consultas del dashboard (`dashboard/sql/`), ejecutadas contra las tablas Gold generadas en local (`tests/test_dashboard_sql.py`).
- Sintaxis de los diagramas Mermaid (`docs/diagramas.md`), revisada con el parser oficial de Mermaid 11.4.1 en un entorno temporal.
- Bundle frente al JSON Schema oficial del CLI v1.19.0.
- Consistencia de bundle, job, notebooks, workflows, privacidad y enlaces con `scripts/validar_repo.py`.

### Pendiente (acción manual en Databricks)

- **Dashboard:** las consultas y las instrucciones están listas ([dashboard/README.md](dashboard/README.md)), pero el dashboard **no existe todavía**.
- **Evidencias:** no hay ninguna captura guardada. La checklist y las consultas están en [evidencias/README.md](evidencias/README.md).
- Ruta exacta de cada tabla en `lakehouse/dev/…` (`DESCRIBE DETAIL`), documentada como evidencia.
- Opcional: una consulta real de un miembro de `retail_etl_readers` sobre Gold.

### No desplegado o no ejecutado

- **Producción** (`-t prod`, `WF_PROD_ETL_RETAIL`): no desplegada ni ejecutada.
- **GitHub Actions** (`CI (validación local)` y `Deploy PROD (manual)`): nunca ejecutado. No hay remoto ni commits.

Las cuestiones abiertas están en [docs/decisiones_y_pendientes.md](docs/decisiones_y_pendientes.md):
- Managed Identity frente al IAM Role;
- la aceptación de los datasets;
- el intermediario de la copia de Automobiles.

La procedencia de E-commerce ya está confirmada: descarga de Kaggle con SHA-256 idéntico.

## Fuentes de datos

| Fuente | Archivo | Filas × columnas | Particularidades |
|---|---|---|---|
| E-commerce | `Ecommerce_Sales_Prediction_Dataset.csv` | 1000 × 7 | Fecha `dd-MM-yyyy`; unidad de `Discount` sin verificar |
| Automobiles | `Automobile_data.csv` | 205 × 26 | Nulos marcados con `?`; sin clave natural |

Las dos fuentes **no comparten columnas** y no se combinan en ninguna capa.
- Esquemas: [docs/esquemas_detectados.md](docs/esquemas_detectados.md).
- Procedencia, atribución y estado de las licencias: [datasets/README.md](datasets/README.md).
  - E-commerce: Kaggle (Nevil Dhinoja), procedencia confirmada por SHA-256; CC0 según la ficha.
  - Automobiles: UCI (Schlimmer, 1985), CC BY 4.0, con el intermediario pendiente.

## Arquitectura

Diagramas editables (Mermaid) de la arquitectura, el job y el flujo Medallion: [docs/diagramas.md](docs/diagramas.md).

```
s3://databricks-retail-etl-2026-smart/
├── raw/                                   ← RAW (lectura directa, External Location de UC)
│   ├── ecommerce/Ecommerce_Sales_Prediction_Dataset.csv
│   └── automobiles/Automobile_data.csv
└── lakehouse/                             ← tablas Delta externas registradas en UC
    ├── prod/                              ← esquemas bronze | silver | gold
    │   ├── bronze/{ecommerce_ventas, automobiles_specs}
    │   ├── silver/{ecommerce_ventas, automobiles_specs}
    │   └── gold/{ecommerce_ventas_mensuales_categoria, ecommerce_ventas_segmento_categoria,
    │             automobiles_resumen_marca, automobiles_resumen_carroceria_combustible}
    └── dev/                               ← esquemas dev_bronze | dev_silver | dev_gold (misma estructura)
```

### Entornos: un solo workspace (Free Edition)

`dev` y `prod` son **una separación lógica dentro del mismo workspace y del mismo catálogo**, no dos workspaces físicos.
Cada target usa sus propios esquemas, rutas en `lakehouse/` y nombre de job. RAW es compartido y los notebooks solo lo leen.

Cada notebook valida el aislamiento con `comun.validar_aislamiento`:
- los notebooks de dev se niegan a escribir en esquemas o rutas de prod;
- ninguno escribe dentro de `raw/`.

Es una garantía **del código, no del almacenamiento**, porque la External Location cubre la raíz del bucket con lectura,
escritura y borrado. Ver [seguridad/README.md](seguridad/README.md#acceso-al-almacenamiento-qué-está-restringido-y-qué-no) y
[docs/configuracion_pendiente.md](docs/configuracion_pendiente.md#entornos-separación-lógica-en-un-solo-workspace).

### Job

`WF_DEV_ETL_RETAIL` / `WF_PROD_ETL_RETAIL`, definido en [resources/wf_prod_etl_retail.job.yml](resources/wf_prod_etl_retail.job.yml):

```
PrepAmb ─┬─ Extract_ecommerce ─── Transform_ecommerce ───┬─ Load ── Grants
         └─ Extract_automobiles ─ Transform_automobiles ─┘
```

| Capa | Notebook | Qué hace |
|---|---|---|
| PrepAmb | `proceso/00_prep_amb.py` | Verifica el catálogo (no lo crea), crea los esquemas del entorno si faltan y comprueba RAW en S3, la separación RAW/lakehouse y el aislamiento |
| Bronze | `proceso/01_extract_*.py` | CSV → Delta, todo `string`, con auditoría (`_archivo_origen`, `_fecha_ingesta`, `_ejecucion_id`) |
| Silver | `proceso/02_transform_*.py` | Tipos explícitos, `?` → nulo y validaciones **antes** de escribir |
| Gold | `proceso/03_load_gold.py` | Agregados por fuente, conciliados con Silver |
| Grants | `proceso/04_grants.py` | `USE CATALOG`, `USE SCHEMA` y `SELECT` sobre Gold, solo para `grant_principal`. Nunca `admins` ni `users` ([detalle](seguridad/README.md#principal-lector-grant_principal)) |

La lógica de negocio está en `proceso/transformaciones.py` (funciones puras de DataFrame) y las utilidades en `proceso/comun.py`.
Los parámetros llegan a los notebooks como **parámetros del job → widgets** (`dbutils.widgets.get`); las variables del bundle
no existen en Python. La ejecución normal **no** hace DROP ni borra rutas: las escrituras sobrescriben las tablas como una
nueva versión Delta y conservan el historial.

## Estructura del repositorio

```
.github/workflows/  ci.yml (validación local, sin secretos) · deploy-prod.yml (manual)
PrepAmb/            prerrequisitos_admin.sql: lo que hace un admin una sola vez (documental)
proceso/            notebooks de producción + comun.py + transformaciones.py
seguridad/          modelo de permisos + verificar_permisos.sql (solo consultas)
reversion/          01_revoke.py · 02_drop_tablas.py (manuales, con confirmación)
datasets/           CSV de entrada (requeridos por el enunciado) + README de procedencia
docs/               esquemas, checklist, configuración, decisiones y pendientes, diagramas (Mermaid)
resources/          definición del job
tests/              pruebas PySpark (CSV reales), aislamiento, principal y validador
scripts/            perfilar_csv.py · validar_repo.py
dashboard/          sql/ (6 consultas sobre Gold) + README para montar el dashboard (aún no creado)
evidencias/         checklist de capturas reales + consultas_evidencia.sql (ninguna captura todavía)
certificaciones/    índice de certificados (ninguno aportado todavía)
databricks.yml · pyproject.toml · uv.lock · .python-version · .gitattributes (CSV sin normalizar ni comprobación de espacios)
```

## Configuración

La lista completa está en [docs/configuracion_pendiente.md](docs/configuracion_pendiente.md).

- `grant_principal` no tiene valor por defecto y hay que pasarlo siempre (en dev se usó `retail_etl_readers`).
- Para producción faltan los secrets del environment `prod` de GitHub (host y autenticación, OAuth M2M o PAT) y la variable
  `DATABRICKS_GRANT_PRINCIPAL`.
- Los secretos nunca se versionan.

## Validación local

Requisitos:
- [uv](https://docs.astral.sh/uv/), que instala Python 3.12 y las dependencias exactas de `uv.lock`;
- **Java 17**, para las pruebas con Spark;
- el Databricks CLI, solo para el JSON Schema del bundle.

Nada de esto contacta con Databricks ni con AWS.

```bash
uv sync --locked                                          # entorno .venv a partir de uv.lock
uv run python scripts/validar_repo.py                     # YAML estricto, bundle, job, workflows, privacidad, enlaces (sin Spark)
databricks bundle schema > /tmp/bundle_schema.json        # offline, sin credenciales
uv run python scripts/validar_repo.py --schema /tmp/bundle_schema.json
uv run python -m py_compile proceso/*.py reversion/*.py scripts/*.py tests/*.py
PYFLAKES_BUILTINS=spark,dbutils,display uv run python -m pyflakes proceso reversion scripts tests
uv run pytest -q                                          # requiere Java 17 (JAVA_HOME o java en PATH)
uv run pytest -q tests/test_comun.py tests/test_validar_repo.py   # subconjunto sin Spark ni Java
```

`.github/workflows/ci.yml` ejecuta `uv sync --locked`, `py_compile`, `pyflakes`, `validar_repo.py --schema` y `pytest -q`,
igual que en este bloque. Además ejecuta `git diff --check "$(git hash-object -t tree /dev/null)" HEAD`, que necesita al menos
un commit. Antes del primer commit, el equivalente local es `git diff --no-index --check /dev/null <archivo>` para cada archivo nuevo.
Los CSV tienen finales de línea CRLF; `.gitattributes` los excluye de esa comprobación y evita que se normalicen, de modo que
sus SHA-256 se conservan.

## Despliegue

1. Revisa [PrepAmb/prerrequisitos_admin.sql](PrepAmb/prerrequisitos_admin.sql): las comprobaciones [ADMIN] y los privilegios, si hacen falta.
2. Los CSV deben estar en `s3://databricks-retail-etl-2026-smart/raw/{ecommerce,automobiles}/`.
3. **dev** se despliega desde el CLI local (ya ejecutado una vez con éxito):
   ```bash
   databricks bundle validate -t dev --profile <perfil> --var="grant_principal=retail_etl_readers" --strict
   databricks bundle deploy   -t dev --profile <perfil> --var="grant_principal=retail_etl_readers"
   databricks bundle run      -t dev --profile <perfil> --var="grant_principal=retail_etl_readers" wf_prod_etl_retail
   ```
4. **prod** (no ejecutado): configura el environment `prod` en GitHub. Después, Actions → **Deploy PROD (manual)** → `validate` y,
   por último, `deploy-and-run`.

## Cumplimiento, pendientes y decisiones

- [docs/checklist_cumplimiento.md](docs/checklist_cumplimiento.md): requisitos y su estado (local, workspace o pendiente).
- [docs/decisiones_y_pendientes.md](docs/decisiones_y_pendientes.md): diferencias con el enunciado que necesitan confirmación humana.
- [seguridad/README.md](seguridad/README.md): modelo de permisos, aislamiento, datos personales y secretos.
