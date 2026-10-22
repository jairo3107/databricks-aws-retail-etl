"""Lógica de negocio (PySpark DataFrame API), sin E/S.

Funciones puras DataFrame -> DataFrame, usadas por los notebooks de proceso/ y
probables en local. Las dos fuentes se tratan por separado: no hay joins ni
uniones entre E-commerce y Automobiles.

Las reglas de tipificación se basan en docs/esquemas_detectados.md.
"""

from pyspark.sql import functions as F

# --- Contratos de columnas RAW (cabeceras verificadas) -------------------------
COLS_RAW_ECOMMERCE = (
    "Date", "Product_Category", "Price", "Discount",
    "Customer_Segment", "Marketing_Spend", "Units_Sold",
)

COLS_RAW_AUTOMOBILES = (
    "symboling", "normalized-losses", "make", "fuel-type", "aspiration",
    "num-of-doors", "body-style", "drive-wheels", "engine-location",
    "wheel-base", "length", "width", "height", "curb-weight", "engine-type",
    "num-of-cylinders", "engine-size", "fuel-system", "bore", "stroke",
    "compression-ratio", "horsepower", "peak-rpm", "city-mpg", "highway-mpg",
    "price",
)

# Marcador de ausente en Automobiles (verificado: no hay celdas vacías).
NULO_AUTOMOBILES = "?"

# Discount: unidad no verificada. 'desconocida' impide derivar precio neto.
SEMANTICAS_DISCOUNT = ("desconocida", "porcentaje", "importe")

_RE_ENTERO = r"^-?[0-9]+$"
_RE_DECIMAL = r"^-?[0-9]+(\.[0-9]+)?$"
_RE_FECHA_DMY = r"^[0-9]{2}-[0-9]{2}-[0-9]{4}$"

PALABRAS_NUMERO = {
    "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "eight": 8, "twelve": 12,
}


# --- Tipificación explícita ------------------------------------------------------
# Cada regla valida el texto con un patrón antes de convertir: un valor que no
# encaja queda nulo (no lanza error en modo ANSI) y se detecta en las
# validaciones de Silver al comparar nulos antes y después.
def a_entero(c):
    c = F.trim(F.col(c))
    return F.when(c.rlike(_RE_ENTERO), c.cast("int"))


def a_decimal(c, precision=12, escala=2):
    c = F.trim(F.col(c))
    return F.when(c.rlike(_RE_DECIMAL), c.cast(f"decimal({precision},{escala})"))


def a_fecha_dmy(c):
    c = F.trim(F.col(c))
    return F.when(c.rlike(_RE_FECHA_DMY), F.to_date(c, "dd-MM-yyyy"))


def a_texto(c):
    c = F.trim(F.col(c))
    return F.when(c != "", c)


def palabra_a_entero(c):
    mapa = F.create_map(*[x for k, v in PALABRAS_NUMERO.items() for x in (F.lit(k), F.lit(v))])
    return mapa[F.lower(F.trim(F.col(c)))]


def snake(nombre):
    return nombre.strip().lower().replace("-", "_").replace(" ", "_")


# --- Bronze -------------------------------------------------------------------------
def a_bronze(df_raw, ejecucion_id):
    """RAW tal cual (todo string) + columnas de auditoría."""
    return (df_raw
            .withColumn("_archivo_origen", F.col("_metadata.file_path"))
            .withColumn("_fecha_ingesta", F.current_timestamp())
            .withColumn("_ejecucion_id", F.lit(ejecucion_id)))


# --- Silver: E-commerce ---------------------------------------------------------------
TIPOS_SILVER_ECOMMERCE = {
    "fecha": "date",
    "product_category": "string",
    "price": "decimal(12,2)",
    "discount": "decimal(12,2)",
    "customer_segment": "string",
    "marketing_spend": "decimal(12,2)",
    "units_sold": "int",
}


def silver_ecommerce(df_bronze):
    return df_bronze.select(
        a_fecha_dmy("Date").alias("fecha"),
        a_texto("Product_Category").alias("product_category"),
        a_decimal("Price").alias("price"),
        # Se conserva el valor original; su unidad no está verificada.
        a_decimal("Discount").alias("discount"),
        a_texto("Customer_Segment").alias("customer_segment"),
        a_decimal("Marketing_Spend").alias("marketing_spend"),
        a_entero("Units_Sold").alias("units_sold"),
        "_archivo_origen", "_fecha_ingesta", "_ejecucion_id",
    )


# --- Silver: Automobiles --------------------------------------------------------------
# Bronze ya trae los nombres en snake_case (mapeo 1:1 de la cabecera RAW); los valores son los RAW.
COLS_BRONZE_AUTOMOBILES = tuple(snake(c) for c in COLS_RAW_AUTOMOBILES)

_AUTOS_ENTEROS = ("symboling", "normalized_losses", "curb_weight", "engine_size",
                  "horsepower", "peak_rpm", "city_mpg", "highway_mpg", "price")
_AUTOS_DECIMALES = ("wheel_base", "length", "width", "height",
                    "bore", "stroke", "compression_ratio")
