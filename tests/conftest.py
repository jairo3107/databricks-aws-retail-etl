"""Configuración común de pytest.

Las pruebas de tests/test_transformaciones.py arrancan un Spark local y
necesitan Java 17. Si no hay Java, se aborta con un mensaje claro en lugar
del error opaco de Py4J. No se omiten pruebas en silencio.
"""

import os
import shutil

import pytest


def _java_disponible():
    java_home = os.environ.get("JAVA_HOME")
    if java_home and os.path.exists(os.path.join(java_home, "bin", "java")):
        return True
    return shutil.which("java") is not None


def pytest_collection_modifyitems(config, items):
    necesitan_spark = [i for i in items if "spark" in getattr(i, "fixturenames", ())]
    if necesitan_spark and not _java_disponible():
        raise pytest.UsageError(
            f"{len(necesitan_spark)} pruebas necesitan Spark local y no se encontró Java "
            "(ni JAVA_HOME ni 'java' en PATH). Instala Java 17 o ejecuta solo las pruebas sin Spark: "
            "uv run pytest -q tests/test_comun.py tests/test_validar_repo.py"
        )
