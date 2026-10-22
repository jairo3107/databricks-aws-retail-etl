"""Utilidades compartidas por los notebooks de proceso/.

Módulo Python plano (sin cabecera de notebook): los notebooks lo importan con
`import comun`, lo que requiere DBR 14.3 LTS+ o serverless (el directorio del
notebook está en sys.path). No contiene lógica de negocio: esa vive en
transformaciones.py.

PySpark solo se importa dentro de las funciones que operan sobre DataFrames,
de modo que los helpers puros (parámetros, aislamiento, principal) se pueden
usar y validar sin Spark, por ejemplo desde scripts/validar_repo.py.
"""

import re

# --- Inventario de tablas: única fuente para load, grants y reversión ---------
CAPAS = ("bronze", "silver", "gold")

TABLAS = {
    "bronze": ["ecommerce_ventas", "automobiles_specs"],
    "silver": ["ecommerce_ventas", "automobiles_specs"],
    "gold": [
        "ecommerce_ventas_mensuales_categoria",
        "ecommerce_ventas_segmento_categoria",
        "automobiles_resumen_marca",
        "automobiles_resumen_carroceria_combustible",
    ],
}

# Parámetros del job; esquemas se resuelven por capa con esquema_<capa>.
# `entorno` lo añade siempre leer_parametros().
PARAMS_BASE = ("catalogo", "esquema_bronze", "esquema_silver", "esquema_gold",
               "raw_root", "lakehouse_root")

# Aislamiento lógico dev/prod en un único workspace (Free Edition).
ENTORNOS = ("dev", "prod")
PREFIJO_DEV = "dev_"

_RE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Principal que recibe lectura sobre Gold (grant_principal). En UC solo son válidos los
# grupos de CUENTA, los usuarios (correo) y los service principals (application ID).
# Se rechazan los grupos de sistema (acceso indiscriminado) y los nombres típicos de
# grupos locales del workspace, que UC no admite.
PRINCIPALES_PROHIBIDOS = {"admins", "users", "account users"}
_RE_GRUPO_LOCAL = re.compile(r"(-clone-\d{4}-\d{2}-\d{2}-\d{4}-utc|\s\(workspace\))$", re.IGNORECASE)
_RE_CORREO = re.compile(r"^[^@\s`]+@[^@\s`]+\.[^@\s`]+$")
_RE_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


# --- Parámetros ----------------------------------------------------------------
def leer_parametros(dbutils, nombres):
    """Lee widgets (o parámetros del job), falla si alguno está vacío y valida el entorno."""
    nombres = ("entorno",) + tuple(n for n in nombres if n != "entorno")
    for n in nombres:
        dbutils.widgets.text(n, "")
    valores = {n: dbutils.widgets.get(n).strip() for n in nombres}
    faltan = [n for n, v in valores.items() if not v]
    if faltan:
        raise ValueError(f"Parámetros obligatorios sin valor: {faltan}. "
                         "Configúralos en el job (bundle) o en los widgets.")
    for n in ("catalogo", "esquema_bronze", "esquema_silver", "esquema_gold"):
        if n in valores and not _RE_IDENT.match(valores[n]):
            raise ValueError(f"'{n}'='{valores[n]}' no es un identificador válido")
    for n in ("raw_root", "lakehouse_root"):
        if n in valores:
            if not valores[n].startswith("s3://"):
                raise ValueError(f"'{n}' debe ser una URI s3:// (recibido '{valores[n]}')")
            valores[n] = valores[n].rstrip("/")
    validar_aislamiento(valores)
    return valores


def validar_aislamiento(p):
    """Impide que dev toque esquemas o rutas de prod, y al revés.

    dev  -> esquemas con prefijo dev_ y lakehouse_root terminado en /dev
    prod -> esquemas sin prefijo dev_ y lakehouse_root terminado en /prod
    """
    entorno = p["entorno"]
    if entorno not in ENTORNOS:
        raise ValueError(f"entorno='{entorno}' no válido; opciones {ENTORNOS}")
    errores = []
    for n in ("esquema_bronze", "esquema_silver", "esquema_gold"):
        if n in p and p[n].startswith(PREFIJO_DEV) != (entorno == "dev"):
            regla = "debe" if entorno == "dev" else "no debe"
            errores.append(f"{n}='{p[n]}' {regla} empezar por '{PREFIJO_DEV}' en {entorno}")
    if "lakehouse_root" in p and not p["lakehouse_root"].endswith("/" + entorno):
        errores.append(f"lakehouse_root='{p['lakehouse_root']}' debe terminar en '/{entorno}'")
    # Los notebooks solo leen RAW. La External Location permite escribir en todo el bucket,
    # así que la separación entre RAW y las tablas se exige aquí, en el código.
    if "raw_root" in p and "lakehouse_root" in p:
        raw, lake = p["raw_root"].rstrip("/") + "/", p["lakehouse_root"].rstrip("/") + "/"
        if raw.startswith(lake) or lake.startswith(raw):
            errores.append(f"raw_root y lakehouse_root se solapan ('{p['raw_root']}', '{p['lakehouse_root']}')")
    if errores:
        raise ValueError("Aislamiento de entornos violado: " + "; ".join(errores))


