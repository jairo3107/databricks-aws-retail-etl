# Configuración: confirmada y pendiente

Ningún valor de esta página es inventado. Las variables del bundle se definen en [`databricks.yml`](../databricks.yml)
y se sobrescriben con `--var nombre=valor` o `BUNDLE_VAR_nombre`. Los secretos van **solo** en el environment `prod` de GitHub.
El estado de ejecución (qué se ha probado y dónde) está en el [README](../README.md#estado-del-proyecto-2026-10-21) y en la
[checklist](checklist_cumplimiento.md).

## Valores confirmados

| Elemento | Valor |
|---|---|
| Workspace | Databricks **Free Edition** en AWS: un único workspace, con cómputo **serverless** |
| Bucket S3 | `databricks-retail-etl-2026-smart` |
| External Location | Sobre la **raíz** del bucket, con Read, List, Write y **Delete** probados. El almacenamiento **no** está restringido a solo lectura en ninguna ruta, tampoco en `raw/` |
| Catálogo | `workspace` (default de la variable `catalog`) |
| `grant_principal` | `retail_etl_readers`, grupo con origen **Account** (usado en dev). La variable **no tiene default**: hay que pasarla siempre |

## Entornos (separación lógica en un solo workspace)

| | dev (`-t dev`, por defecto) | prod (`-t prod`) |
|---|---|---|
| Job | `[dev <usuario>] WF_DEV_ETL_RETAIL` | `WF_PROD_ETL_RETAIL` |
| Esquemas | `dev_bronze`, `dev_silver`, `dev_gold` (existen tras el run de dev) | `bronze`, `silver`, `gold` (creados a mano) |
| Tablas (Delta externas) | `s3://databricks-retail-etl-2026-smart/lakehouse/dev/<capa>/<tabla>` | `…/lakehouse/prod/<capa>/<tabla>` |
| RAW (compartido; los notebooks solo lo leen) | `s3://databricks-retail-etl-2026-smart/raw/` | igual |
| Despliegue | CLI local con un perfil de `~/.databrickscfg` | GitHub Actions (manual) |

**No son dos workspaces físicos.** Comparten el catálogo, la External Location y los permisos, y el aislamiento depende del código:
- `comun.validar_aislamiento()` hace fallar cualquier notebook que, con `entorno=dev`, reciba un esquema sin `dev_` o una ruta fuera
  de `lakehouse/dev`, y lo mismo a la inversa en prod.
- Tampoco admite que `lakehouse_root` y `raw_root` se solapen.
- `entorno` sale de `${bundle.target}` y no se puede sobrescribir con `--var`.

Una identidad con acceso a la External Location podría escribir o borrar en cualquier ruta del bucket desde fuera de estos
notebooks (ver [seguridad](../seguridad/README.md#acceso-al-almacenamiento-qué-está-restringido-y-qué-no)).

## Valores por defecto del bundle (decisiones de diseño, cambiables)

| Variable | Valor | Nota |
|---|---|---|
| `raw_root` | `s3://databricks-retail-etl-2026-smart/raw` | En dev funcionó: `00_prep_amb` y las tareas Extract leyeron de esta ruta |
| `raw_path_ecommerce` | `ecommerce/Ecommerce_Sales_Prediction_Dataset.csv` | Relativa a `raw_root` |
| `raw_path_automobiles` | `automobiles/Automobile_data.csv` | Relativa a `raw_root` |
| `semantica_discount` | `desconocida` | Ver [esquemas_detectados.md](esquemas_detectados.md#evidencia-sobre-discount) |

## Pendiente para producción

| Elemento | Descripción | Dónde |
|---|---|---|
| Host del workspace | URL `https://<deployment>.cloud.databricks.com` | Secret `DATABRICKS_HOST` del environment `prod` |
| Autenticación de CI | Ver la sección siguiente | Secrets del environment `prod` |
| `grant_principal` en CI | `retail_etl_readers` | Variable `DATABRICKS_GRANT_PRINCIPAL` del environment `prod` |
| Privilegios de la identidad de CI | No hacen falta si esa identidad es la owner del catálogo y de la External Location | [PrepAmb/prerrequisitos_admin.sql](../PrepAmb/prerrequisitos_admin.sql) |

## Autenticación de GitHub Actions (no verificada todavía)

El CLI rechaza tener configurado más de un método a la vez ("more than one authorization method configured", comprobado en el
binario v1.19.0). Por eso `deploy-prod.yml` solo expone el PAT cuando no hay OAuth M2M.

| Opción | Secrets | Requisitos de administración | Estado en Free Edition |
|---|---|---|---|
| **A. OAuth M2M** (preferida) | `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET` | Ser admin del workspace para crear el service principal y generarle un secreto OAuth. El SP necesita los privilegios de UC de PrepAmb y acceso al workspace | **Por verificar**: comprobar en Settings → Identity and access → Service principals si se puede crear un SP y generarle un secreto |
| **B. PAT** (alternativa) | `DATABRICKS_TOKEN` | Tener habilitados los tokens personales. El job se ejecuta como el usuario dueño del token | Por verificar: Settings → Developer → Access tokens |
| C. OIDC federation de GitHub | ninguno de larga duración | Política de federación a nivel de cuenta (account console) | Probablemente no disponible sin account console. Descartada por ahora |

Con la opción B, el job de prod se ejecuta como el usuario. Hay que rotar el PAT y darle la vigencia más corta posible.

## Requisitos de runtime

- Los notebooks importan `comun.py` y `transformaciones.py` desde su propia carpeta. Funcionó en **serverless** en el run de dev.
- No se usan `.cache()`, `input_file_name()`, configuraciones de Spark ni clusters (compatible con Free Edition).
