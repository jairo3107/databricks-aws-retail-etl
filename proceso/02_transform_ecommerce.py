# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Transform E-commerce: Bronze → Silver
# MAGIC
# MAGIC Reglas explícitas (ver `transformaciones.py` y `docs/esquemas_detectados.md`):
# MAGIC - `Date` en formato `dd-MM-yyyy` → `fecha` (`date`).
# MAGIC - `Price`, `Discount` y `Marketing_Spend` → `decimal(12,2)`; `Units_Sold` → `int`.
# MAGIC - `Discount` se conserva con su valor original: **su unidad no está verificada**, así que aquí no se calcula
# MAGIC   ningún precio neto.
# MAGIC
# MAGIC Las validaciones se ejecutan **antes** de escribir: si alguna falla, Silver no se modifica.

# COMMAND ----------

import comun
import transformaciones as T
from pyspark.sql import functions as F

p = comun.leer_parametros(dbutils, comun.PARAMS_BASE)
TABLA = "ecommerce_ventas"
origen = comun.nombre_tabla(p, "bronze", TABLA)
destino = comun.nombre_tabla(p, "silver", TABLA)
ruta_destino = comun.ruta_tabla(p, "silver", TABLA)

df_bronze = spark.table(origen)
df_silver = T.silver_ecommerce(df_bronze)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validaciones de calidad (antes de escribir)

# COMMAND ----------

n_bronze, n_silver = df_bronze.count(), df_silver.count()
comun.exigir(n_silver == n_bronze, f"Silver conserva todas las filas de Bronze ({n_silver} = {n_bronze})")
comun.validar_tipos(df_silver, T.TIPOS_SILVER_ECOMMERCE, "silver ecommerce")

# Si un valor no vacío no encaja con su regla de tipo, queda nulo. Por eso los nulos de Silver
# deben coincidir exactamente con los vacíos de Bronze.
mapa = dict(zip(T.COLS_RAW_ECOMMERCE, T.TIPOS_SILVER_ECOMMERCE))
fila = df_bronze.select([F.sum((F.col(c).isNull() | (F.trim(F.col(c)) == "")).cast("int")).alias(c)
                         for c in T.COLS_RAW_ECOMMERCE]).first()
vacios_bronze = {mapa[c]: int(fila[c] or 0) for c in T.COLS_RAW_ECOMMERCE}
nulos_silver = comun.conteo_nulos(df_silver, list(T.TIPOS_SILVER_ECOMMERCE))
print("Vacíos Bronze:", vacios_bronze)
print("Nulos Silver :", nulos_silver)
comun.exigir(nulos_silver == vacios_bronze, "Ningún valor se perdió al tipificar (nulos Silver = vacíos Bronze)")

reglas = {
    "price > 0": F.col("price") <= 0,
    "units_sold >= 0": F.col("units_sold") < 0,
    "discount >= 0": F.col("discount") < 0,
    "marketing_spend >= 0": F.col("marketing_spend") < 0,
}
for regla, incumple in reglas.items():
    n = df_silver.filter(incumple).count()
    comun.exigir(n == 0, f"Regla '{regla}' sin incumplimientos ({n})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Evidencia sobre la semántica de `Discount` (informativa, sin interpretarla)

# COMMAND ----------

ev = df_silver.agg(
    F.min("discount").alias("min"), F.max("discount").alias("max"),
    F.sum((F.col("discount") > F.col("price")).cast("int")).alias("filas_discount_mayor_que_price"),
    F.sum((F.col("discount") > 100).cast("int")).alias("filas_discount_mayor_que_100"),
).first().asDict()
print(ev)
print("Si alguna fila tiene discount > price, 'importe absoluto' daría un precio neto negativo en esas filas. "
      "La semántica definitiva se fija con el parámetro semantica_discount del Load.")

n_fechas = df_silver.select("fecha").distinct().count()
print(f"Fechas distintas: {n_fechas} de {n_silver} filas (informativo; no se usa como clave)")

# COMMAND ----------

comun.escribir_tabla_externa(spark, df_silver, destino, ruta_destino)
comun.exigir(spark.table(destino).count() == n_silver, f"{destino} tiene {n_silver} filas")
display(spark.table(destino).limit(5))
