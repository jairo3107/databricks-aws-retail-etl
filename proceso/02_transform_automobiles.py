# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Transform Automobiles: Bronze → Silver
# MAGIC
# MAGIC Reglas explícitas (ver `transformaciones.py` y `docs/esquemas_detectados.md`):
# MAGIC - `?` → nulo en todas las columnas.
# MAGIC - Enteros: symboling, normalized_losses, curb_weight, engine_size, horsepower, peak_rpm, city_mpg,
# MAGIC   highway_mpg y price.
# MAGIC - Decimales `decimal(8,2)`: wheel_base, length, width, height, bore, stroke y compression_ratio.
# MAGIC - Números escritos en palabras → `int`: num_of_doors y num_of_cylinders, mediante un mapa explícito.
# MAGIC - Categóricas: `trim` y minúsculas. `registro_hash` es una clave técnica, porque no hay clave natural.

# COMMAND ----------

import comun
import transformaciones as T
from pyspark.sql import functions as F

p = comun.leer_parametros(dbutils, comun.PARAMS_BASE)
TABLA = "automobiles_specs"
origen = comun.nombre_tabla(p, "bronze", TABLA)
destino = comun.nombre_tabla(p, "silver", TABLA)
ruta_destino = comun.ruta_tabla(p, "silver", TABLA)

df_bronze = spark.table(origen)
df_silver = T.silver_automobiles(df_bronze)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validaciones de calidad (antes de escribir)

# COMMAND ----------

n_bronze, n_silver = df_bronze.count(), df_silver.count()
comun.exigir(n_silver == n_bronze, f"Silver conserva todas las filas de Bronze ({n_silver} = {n_bronze})")
comun.validar_tipos(df_silver, T.TIPOS_SILVER_AUTOMOBILES, "silver automobiles")

# Los nulos de Silver deben ser exactamente los '?' (o vacíos) de Bronze. Así se detecta cualquier valor
# que no encaje con su regla de tipo o cualquier palabra que falte en el mapa.
cols = list(T.COLS_BRONZE_AUTOMOBILES)
fila = df_bronze.select([F.sum((F.col(c).isNull() | F.trim(F.col(c)).isin("", T.NULO_AUTOMOBILES)).cast("int")).alias(c)
                         for c in cols]).first()
ausentes_bronze = {c: int(fila[c] or 0) for c in cols}
nulos_silver = comun.conteo_nulos(df_silver, cols)
print("Ausentes Bronze ('?'):", {c: n for c, n in ausentes_bronze.items() if n})
print("Nulos Silver         :", {c: n for c, n in nulos_silver.items() if n})
diferencias = {c: (ausentes_bronze[c], nulos_silver[c]) for c in cols if ausentes_bronze[c] != nulos_silver[c]}
comun.exigir(not diferencias, f"Ningún valor se perdió al tipificar; diferencias={diferencias}")

reglas = {
    "price > 0": F.col("price") <= 0,
    "horsepower > 0": F.col("horsepower") <= 0,
    "engine_size > 0": F.col("engine_size") <= 0,
    "symboling entre -3 y 3": ~F.col("symboling").between(-3, 3),
}
for regla, incumple in reglas.items():
    n = df_silver.filter(incumple).count()
    comun.exigir(n == 0, f"Regla '{regla}' sin incumplimientos ({n})")

duplicados = n_silver - df_silver.select("registro_hash").distinct().count()
print(f"Registros idénticos en origen: {duplicados} (informativo; se conservan)")

# COMMAND ----------

comun.escribir_tabla_externa(spark, df_silver, destino, ruta_destino)
comun.exigir(spark.table(destino).count() == n_silver, f"{destino} tiene {n_silver} filas")
display(spark.table(destino).limit(5))