_AUTOS_PALABRAS = ("num_of_doors", "num_of_cylinders")
_AUTOS_TEXTO = ("make", "fuel_type", "aspiration", "body_style", "drive_wheels",
                "engine_location", "engine_type", "fuel_system")

TIPOS_SILVER_AUTOMOBILES = {
    **{c: "int" for c in _AUTOS_ENTEROS + _AUTOS_PALABRAS},
    **{c: "decimal(8,2)" for c in _AUTOS_DECIMALES},
    **{c: "string" for c in _AUTOS_TEXTO},
}


def automobiles_sin_marcador(df_bronze):
    """Sustituye '?' por nulo en todas las columnas de datos."""
    return df_bronze.select(*[
        F.when(F.trim(F.col(c)) != NULO_AUTOMOBILES, F.col(c)).alias(c)
        if c in COLS_BRONZE_AUTOMOBILES else F.col(c)
        for c in df_bronze.columns
    ])


def silver_automobiles(df_bronze):
    df = automobiles_sin_marcador(df_bronze)
    expr = {}
    for c in _AUTOS_ENTEROS:
        expr[c] = a_entero(c)
    for c in _AUTOS_DECIMALES:
        expr[c] = a_decimal(c, 8, 2)
    for c in _AUTOS_PALABRAS:
        expr[c] = palabra_a_entero(c)
    for c in _AUTOS_TEXTO:
        expr[c] = F.lower(a_texto(c))
    # Sin clave natural: huella del registro original como clave técnica.
    huella = F.sha2(F.concat_ws("|", *[F.coalesce(F.col(c), F.lit("<null>"))
                                        for c in COLS_BRONZE_AUTOMOBILES]), 256)
    return df.select(
        huella.alias("registro_hash"),
        *[expr[c].alias(c) for c in COLS_BRONZE_AUTOMOBILES],
        "_archivo_origen", "_fecha_ingesta", "_ejecucion_id",
    )


# --- Gold: E-commerce ------------------------------------------------------------------
def _precio_neto(semantica):
    if semantica == "porcentaje":
        return F.col("price") * (F.lit(1) - F.col("discount") / F.lit(100))
    if semantica == "importe":
        return F.col("price") - F.col("discount")
    return None


def gold_ecommerce_mensual_categoria(df_silver, semantica_discount="desconocida"):
    if semantica_discount not in SEMANTICAS_DISCOUNT:
        raise ValueError(f"semantica_discount debe ser una de {SEMANTICAS_DISCOUNT}")
    aggs = [
        F.count(F.lit(1)).alias("dias_con_registro"),
        F.sum("units_sold").alias("unidades_vendidas"),
        F.round(F.avg("price"), 2).alias("precio_promedio"),
        F.round(F.avg("discount"), 2).alias("discount_promedio_valor_original"),
        F.sum("marketing_spend").alias("gasto_marketing_total"),
    ]
    neto = _precio_neto(semantica_discount)
    if neto is not None:
        aggs.append(F.round(F.avg(neto), 2).alias(f"precio_neto_promedio_{semantica_discount}"))
    return (df_silver
            .withColumn("anio_mes", F.date_format("fecha", "yyyy-MM"))
            .groupBy("anio_mes", "product_category")
            .agg(*aggs)
            .orderBy("anio_mes", "product_category"))


def gold_ecommerce_segmento_categoria(df_silver):
    return (df_silver
            .groupBy("customer_segment", "product_category")
            .agg(F.count(F.lit(1)).alias("registros"),
                 F.sum("units_sold").alias("unidades_vendidas"),
                 F.round(F.avg("units_sold"), 2).alias("unidades_promedio"),
                 F.round(F.avg("price"), 2).alias("precio_promedio"),
                 F.sum("marketing_spend").alias("gasto_marketing_total"))
            .orderBy("customer_segment", "product_category"))


# --- Gold: Automobiles -------------------------------------------------------------------
def gold_automobiles_resumen_marca(df_silver):
    return (df_silver
            .groupBy("make")
            .agg(F.count(F.lit(1)).alias("registros"),
                 F.sum(F.col("price").isNull().cast("int")).alias("registros_sin_precio"),
                 F.round(F.avg("price"), 2).alias("precio_promedio"),
                 F.min("price").alias("precio_min"),
                 F.max("price").alias("precio_max"),
                 F.round(F.avg("horsepower"), 1).alias("horsepower_promedio"),
                 F.round(F.avg("city_mpg"), 1).alias("city_mpg_promedio"),
                 F.round(F.avg("highway_mpg"), 1).alias("highway_mpg_promedio"))
            .orderBy("make"))


def gold_automobiles_carroceria_combustible(df_silver):
    return (df_silver
            .groupBy("body_style", "fuel_type")
            .agg(F.count(F.lit(1)).alias("registros"),
                 F.round(F.avg("price"), 2).alias("precio_promedio"),
                 F.round(F.avg("horsepower"), 1).alias("horsepower_promedio"),
                 F.round(F.avg("engine_size"), 1).alias("engine_size_promedio"),
                 F.round(F.avg("city_mpg"), 1).alias("city_mpg_promedio"))
            .orderBy("body_style", "fuel_type"))
