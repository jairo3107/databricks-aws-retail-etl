# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Extract E-commerce: RAW (S3) → Bronze
# MAGIC
# MAGIC Lee el CSV **directamente desde S3** (sin DBFS ni Volúmenes), sin inferir tipos: todas las columnas
# MAGIC quedan como `string`. Añade columnas de auditoría y registra la tabla Delta externa en Unity Catalog,
# MAGIC en `lakehouse/bronze/`.

# COMMAND ----------

import comun
import transformaciones as T

p = comun.leer_parametros(dbutils, comun.PARAMS_BASE + ("raw_path_ecommerce",))
dbutils.widgets.text("ejecucion_id", "manual")
ejecucion_id = dbutils.widgets.get("ejecucion_id")

TABLA = "ecommerce_ventas"
origen = comun.ruta_raw(p, p["raw_path_ecommerce"])
destino = comun.nombre_tabla(p, "bronze", TABLA)
ruta_destino = comun.ruta_tabla(p, "bronze", TABLA)
print(f"{origen}\n  -> {destino}\n  -> {ruta_destino}")

# COMMAND ----------

df_raw = (spark.read.format("csv")
          .option("header", "true")
          .option("inferSchema", "false")
          .option("sep", ",")
          .option("encoding", "UTF-8")
          .option("mode", "FAILFAST")
          .load(origen))

comun.validar_columnas(df_raw, T.COLS_RAW_ECOMMERCE, "raw ecommerce")
df_bronze = T.a_bronze(df_raw, ejecucion_id)

# COMMAND ----------

comun.escribir_tabla_externa(spark, df_bronze, destino, ruta_destino)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verificación

# COMMAND ----------

n_raw = df_raw.count()
tabla = spark.table(destino)
n_bronze = tabla.count()
comun.exigir(n_raw > 0, f"RAW ecommerce tiene filas ({n_raw})")
comun.exigir(n_bronze == n_raw, f"Bronze ecommerce = RAW ({n_bronze} = {n_raw})")
comun.exigir(all(t == "string" for c, t in tabla.dtypes if not c.startswith("_")),
             "Bronze ecommerce conserva todas las columnas de datos como string")
print("Nulos por columna:", comun.conteo_nulos(tabla, list(T.COLS_RAW_ECOMMERCE)))
display(tabla.limit(5))
