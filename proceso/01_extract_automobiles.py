# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Extract Automobiles: RAW (S3) → Bronze
# MAGIC
# MAGIC Lee el CSV **directamente desde S3** sin inferir tipos. El marcador `?` se conserva tal cual en Bronze
# MAGIC y se convierte a nulo en Silver. Registra la tabla Delta externa en Unity Catalog, en `lakehouse/bronze/`.

# COMMAND ----------

import comun
import transformaciones as T

p = comun.leer_parametros(dbutils, comun.PARAMS_BASE + ("raw_path_automobiles",))
dbutils.widgets.text("ejecucion_id", "manual")
ejecucion_id = dbutils.widgets.get("ejecucion_id")

TABLA = "automobiles_specs"
origen = comun.ruta_raw(p, p["raw_path_automobiles"])
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

comun.validar_columnas(df_raw, T.COLS_RAW_AUTOMOBILES, "raw automobiles")
# Nombres en snake_case desde Bronze: los guiones obligan a usar comillas invertidas en SQL.
# Solo cambia el nombre (mapeo 1:1 con T.snake); los valores quedan tal cual, '?' incluido.
df_raw = df_raw.toDF(*[T.snake(c) for c in df_raw.columns])
df_bronze = T.a_bronze(df_raw, ejecucion_id)

# COMMAND ----------

comun.escribir_tabla_externa(spark, df_bronze, destino, ruta_destino)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verificación

# COMMAND ----------

from pyspark.sql import functions as F

n_raw = df_raw.count()
tabla = spark.table(destino)
n_bronze = tabla.count()
comun.exigir(n_raw > 0, f"RAW automobiles tiene filas ({n_raw})")
comun.exigir(n_bronze == n_raw, f"Bronze automobiles = RAW ({n_bronze} = {n_raw})")
comun.exigir(all(t == "string" for c, t in tabla.dtypes if not c.startswith("_")),
             "Bronze automobiles conserva todas las columnas de datos como string")
columnas = list(T.COLS_BRONZE_AUTOMOBILES)
fila = tabla.select([F.sum((F.trim(F.col(c)) == T.NULO_AUTOMOBILES).cast("int")).alias(c) for c in columnas]).first()
print("Marcadores '?' por columna:", {c: fila[c] for c in columnas if fila[c]})
display(tabla.limit(5))
