# evidencias/

Carpeta de entrega **requerida**. Contiene las capturas de ejecuciones **reales**. Ahora mismo **no hay ninguna guardada**.
Varias comprobaciones ya se hicieron en Databricks (ver la columna «Hecho comprobado»), pero sin captura en el repositorio
todavía. Las consultas para reproducirlas están en [`consultas_evidencia.sql`](consultas_evidencia.sql) y
[`../seguridad/verificar_permisos.sql`](../seguridad/verificar_permisos.sql), y todas son de solo lectura.

## Checklist de capturas

Marca la casilla solo cuando el archivo `.png` esté guardado en esta carpeta y revisado según las reglas de privacidad.

### Infraestructura

| ✓ | Archivo sugerido | Qué debe mostrar | Hecho comprobado |
|---|---|---|---|
| [ ] | `S3_BUCKET_RAW.png` | Bucket `databricks-retail-etl-2026-smart` con `raw/ecommerce/` y `raw/automobiles/` | Sí (lectura de RAW) |
| [ ] | `UC_EXTERNAL_LOCATION.png` | External Location sobre la raíz del bucket y su prueba de conexión | Sí |

### Target dev

| ✓ | Archivo sugerido | Qué debe mostrar | Hecho comprobado |
|---|---|---|---|
| [ ] | `DEV_BUNDLE_VALIDATE.png` | Salida de `databricks bundle validate -t dev … --strict` con `Validation OK` | Sí |
| [ ] | `DEV_JOB_RUN_SUCCESS.png` | Run de `WF_DEV_ETL_RETAIL` con el DAG de 7 tareas en verde y `Succeeded` | Sí |
| [ ] | `DEV_CONTEOS_TABLAS.png` | Resultado de la consulta E1: conteo de las 8 tablas | Sí (conteos comprobados) |
| [ ] | `DEV_TIPO_TABLAS.png` | Resultado de E2: las 8 tablas con `table_type = EXTERNAL` | Sí (8 tablas Delta externas) |
| [ ] | `DEV_UBICACIONES_DELTA.png` | `DESCRIBE DETAIL` (E3): `format = delta` y `location` en `lakehouse/dev/<capa>/<tabla>` | Ruta exacta sin documentar |
| [ ] | `S3_LAKEHOUSE_DEV.png` | Prefijos `lakehouse/dev/{bronze,silver,gold}/` en S3 | No |
| [ ] | `DEV_GRANTS_GOLD.png` | `SHOW GRANTS` de `retail_etl_readers`: `USE CATALOG`, `USE SCHEMA` sobre `dev_gold` y `SELECT` sobre las 4 tablas Gold | Sí (concesiones comprobadas) |
| [ ] | `UC_GRUPO_READERS.png` | Grupo `retail_etl_readers` con origen **Account**, sin la lista de miembros | Sí |

### Dashboard (ver [`../dashboard/README.md`](../dashboard/README.md))

| ✓ | Archivo sugerido | Qué debe mostrar | Hecho comprobado |
|---|---|---|---|
| [ ] | `../dashboard/DASHBOARD_ECOMMERCE.png` y `../dashboard/DASHBOARD_AUTOMOBILES.png` | El dashboard real sobre Gold | **No: el dashboard no existe todavía** |

### Cuando ocurran (todavía no han ocurrido)

| ✓ | Archivo sugerido | Qué debe mostrar | Hecho comprobado |
|---|---|---|---|
| [ ] | `GITHUB_ACTION_CI.png` | Ejecución verde de `CI (validación local)` | **No ejecutado** |
| [ ] | `GITHUB_ACTION_DEPLOY.png` | Ejecución verde de `Deploy PROD (manual)` con `deploy-and-run` | **No ejecutado** |
| [ ] | `PROD_JOB_RUN_SUCCESS.png` | Run de `WF_PROD_ETL_RETAIL` con las 7 tareas en verde | **No ejecutado** |
| [ ] | `PROD_CONTEOS_TABLAS.png`, `PROD_UBICACIONES_DELTA.png`, `PROD_GRANTS_GOLD.png` | Como los de dev, sobre `bronze/silver/gold` y `lakehouse/prod/` | **No ejecutado** |

## Privacidad (repositorio público)

Antes de guardar cualquier captura, **recórtala u oculta**:
- correos, nombres y avatares de usuarios, incluidos el propietario del workspace y los miembros del grupo;
- la URL o el ID del workspace, los ID de cuenta de AWS o Databricks, ARN completos, External IDs, ID de jobs y runs, y application IDs;
- tokens, client secrets y cualquier valor de los secrets de GitHub;
- las rutas de usuario (`/Workspace/Users/<correo>/…`) que aparecen en el bundle y en los jobs.

Deja visible solo lo que prueba la evidencia: nombres de tablas, esquemas, estados, conteos y privilegios.
