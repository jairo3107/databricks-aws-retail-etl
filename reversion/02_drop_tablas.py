# Databricks notebook source
# MAGIC %md
# MAGIC # Reversión 02 · DROP de las tablas del proyecto
# MAGIC
# MAGIC Requiere `entorno` (dev|prod), que valida que los esquemas y rutas sean los de ese entorno. **No forma parte del job.** Para ejecutarlo hay que escribir `SI` en `confirmar`.
# MAGIC
# MAGIC - Elimina el registro en Unity Catalog de las tablas Gold, Silver y Bronze, en ese orden.
# MAGIC - Las tablas son **externas**: `DROP TABLE` **no borra** los datos de `s3://…/lakehouse/`. Este notebook muestra
# MAGIC   las rutas para que su borrado, si se quiere, sea una decisión manual y aparte.
# MAGIC - Los esquemas solo se eliminan si `eliminar_esquemas = SI`, y sin `CASCADE`: si contienen otros objetos, fallan.
# MAGIC - **Nunca** elimina el catálogo, la External Location ni el bucket.

# COMMAND ----------

import os
import sys

sys.path.append(os.path.abspath("../proceso"))
import comun

p = comun.leer_parametros(dbutils, ("catalogo", "esquema_bronze", "esquema_silver", "esquema_gold", "lakehouse_root"))
dbutils.widgets.dropdown("confirmar", "NO", ["NO", "SI"])
dbutils.widgets.dropdown("eliminar_esquemas", "NO", ["NO", "SI"])
if dbutils.widgets.get("confirmar") != "SI":
    dbutils.notebook.exit("Cancelado: confirmar != SI")

# COMMAND ----------

for capa in ("gold", "silver", "bronze"):
    for tabla in comun.TABLAS[capa]:
        nombre = comun.nombre_tabla(p, capa, tabla)
        spark.sql(f"DROP TABLE IF EXISTS {nombre}")
        print(f"DROP   {nombre}   (datos conservados en {comun.ruta_tabla(p, capa, tabla)})")

if dbutils.widgets.get("eliminar_esquemas") == "SI":
    for capa in ("gold", "silver", "bronze"):
        esquema = f"`{p['catalogo']}`.`{p['esquema_' + capa]}`"
        spark.sql(f"DROP SCHEMA IF EXISTS {esquema}")
        print(f"DROP   {esquema}")
