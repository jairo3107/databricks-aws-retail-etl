# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · PrepAmb: preparación y verificación del ambiente
# MAGIC
# MAGIC - Comprueba que el **catálogo** existe y es accesible. **No lo crea**: no se asumen permisos de administración.
# MAGIC - Crea los esquemas Bronze/Silver/Gold si no existen (requiere `CREATE SCHEMA` sobre el catálogo).
# MAGIC - Verifica que los CSV RAW son legibles **directamente en S3** a través de la External Location de Unity Catalog.
# MAGIC - Verifica que RAW y `lakehouse/` no se solapan, y el aislamiento del entorno: dev usa `dev_*` y `lakehouse/dev/`,
# MAGIC   prod usa `bronze|silver|gold` y `lakehouse/prod/`. Lo valida `comun.leer_parametros`.
# MAGIC
# MAGIC No escribe datos, no borra rutas y no ejecuta DROP.

# COMMAND ----------

import comun

p = comun.leer_parametros(dbutils, comun.PARAMS_BASE + ("raw_path_ecommerce", "raw_path_automobiles"))
for k, v in p.items():
    print(f"{k:22} = {v}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Catálogo (solo verificación)

# COMMAND ----------

catalogos = [r[0] for r in spark.sql("SHOW CATALOGS").collect()]
if p["catalogo"] not in catalogos:
    raise RuntimeError(
        f"El catálogo '{p['catalogo']}' no existe o la identidad actual no tiene USE CATALOG sobre él. "
        "Permiso pendiente: que el owner o un admin lo cree o conceda "
        f"`GRANT USE CATALOG, CREATE SCHEMA ON CATALOG {p['catalogo']} TO <identidad del job>`. "
        "Ver PrepAmb/prerrequisitos_admin.sql."
    )
print(f"CHECK OK  catálogo '{p['catalogo']}' accesible")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Esquemas Medallion

# COMMAND ----------

for capa in comun.CAPAS:
    esquema = f"{p['catalogo']}.{p['esquema_' + capa]}"
    if spark.catalog.databaseExists(esquema):
        print(f"CHECK OK  esquema {esquema} ya existe")
        continue
    try:
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{p['catalogo']}`.`{p['esquema_' + capa]}` "
                  f"COMMENT 'Capa {capa} - databricks-aws-retail-etl'")
        print(f"CREADO    esquema {esquema}")
    except Exception as e:
        raise RuntimeError(
            f"No se pudo crear el esquema {esquema}. Permiso pendiente: "
            f"`CREATE SCHEMA ON CATALOG {p['catalogo']}` para la identidad del job. Error original: {e}"
        ) from e

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. RAW legible en S3 (External Location)

# COMMAND ----------

for clave in ("raw_path_ecommerce", "raw_path_automobiles"):
    ruta = comun.ruta_raw(p, p[clave])
    try:
        info = dbutils.fs.ls(ruta)
    except Exception as e:
        raise RuntimeError(
            f"No se puede listar '{ruta}'. Comprueba que el archivo está subido a esa ruta y que la identidad "
            "del job tiene `READ FILES` sobre la External Location que cubre el bucket. "
            f"Error original: {e}"
        ) from e
    tamano = info[0].size if len(info) == 1 else None
    comun.exigir(bool(tamano), f"RAW es un único archivo no vacío: {ruta} ({tamano} bytes)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Separación entre RAW y lakehouse

# COMMAND ----------

raw, lake = p["raw_root"] + "/", p["lakehouse_root"] + "/"
comun.exigir(not raw.startswith(lake) and not lake.startswith(raw),
             f"RAW ({p['raw_root']}) y lakehouse ({p['lakehouse_root']}) no se solapan")

for capa in comun.CAPAS:
    for tabla in comun.TABLAS[capa]:
        print(f"{comun.nombre_tabla(p, capa, tabla):70} -> {comun.ruta_tabla(p, capa, tabla)}")
