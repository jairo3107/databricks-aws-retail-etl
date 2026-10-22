"""Pruebas locales de proceso/transformaciones.py sobre los CSV de datasets/.

No usa Databricks, S3 ni Delta: comprueba la lógica DataFrame (tipos, nulos,
conciliación Gold). Requiere Java 17 (PySpark lo instala uv):
    uv sync --locked && uv run pytest -q
"""

import sys
from pathlib import Path

import pytest
from pyspark.sql import SparkSession, functions as F

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "proceso"))

import comun  # noqa: E402
import transformaciones as T  # noqa: E402

CSV_ECOMMERCE = RAIZ / "datasets/ecommerce/Ecommerce_Sales_Prediction_Dataset.csv"
CSV_AUTOMOBILES = RAIZ / "datasets/automobiles/Automobile_data.csv"


@pytest.fixture(scope="session")
def spark():
    s = (SparkSession.builder.master("local[2]").appName("tests")
         .config("spark.sql.ansi.enabled", "true")  # como serverless
         .config("spark.sql.session.timeZone", "UTC")
         .config("spark.ui.enabled", "false").getOrCreate())
    yield s
    s.stop()


def leer(spark, ruta):
    return (spark.read.format("csv").option("header", "true").option("inferSchema", "false")
            .option("mode", "FAILFAST").load(str(ruta)))


@pytest.fixture(scope="session")
def ecommerce(spark):
    raw = leer(spark, CSV_ECOMMERCE)
    comun.validar_columnas(raw, T.COLS_RAW_ECOMMERCE, "test")
    return T.silver_ecommerce(T.a_bronze(raw, "test"))


@pytest.fixture(scope="session")
def autos(spark):
    raw = leer(spark, CSV_AUTOMOBILES)
    comun.validar_columnas(raw, T.COLS_RAW_AUTOMOBILES, "test")
    raw = raw.toDF(*[T.snake(c) for c in raw.columns])
    return T.silver_automobiles(T.a_bronze(raw, "test"))


def test_ecommerce_silver(ecommerce):
    assert ecommerce.count() == 1000
    comun.validar_tipos(ecommerce, T.TIPOS_SILVER_ECOMMERCE, "test")
    assert set(comun.conteo_nulos(ecommerce, list(T.TIPOS_SILVER_ECOMMERCE)).values()) == {0}
    r = ecommerce.agg(F.min("fecha"), F.max("fecha")).first()
    assert (str(r[0]), str(r[1])) == ("2023-01-01", "2025-09-26")
    assert ecommerce.first()["_archivo_origen"].endswith("Ecommerce_Sales_Prediction_Dataset.csv")


def test_automobiles_silver(autos):
    assert autos.count() == 205
    comun.validar_tipos(autos, T.TIPOS_SILVER_AUTOMOBILES, "test")
    nulos = {c: n for c, n in comun.conteo_nulos(autos, list(T.COLS_BRONZE_AUTOMOBILES)).items() if n}
    assert nulos == {"normalized_losses": 41, "num_of_doors": 2, "bore": 4, "stroke": 4,
                     "horsepower": 2, "peak_rpm": 2, "price": 4}
    assert {r[0] for r in autos.select("num_of_cylinders").distinct().collect()} == {2, 3, 4, 5, 6, 8, 12}
    assert autos.select("registro_hash").distinct().count() == 205


def test_valor_invalido_queda_nulo_sin_error(spark):
    df = spark.createDataFrame([("12",), ("1x",), ("?",)], ["v"])
    assert [r[0] for r in df.select(T.a_entero("v")).collect()] == [12, None, None]


def test_gold_ecommerce_concilia(ecommerce):
    unidades = ecommerce.agg(F.sum("units_sold")).first()[0]
    mensual = T.gold_ecommerce_mensual_categoria(ecommerce)
    segmento = T.gold_ecommerce_segmento_categoria(ecommerce)
    assert mensual.agg(F.sum("unidades_vendidas")).first()[0] == unidades
    assert segmento.agg(F.sum("unidades_vendidas")).first()[0] == unidades
    assert segmento.count() == 15  # 3 segmentos x 5 categorías
    assert not any(c.startswith("precio_neto") for c in mensual.columns)


def test_gold_ecommerce_precio_neto_solo_si_se_declara(ecommerce):
    cols = T.gold_ecommerce_mensual_categoria(ecommerce, "porcentaje").columns
    assert "precio_neto_promedio_porcentaje" in cols
    with pytest.raises(ValueError):
        T.gold_ecommerce_mensual_categoria(ecommerce, "otra")


def test_gold_automobiles_concilia(autos):
    marca = T.gold_automobiles_resumen_marca(autos)
    assert marca.count() == 22
    assert marca.agg(F.sum("registros")).first()[0] == 205
    assert marca.agg(F.sum("registros_sin_precio")).first()[0] == 4
    assert T.gold_automobiles_carroceria_combustible(autos).agg(F.sum("registros")).first()[0] == 205


def test_inventario_gold_coincide_con_funciones():
    assert len(comun.TABLAS["gold"]) == 4