def tipo_principal(nombre):
    """'usuario' (correo), 'service_principal' (application ID) o 'grupo'."""
    if _RE_CORREO.match(nombre):
        return "usuario"
    if _RE_UUID.match(nombre):
        return "service_principal"
    return "grupo"


def validar_principal(nombre):
    """Valida grant_principal y devuelve su tipo. No consulta el workspace."""
    nombre = nombre.strip()
    if not nombre or "`" in nombre:
        raise ValueError("grant_principal vacío o con comillas invertidas")
    if nombre.casefold() in PRINCIPALES_PROHIBIDOS:
        raise ValueError(f"grant_principal='{nombre}' es un grupo de sistema: daría acceso indiscriminado. "
                         "Usa un grupo de cuenta dedicado (p. ej. retail_etl_readers), un usuario o un service principal.")
    if _RE_GRUPO_LOCAL.search(nombre):
        raise ValueError(f"grant_principal='{nombre}' tiene nombre de grupo local del workspace (origen Workspace); "
                         "Unity Catalog no admite conceder acceso a datos a grupos locales.")
    return tipo_principal(nombre)


def enmascarar(nombre):
    """Oculta la parte local de un correo para que no quede en logs ni capturas."""
    if tipo_principal(nombre) == "usuario":
        local, dominio = nombre.split("@", 1)
        return f"{local[:1]}***@{dominio}"
    return nombre


def nombre_tabla(p, capa, tabla):
    return f"`{p['catalogo']}`.`{p['esquema_' + capa]}`.`{tabla}`"


def ruta_tabla(p, capa, tabla):
    return f"{p['lakehouse_root']}/{capa}/{tabla}"


def ruta_raw(p, relativa):
    return f"{p['raw_root']}/{relativa.lstrip('/')}"


# --- Escritura -----------------------------------------------------------------
def escribir_tabla_externa(spark, df, nombre, ruta):
    """Sobrescribe una tabla Delta externa de UC ubicada en `ruta`.

    La primera vez la crea con LOCATION explícita. Después reescribe la tabla
    existente (nueva versión Delta; el historial se conserva, no se borra la
    ruta) y comprueba que su ubicación sigue siendo la esperada.
    """
    if spark.catalog.tableExists(nombre.replace("`", "")):
        ubicacion = spark.sql(f"DESCRIBE DETAIL {nombre}").first()["location"].rstrip("/")
        if ubicacion != ruta.rstrip("/"):
            raise RuntimeError(f"{nombre} ya existe en '{ubicacion}', distinta de '{ruta}'. "
                               "Revísalo manualmente; no se sobrescribe.")
        (df.write.format("delta").mode("overwrite")
           .option("overwriteSchema", "true").saveAsTable(nombre))
    else:
        (df.write.format("delta").mode("overwrite")
           .option("path", ruta).saveAsTable(nombre))
    tabla = spark.catalog.getTable(nombre.replace("`", ""))
    ubicacion = spark.sql(f"DESCRIBE DETAIL {nombre}").first()["location"].rstrip("/")
    if tabla.tableType != "EXTERNAL" or ubicacion != ruta.rstrip("/"):
        raise RuntimeError(f"{nombre} quedó como {tabla.tableType} en '{ubicacion}'; se esperaba EXTERNAL en '{ruta}'")
    print(f"OK  {nombre}  ->  {ruta}")


# --- Validaciones ----------------------------------------------------------------
def validar_columnas(df, esperadas, contexto):
    reales = [c for c in df.columns if not c.startswith("_")]
    if reales != list(esperadas):
        raise ValueError(f"[{contexto}] Columnas inesperadas.\n  esperadas={list(esperadas)}\n  reales={reales}")


def validar_tipos(df, esperados, contexto):
    reales = dict(df.dtypes)
    diferencias = {c: (t, reales.get(c)) for c, t in esperados.items() if reales.get(c) != t}
    if diferencias:
        raise TypeError(f"[{contexto}] Tipos distintos (esperado, real): {diferencias}")


def conteo_nulos(df, columnas=None):
    from pyspark.sql import functions as F

    columnas = columnas or df.columns
    fila = df.select([F.sum(F.col(c).isNull().cast("int")).alias(c) for c in columnas]).first()
    return {c: int(fila[c] or 0) for c in columnas}


def exigir(condicion, mensaje):
    if not condicion:
        raise AssertionError(mensaje)
    print(f"CHECK OK  {mensaje}")
