# Databricks notebook source
# MAGIC %md
# MAGIC # 03 · Load: Silver → Gold
# MAGIC
# MAGIC Agregados de negocio **por fuente**, sin joins ni uniones entre E-commerce y Automobiles.
# MAGIC
# MAGIC `semantica_discount` vale `desconocida` por defecto, y así no se calcula ningún precio neto. Cambiarla a
# MAGIC `porcentaje` o `importe` solo después de verificar la unidad con el propietario del dataset.

# COMMAND ----------

import comun
import transformaciones as T
from pyspark.sql import functions as F

p = comun.leer_parametros(dbutils, comun.PARAMS_BASE)
dbutils.widgets.text("semantica_discount", "desconocida")
semantica = dbutils.widgets.get("semantica_discount").strip().lower()
if semantica not in T.SEMANTICAS_DISCOUNT:
    raise ValueError(f"semantica_discount='{semantica}' no válida; opciones {T.SEMANTICAS_DISCOUNT}")
print(f"semantica_discount = {semantica}")

ecommerce = spark.table(comun.nombre_tabla(p, "silver", "ecommerce_ventas"))
autos = spark.table(comun.nombre_tabla(p, "silver", "automobiles_specs"))

gold = {
    "ecommerce_ventas_mensuales_categoria": T.gold_ecommerce_mensual_categoria(ecommerce, semantica),
    "ecommerce_ventas_segmento_categoria": T.gold_ecommerce_segmento_categoria(ecommerce),
    "automobiles_resumen_marca": T.gold_automobiles_resumen_marca(autos),
    "automobiles_resumen_carroceria_combustible": T.gold_automobiles_carroceria_combustible(autos),
}
assert set(gold) == set(comun.TABLAS["gold"]), "Inventario de Gold desalineado con comun.TABLAS"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validaciones de conciliación con Silver (antes de escribir)

# COMMAND ----------

unidades_silver = ecommerce.agg(F.sum("units_sold")).first()[0]
filas_ecommerce = ecommerce.count()
filas_autos = autos.count()

for nombre in ("ecommerce_ventas_mensuales_categoria", "ecommerce_ventas_segmento_categoria"):
    unidades_gold = gold[nombre].agg(F.sum("unidades_vendidas")).first()[0]
    comun.exigir(unidades_gold == unidades_silver, f"{nombre}: unidades {unidades_gold} = Silver {unidades_silver}")
comun.exigir(gold["ecommerce_ventas_mensuales_categoria"].agg(F.sum("dias_con_registro")).first()[0] == filas_ecommerce,
             "ecommerce mensual: suma de registros = filas Silver")
comun.exigir(gold["ecommerce_ventas_segmento_categoria"].agg(F.sum("registros")).first()[0] == filas_ecommerce,
             "ecommerce segmento: suma de registros = filas Silver")

for nombre in ("automobiles_resumen_marca", "automobiles_resumen_carroceria_combustible"):
    registros = gold[nombre].agg(F.sum("registros")).first()[0]
    comun.exigir(registros == filas_autos, f"{nombre}: registros {registros} = Silver {filas_autos}")
comun.exigir(gold["automobiles_resumen_marca"].count() == autos.select("make").distinct().count(),
             "automobiles_resumen_marca: una fila por marca")

# COMMAND ----------

for tabla, df in gold.items():
    comun.escribir_tabla_externa(spark, df, comun.nombre_tabla(p, "gold", tabla), comun.ruta_tabla(p, "gold", tabla))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Resultados Gold

# COMMAND ----------

for tabla in comun.TABLAS["gold"]:
    nombre = comun.nombre_tabla(p, "gold", tabla)
    print(f"{nombre}: {spark.table(nombre).count()} filas")
    display(spark.table(nombre).limit(10))
