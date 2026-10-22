# Checklist de cumplimiento

> **El PDF del profesor manda.** Requisitos que se sabe que exige: Medallion, PySpark, al menos 2 fuentes, CI/CD, notebooks de
> producción en `proceso/` y la estructura de carpetas `datasets/`, `dashboard/`, `reversion/`, `.github/workflows/`,
> `seguridad/`, `PrepAmb/`, `proceso/`, `certificaciones/` y `evidencias/`. **Contrasta esta lista con el PDF antes de entregar.**
> Las diferencias conocidas con el enunciado están en [decisiones_y_pendientes.md](decisiones_y_pendientes.md).

Leyenda:
- `[x]` hecho y comprobado: en el workspace si la marca es **(W)**, en local si es **(L)**.
- `[~]` hecho, pero con la comprobación incompleta (se indica qué falta).
- `[ ]` pendiente o no ejecutado.

## 1. Infraestructura (comprobada por el propietario del workspace)
- [x] (W) Free Edition con cómputo serverless
- [x] (W) Bucket `databricks-retail-etl-2026-smart` y External Location sobre su raíz, con Read/List/Write/Delete correctos.
  **No** es de solo lectura: el código limita las escrituras a `lakehouse/` (ver [seguridad](../seguridad/README.md#acceso-al-almacenamiento-qué-está-restringido-y-qué-no))
- [x] (W) Lectura de los dos CSV de RAW desde el workspace: 1000 filas (E-commerce) y 205 (Automobiles)
- [x] (W) Escritura Delta y registro en Unity Catalog
- [x] (W) Catálogo `workspace` con los esquemas `bronze`, `silver` y `gold` creados
- [x] (W) Grupo `retail_etl_readers` con origen **Account**, elegido como `grant_principal`

## 2. Ejecución en Databricks
### Target dev (comprobado por el propietario del workspace)
- [x] (W) `databricks bundle validate -t dev --var="grant_principal=retail_etl_readers" --strict` → `Validation OK`
- [x] (W) `databricks bundle deploy -t dev`
- [x] (W) Run de `WF_DEV_ETL_RETAIL` (recurso `wf_prod_etl_retail`) → `TERMINATED SUCCESS`, con las 7 tareas terminadas sin errores reportados
- [x] (W) 8 tablas **Delta externas** en `workspace.dev_bronze`, `workspace.dev_silver` y `workspace.dev_gold`
- [x] (W) RAW en `raw_root/raw_path_*`: confirmado de forma indirecta, porque `00_prep_amb` y las dos tareas Extract terminaron bien
- [x] (W) Conteos de las 8 tablas comprobados. Valores esperados según las pruebas locales: 1000, 205, 1000, 205, 165, 15, 22 y 9.
  Falta guardar la captura (`evidencias/DEV_CONTEOS_TABLAS.png`)
- [ ] (W) Ruta exacta de cada tabla en `lakehouse/dev/<capa>/<tabla>` (`DESCRIBE DETAIL`), documentada como evidencia
- [x] (W) Concesiones a `retail_etl_readers` comprobadas: `USE CATALOG`, `USE SCHEMA` sobre `dev_gold` y `SELECT` sobre las 4 tablas Gold
- [ ] (W) Opcional: una consulta real de un miembro de `retail_etl_readers` sobre Gold

### Target prod
- [ ] (W) `bundle validate -t prod`, `deploy` y run de `WF_PROD_ETL_RETAIL`. **No se ha desplegado ni ejecutado**
- [ ] (W) Validación de permisos sobre `workspace.gold`

## 3. Arquitectura, datos y job
- [x] (L) Dos fuentes independientes, sin fusionarlas en ninguna capa
- [x] (L) RAW se lee con `spark.read` sobre una URI `s3://`, sin DBFS ni Volúmenes (`validar_repo.py`)
- [x] (L) Transformaciones de negocio con la API DataFrame de PySpark (`proceso/transformaciones.py`)
- [x] (L) Validaciones de conteos, tipos, nulos y conciliación Gold, en los notebooks y en `tests/`
- [x] (L) Escrituras solo a `lakehouse/` vía `comun.ruta_tabla`. En `proceso/` no hay borrado de archivos, DROP ni DELETE (`validar_repo.py`)
- [x] (L) Aislamiento dev/prod forzado en el código (`comun.validar_aislamiento`, con pruebas)
- [x] (L) Notebooks de producción solo en `proceso/`, en formato fuente Databricks
- [x] (L) Job: PrepAmb → Extract ×2 en paralelo → Transform ×2 → Load → Grants, sin schedule y serverless
- [x] (L) Los parámetros del job coinciden con los widgets de cada notebook (`validar_repo.py`)
- [x] (L) Bundle conforme al JSON Schema oficial del CLI v1.19.0 (offline)

## 4. Seguridad y reversión
- [x] (L) `PrepAmb/prerrequisitos_admin.sql` distingue las operaciones [ADMIN] de las del [JOB] y no es destructivo
- [x] (L) Permisos de ejecución (PrepAmb, manual) separados de los GRANT de consumo: `04_grants` solo concede
  `USE CATALOG`, `USE SCHEMA` y `SELECT` a `grant_principal`, y rechaza `admins`, `users` y grupos locales (`validar_repo.py`)
- [x] (L) `seguridad/` y `reversion/` quedan fuera del job
- [ ] (W) `reversion/01_revoke.py` y `reversion/02_drop_tablas.py` (con confirmación explícita, sin DROP de catálogo ni borrado de S3): no ejecutados
- [x] (L) Sin credenciales ni correos en los archivos publicables; principal e identidad enmascarados en los logs de Actions (`validar_repo.py`)

## 5. CI/CD
- [x] (L) `ci.yml` separado del despliegue: sin secretos, con acciones fijadas a SHA y los mismos comandos `uv` que en local.
  Su `git diff --check` se reprodujo en una copia temporal con commit: pasa gracias a `.gitattributes` (sin él, los CRLF de los CSV lo harían fallar)
- [x] (L) `deploy-prod.yml`: solo manual; validate → deploy → run en ese orden, y un fallo corta el resto
- [ ] GitHub Actions **nunca se ha ejecutado** (no hay remoto ni commits): falta un run verde de `CI (validación local)`
- [ ] (W) Elegir y configurar la autenticación de CI, OAuth M2M o PAT ([configuración](configuracion_pendiente.md#autenticación-de-github-actions-no-verificada-todavía))
- [ ] (W) Run verde de `Deploy PROD (manual)` con `deploy-and-run`

## 6. Entregables (estructura del PDF)
- [x] `datasets/` con los dos CSV de entrada
- [~] Procedencia documentada en [datasets/README.md](../datasets/README.md).
  - Automobiles: UCI, CC BY 4.0, verificado por contenido; falta el intermediario.
  - E-commerce: procedencia **confirmada**: descarga directa de Kaggle con SHA-256 idéntico. Licencia CC0 según la ficha de Kaggle,
    no verificada legalmente. Falta la captura de la ficha.
- [x] (L) Entorno local reproducible con `uv` (`pyproject.toml` + `uv.lock`)
- [x] (L) README con la arquitectura, los entornos, el estado y la ejecución
- [~] `dashboard/`: 6 consultas sobre Gold, probadas en local (`tests/test_dashboard_sql.py`), e instrucciones de montaje
  ([dashboard/README.md](../dashboard/README.md)). **El dashboard no está creado** y no hay capturas
- [~] `evidencias/`: checklist de capturas y consultas de solo lectura preparadas ([evidencias/README.md](../evidencias/README.md)).
  **Ninguna captura guardada**
- [~] `certificaciones/`: índice preparado ([certificaciones/README.md](../certificaciones/README.md)). **Ningún certificado aportado**;
  hay que confirmar con el PDF cuáles se exigen
- [x] (L) Diagramas de arquitectura, job y Medallion en Mermaid editable ([diagramas.md](diagramas.md)). `validar_repo.py` comprueba
  su coherencia con el job y las tablas; la sintaxis se revisó con el parser de Mermaid 11.4.1 en un entorno temporal
- [ ] Repositorio **público** en GitHub (no hay commits ni remoto)
- [x] (L) Código propio, sin copiar literalmente el repositorio de referencia

## 7. Por confirmar con el profesor o el equipo
- [ ] Si el IAM Role de AWS cubre el requisito «Managed Identity» del enunciado ([D1](decisiones_y_pendientes.md#d1-acceso-a-raw-managed-identity-enunciado-frente-a-iam-role-de-aws-implementación))
- [ ] Si los datasets E-commerce y Automobiles se aceptan frente al enunciado ([D2](decisiones_y_pendientes.md#d2-datasets-e-commerce-y-automobiles-frente-a-los-del-ejemplo))
- [ ] Redistribución de Automobiles: identificar el intermediario de la copia ([D3](decisiones_y_pendientes.md#d3-licencias-de-los-csv)).
  E-commerce ya tiene la procedencia confirmada
