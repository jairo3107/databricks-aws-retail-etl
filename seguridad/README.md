# Seguridad

## Modelo de acceso: dos capas separadas

### 1. Permisos de ejecución (identidad del job)

Son los que necesita la identidad que despliega y ejecuta el job (el service principal o el usuario del PAT) para **leer RAW y
escribir las tablas**. Los concede un admin u owner **fuera del job** ([PrepAmb/prerrequisitos_admin.sql](../PrepAmb/prerrequisitos_admin.sql), sección [ADMIN]).
El job no se los concede a sí mismo ni intenta elevarse.

| Objeto | Privilegios mínimos | Quién |
|---|---|---|
| Catálogo `workspace` | `USE CATALOG`, `CREATE SCHEMA` | Admin u owner (innecesario si la identidad es owner) |
| External Location (raíz del bucket) | `READ FILES`, `CREATE EXTERNAL TABLE` | Admin u owner |
| Esquemas `bronze/silver/gold` y `dev_*` | Owner si los crea `00_prep_amb`; si los creó otro: `USE SCHEMA`, `CREATE TABLE`, `MODIFY`, `SELECT` | Automático, o admin u owner |
| Opcional: catálogo | `MANAGE`, solo para que `04_grants` pueda conceder `USE CATALOG` | Admin u owner |

### 2. Permisos de consumo (GRANT finales sobre Gold)

Los aplica **solo** la última tarea del job, `Grants` ([`proceso/04_grants.py`](../proceso/04_grants.py)), y **solo** a `grant_principal`.
`scripts/validar_repo.py` comprueba que ese notebook no concede nada más.

| Objeto | Privilegio |
|---|---|
| Catálogo | `USE CATALOG` |
| Esquema Gold del entorno (`gold` o `dev_gold`) | `USE SCHEMA` |
| Cada tabla Gold de `comun.TABLAS["gold"]` | `SELECT` |

`grant_principal` **no** recibe nada sobre Bronze ni Silver, ningún privilegio de escritura y nada sobre la External Location.
Las dos capas no se mezclan: el job nunca concede permisos de ejecución, y `PrepAmb/` no concede permisos de consumo.

## Acceso al almacenamiento: qué está restringido y qué no

- La External Location cubre la **raíz** del bucket y se probó con **lectura, escritura y borrado**. **No hay ninguna restricción
  técnica de solo lectura sobre `raw/`**: una identidad con `WRITE FILES` (o owner) en la External Location puede escribir y
  borrar en cualquier ruta del bucket, también en `raw/` y en `lakehouse/prod/`.
- Lo que sí se garantiza **en el código del pipeline**:
  - los notebooks leen RAW solo con `spark.read` y `dbutils.fs.ls`;
  - escriben únicamente mediante `comun.escribir_tabla_externa` hacia `comun.ruta_tabla` (`lakehouse/<entorno>/…`);
  - `comun.validar_aislamiento` rechaza que `lakehouse_root` y `raw_root` se solapen;
  - en `proceso/` no hay `dbutils.fs.rm`, `DROP`, `TRUNCATE` ni `DELETE`.
  `scripts/validar_repo.py` lo comprueba en el CI.
- Endurecimiento opcional, **no aplicado** (requiere cambios de admin en AWS/UC): una External Location separada para `raw/`,
  en la que la identidad del job tenga solo `READ FILES`, y otra para `lakehouse/`. No se ha hecho porque la configuración
  cloud existente no debe reconstruirse.

## Principal lector (`grant_principal`)

Unity Catalog solo concede acceso a datos a **grupos de cuenta**, **usuarios** y **service principals**.
Los **grupos locales del workspace** (origen *Workspace* en Settings → Identity and access → Groups) **no sirven**.

| Grupo visto en el workspace | Origen | ¿Válido para `grant_principal`? |
|---|---|---|
| `admins` | System | **No**: grupo de sistema del workspace; además daría acceso indiscriminado |
| `users` | System | **No**: todos los usuarios del workspace |
| `users-clone-<fecha>-UTC` | Workspace | **No**: grupo local generado por Databricks; UC no lo admite |

