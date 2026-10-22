# Databricks notebook source
# MAGIC %md
# MAGIC # 04 · Grants: acceso de lectura a Gold
# MAGIC
# MAGIC Concede a `grant_principal` el mínimo necesario para consultar el Gold del entorno:
# MAGIC `USE CATALOG`, `USE SCHEMA` sobre Gold y `SELECT` sobre cada tabla Gold.
# MAGIC No concede acceso a Bronze ni a Silver, ni privilegios de escritura.
# MAGIC
# MAGIC `grant_principal` admite, por orden de preferencia:
# MAGIC 1. **Grupo de cuenta** dedicado (p. ej. `retail_etl_readers`), con origen *Account*.
# MAGIC 2. **Service principal**, por su application ID.
# MAGIC 3. **Usuario**, por su correo. Se pasa como parámetro y nunca se escribe en el repositorio.
# MAGIC
# MAGIC Se rechazan `admins`, `users`, `account users` y los grupos locales del workspace (origen *Workspace*),
# MAGIC porque Unity Catalog no admite conceder acceso a datos a grupos locales.
# MAGIC
# MAGIC Si la identidad del job no puede conceder algún privilegio (no es owner y no tiene `MANAGE`), **no intenta
# MAGIC elevarse**: muestra qué permiso falta y la tarea termina con error. Reversión: `reversion/01_revoke.py`.

# COMMAND ----------

import comun

p = comun.leer_parametros(dbutils, ("catalogo", "esquema_gold", "grant_principal"))
principal = p["grant_principal"]
tipo = comun.validar_principal(principal)
visible = comun.enmascarar(principal)
print(f"grant_principal: {visible} (tipo: {tipo})")

esquema = f"`{p['catalogo']}`.`{p['esquema_gold']}`"
sentencias = [f"GRANT USE CATALOG ON CATALOG `{p['catalogo']}` TO `{principal}`",
              f"GRANT USE SCHEMA ON SCHEMA {esquema} TO `{principal}`"]
sentencias += [f"GRANT SELECT ON TABLE {esquema}.`{t}` TO `{principal}`" for t in comun.TABLAS["gold"]]

# COMMAND ----------

fallos = []
for s in sentencias:
    mostrada = s.replace(principal, visible)
    try:
        spark.sql(s)
        print(f"OK     {mostrada}")
    except Exception as e:
        primera_linea = str(e).strip().splitlines()[0].replace(principal, visible)
        fallos.append((mostrada, primera_linea))
        print(f"FALLO  {mostrada}\n       {primera_linea}")

# COMMAND ----------

try:
    display(spark.sql(f"SHOW GRANTS `{principal}` ON SCHEMA {esquema}"))
except Exception as e:
    print(f"No se pudo mostrar SHOW GRANTS (informativo): {str(e).strip().splitlines()[0].replace(principal, visible)}")

# COMMAND ----------

if fallos:
    detalle = "\n".join(f"- {s}\n    {e}" for s, e in fallos)
    pista = ("Si es un grupo, comprueba en Settings → Identity and access → Groups que su origen es Account "
             "(los grupos con origen Workspace no sirven en Unity Catalog). " if tipo == "grupo" else
             "Comprueba que el principal existe y tiene acceso al workspace. ")
    raise RuntimeError(
        f"{len(fallos)} GRANT(s) no aplicados a {visible}. {pista}Si el error es de privilegios, que el owner del "
        "objeto (o alguien con MANAGE) ejecute las sentencias o conceda MANAGE a la identidad del job. "
        f"Ver seguridad/README.md.\n{detalle}"
    )
print(f"CHECK OK  {len(sentencias)} GRANT(s) aplicados a {visible}")
