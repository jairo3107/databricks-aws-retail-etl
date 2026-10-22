# Databricks notebook source
# MAGIC %md
# MAGIC # Reversión 01 · REVOKE de los permisos de lectura en Gold
# MAGIC
# MAGIC Deshace `proceso/04_grants.py`. Requiere `entorno` (dev|prod). **No forma parte del job.** Para ejecutarlo hay que escribir `SI` en `confirmar`.
# MAGIC `USE CATALOG` solo se revoca si `revocar_use_catalog = SI`, porque el principal podría necesitarlo para otros esquemas.

# COMMAND ----------

import os
import sys

sys.path.append(os.path.abspath("../proceso"))
import comun

p = comun.leer_parametros(dbutils, ("catalogo", "esquema_gold", "grant_principal"))
dbutils.widgets.dropdown("confirmar", "NO", ["NO", "SI"])
dbutils.widgets.dropdown("revocar_use_catalog", "NO", ["NO", "SI"])
if dbutils.widgets.get("confirmar") != "SI":
    dbutils.notebook.exit("Cancelado: confirmar != SI")

principal = p["grant_principal"]
comun.validar_principal(principal)
visible = comun.enmascarar(principal)
esquema = f"`{p['catalogo']}`.`{p['esquema_gold']}`"
sentencias = [f"REVOKE SELECT ON TABLE {esquema}.`{t}` FROM `{principal}`" for t in comun.TABLAS["gold"]]
sentencias.append(f"REVOKE USE SCHEMA ON SCHEMA {esquema} FROM `{principal}`")
if dbutils.widgets.get("revocar_use_catalog") == "SI":
    sentencias.append(f"REVOKE USE CATALOG ON CATALOG `{p['catalogo']}` FROM `{principal}`")

for s in sentencias:
    try:
        spark.sql(s)
        print(f"OK     {s.replace(principal, visible)}")
    except Exception as e:
        print(f"FALLO  {s.replace(principal, visible)}\n       {str(e).strip().splitlines()[0].replace(principal, visible)}")