Opciones, por orden de preferencia:

1. **Grupo de cuenta dedicado `retail_etl_readers`: valor recomendado.** Ya está creado y su origen confirmado es **`Account`**,
   así que es válido para los GRANT de UC. (Free Edition no tiene consola de cuenta, pero en un workspace con identity
   federation su admin puede crear grupos de cuenta desde Settings → Identity and access → Groups.)
2. **Service principal**, por su application ID (UUID). Es visible en Settings → Identity and access → Service principals.
3. **Usuario lector concreto**, por su correo. Solo se pasa como `--var grant_principal=…` o como variable
   `DATABRICKS_GRANT_PRINCIPAL` de GitHub. **Nunca se escribe en el repositorio.**

Salvaguardas en el código:
- `comun.validar_principal()` rechaza `admins`, `users`, `account users` y los nombres típicos de grupo local
  (`*-clone-AAAA-MM-DD-HHMM-UTC`, `* (workspace)`).
- Los correos se muestran enmascarados (`l***@dominio`) en la salida del job.
- `deploy-prod.yml` enmascara el principal y la identidad que despliega en los logs públicos de Actions.
- `scripts/validar_repo.py` hace fallar el CI si aparece una dirección de correo en el repositorio.

Lo que el job **no** puede verificar: el nombre de un grupo no dice si es de cuenta o local. Si es local, el `GRANT`
falla y la tarea `Grants` termina con error, indicando que hay que revisar el origen del grupo.

## Aislamiento dev/prod (Free Edition: un solo workspace)

No hay dos workspaces físicos. La separación es lógica y la hace cumplir `comun.validar_aislamiento()` en cada notebook:
en `entorno=dev` solo se aceptan esquemas `dev_*` y rutas `lakehouse/dev/`; en `entorno=prod`, esquemas sin `dev_` y rutas `lakehouse/prod/`.
`entorno` sale de `${bundle.target}` y no es una variable sobrescribible. Ambos entornos comparten el catálogo y la External Location,
así que una identidad con permisos en prod también los tiene técnicamente en dev, y al revés.

## Única implementación

Los GRANT a consumidores se aplican **solo** desde [`proceso/04_grants.py`](../proceso/04_grants.py), la tarea `Grants` del job.
Las tablas se toman del inventario `TABLAS` de [`proceso/comun.py`](../proceso/comun.py); no hay una lista SQL paralela
que pueda quedar desactualizada. Para verificar, usa [verificar_permisos.sql](verificar_permisos.sql), que es de solo lectura.
Para revertir, usa [`reversion/01_revoke.py`](../reversion/01_revoke.py).

## Datos personales

El workspace y el proyecto pertenecen a otra persona. El repositorio no contiene nombres, correos ni otros datos
personales, y el CI lo comprueba en el caso de los correos. Las capturas de `evidencias/` deben ocultarlos (ver `evidencias/README.md`).

## Secretos

- En el repositorio no hay host, token, client secret, ARN ni External ID.
- GitHub Actions lee `DATABRICKS_HOST` y **un único** método de autenticación de los **secrets del environment `prod`**:
  OAuth M2M (`DATABRICKS_CLIENT_ID` + `DATABRICKS_CLIENT_SECRET`, preferido) o, como alternativa, un PAT (`DATABRICKS_TOKEN`).
  Ver [docs/configuracion_pendiente.md](../docs/configuracion_pendiente.md#autenticación-de-github-actions-no-verificada-todavía).
- Las acciones de GitHub están fijadas a SHA de commit y el CLI a la versión 1.19.0.
- `.gitignore` excluye `.databrickscfg`, `.env*`, `.aws/`, `*.pem` y `.databricks/`.
- El acceso a S3 se gobierna con Unity Catalog (Storage Credential + External Location). Los notebooks no usan claves de AWS.
  Ese acceso no es de solo lectura (ver [Acceso al almacenamiento](#acceso-al-almacenamiento-qué-está-restringido-y-qué-no)).
