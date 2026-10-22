"""Las consultas de dashboard/sql/ se ejecutan contra las tablas Gold generadas en local.

Comprueba que todas las columnas existen y que los indicadores cuadran con Silver.
Las tablas se registran como vistas temporales: el prefijo workspace.dev_gold. se
elimina, porque el Spark local no tiene catálogo Unity Catalog. Requiere Java 17.
"""

import re
import sys
from pathlib import Path

import pytest
from pyspark.sql import SparkSession

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "proceso"))

import comun  # noqa: E402
import transformaciones as T  # noqa: E402

SQL = sorted((RAIZ / "dashboard" / "sql").glob("*.sql"))
PREFIJO = "workspace.dev_gold."
FILAS = {"01": 165, "02": 15, "03": 22, "04": 9, "05": 1, "06": 1}


@pytest.fixture(scope="module")
def spark():
    s = (SparkSession.builder.master("local[2]").appName("tests-dashboard")
         .config("spark.sql.ansi.enabled", "true")
         .config("spark.ui.enabled", "false").getOrCreate())
    leer = lambda p: s.read.option("header", "true").option("inferSchema", "false").csv(str(RAIZ / p))  # noqa: E731
    autos = leer("datasets/automobiles/Automobile_data.csv")
    autos = autos.toDF(*[T.snake(c) for c in autos.columns])
    eco = T.silver_ecommerce(T.a_bronze(leer("datasets/ecommerce/Ecommerce_Sales_Prediction_Dataset.csv"), "t"))
    aut = T.silver_automobiles(T.a_bronze(autos, "t"))
    gold = {
        "ecommerce_ventas_mensuales_categoria": T.gold_ecommerce_mensual_categoria(eco),
        "ecommerce_ventas_segmento_categoria": T.gold_ecommerce_segmento_categoria(eco),
        "automobiles_resumen_marca": T.gold_automobiles_resumen_marca(aut),
        "automobiles_resumen_carroceria_combustible": T.gold_automobiles_carroceria_combustible(aut),
    }
    assert set(gold) == set(comun.TABLAS["gold"])
    for nombre, df in gold.items():
        df.createOrReplaceTempView(nombre)
    yield s


def ejecutar(spark, archivo):
    texto = archivo.read_text(encoding="utf-8")
    assert PREFIJO in texto, f"{archivo.name}: debe consultar {PREFIJO}<tabla>"
    for tabla in re.findall(re.escape(PREFIJO) + r"(\w+)", texto):
        assert tabla in comun.TABLAS["gold"], f"{archivo.name}: {tabla} no es una tabla Gold"
    return spark.sql(texto.replace(PREFIJO, "")).collect()


def test_hay_una_consulta_por_tabla_gold():
    tablas = {t for f in SQL for t in re.findall(re.escape(PREFIJO) + r"(\w+)", f.read_text())}
    assert tablas == set(comun.TABLAS["gold"])


@pytest.mark.parametrize("archivo", SQL, ids=[f.name for f in SQL])
def test_consulta_ejecuta(spark, archivo):
    filas = ejecutar(spark, archivo)
    assert len(filas) == FILAS[archivo.name[:2]]


def test_kpis_concilian(spark):
    eco = ejecutar(spark, RAIZ / "dashboard/sql/05_kpi_ecommerce.sql")[0]
    assert eco["unidades_vendidas_total"] == 29631 and eco["registros_silver"] == 1000
    aut = ejecutar(spark, RAIZ / "dashboard/sql/06_kpi_automobiles.sql")[0]
    assert (aut["vehiculos"], aut["vehiculos_sin_precio"], aut["marcas"]) == (205, 4, 22)
