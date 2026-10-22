"""Pruebas de parámetros y aislamiento dev/prod de proceso/comun.py (sin Spark)."""

import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "proceso"))

import comun  # noqa: E402

BASE = {
    "catalogo": "cat",
    "raw_root": "s3://databricks-retail-etl-2026-smart/raw",
}
DEV = {**BASE, "entorno": "dev", "esquema_bronze": "dev_bronze", "esquema_silver": "dev_silver",
       "esquema_gold": "dev_gold", "lakehouse_root": "s3://databricks-retail-etl-2026-smart/lakehouse/dev"}
PROD = {**BASE, "entorno": "prod", "esquema_bronze": "bronze", "esquema_silver": "silver",
        "esquema_gold": "gold", "lakehouse_root": "s3://databricks-retail-etl-2026-smart/lakehouse/prod"}


def dbutils_falso(valores):
    widgets = types.SimpleNamespace(text=lambda n, d: None, get=lambda n: valores.get(n, ""))
    return types.SimpleNamespace(widgets=widgets)


@pytest.mark.parametrize("p", [DEV, PROD])
def test_aislamiento_valido(p):
    comun.validar_aislamiento(p)


@pytest.mark.parametrize("cambio", [
    {"entorno": "dev", "esquema_gold": "gold"},                                         # dev -> esquema prod
    {"entorno": "dev", "lakehouse_root": PROD["lakehouse_root"]},                       # dev -> ruta prod
    {"entorno": "prod", "esquema_bronze": "dev_bronze"},                                # prod -> esquema dev
    {"entorno": "prod", "lakehouse_root": "s3://databricks-retail-etl-2026-smart/lakehouse"},
    {"entorno": "test"},
])
def test_aislamiento_violado(cambio):
    base = DEV if cambio.get("entorno") == "dev" else PROD
    with pytest.raises(ValueError):
        comun.validar_aislamiento({**base, **cambio})


def test_leer_parametros_exige_entorno_y_normaliza():
    valores = {**DEV, "lakehouse_root": DEV["lakehouse_root"]}
    p = comun.leer_parametros(dbutils_falso(valores), comun.PARAMS_BASE)
    assert p["entorno"] == "dev" and p["esquema_bronze"] == "dev_bronze"
    with pytest.raises(ValueError, match="entorno"):
        comun.leer_parametros(dbutils_falso({k: v for k, v in DEV.items() if k != "entorno"}), comun.PARAMS_BASE)


def test_leer_parametros_rechaza_rutas_no_s3():
    with pytest.raises(ValueError, match="s3://"):
        comun.leer_parametros(dbutils_falso({**DEV, "raw_root": "dbfs:/raw"}), comun.PARAMS_BASE)


def test_rutas_por_entorno():
    assert comun.ruta_tabla(DEV, "gold", "t") == "s3://databricks-retail-etl-2026-smart/lakehouse/dev/gold/t"
    assert comun.ruta_tabla(PROD, "gold", "t") == "s3://databricks-retail-etl-2026-smart/lakehouse/prod/gold/t"
    assert comun.nombre_tabla(DEV, "gold", "t") == "`cat`.`dev_gold`.`t`"


# --- grant_principal ---------------------------------------------------------------
@pytest.mark.parametrize("nombre, tipo", [
    ("retail_etl_readers", "grupo"),
    ("lector@example.com", "usuario"),
    ("0f6c2d1e-8a3b-4c5d-9e7f-1a2b3c4d5e6f", "service_principal"),
])
def test_principal_valido(nombre, tipo):
    assert comun.validar_principal(nombre) == tipo


@pytest.mark.parametrize("nombre", [
    "admins", "users", "Account Users",                    # sistema: acceso indiscriminado
    "users-clone-2026-08-21-1611-UTC",                     # grupo local generado por Databricks
    "retail_etl_readers (workspace)",                      # grupo local renombrado en una migración
    "", "grupo`; DROP",
])
def test_principal_rechazado(nombre):
    with pytest.raises(ValueError):
        comun.validar_principal(nombre)


def test_enmascarar_correo():
    assert comun.enmascarar("lector@example.com") == "l***@example.com"
    assert comun.enmascarar("retail_etl_readers") == "retail_etl_readers"


def test_aislamiento_rechaza_lakehouse_dentro_de_raw():
    # La External Location permite escribir en todo el bucket: el código impide escribir dentro de RAW.
    with pytest.raises(ValueError, match="se solapan"):
        comun.validar_aislamiento({**PROD, "raw_root": "s3://databricks-retail-etl-2026-smart/lakehouse"})
