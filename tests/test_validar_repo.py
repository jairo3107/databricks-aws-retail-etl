"""Pruebas del validador estático scripts/validar_repo.py."""

import sys
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import validar_repo  # noqa: E402


def test_detecta_clave_duplicada(tmp_path):
    f = tmp_path / "x.yml"
    f.write_text("variables:\n  raw_root: a\n  raw_root: b\n")
    with pytest.raises(yaml.YAMLError, match="duplicada 'raw_root'"):
        validar_repo.cargar_yaml(f)


def test_repositorio_consistente(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["validar_repo.py"])
    validar_repo.errores.clear()
    assert validar_repo.main() == 0


def test_validador_no_requiere_pyspark():
    """validar_repo.py debe funcionar en un entorno sin PySpark (comun.py lo importa de forma diferida)."""
    import subprocess
    codigo = (
        "import sys; sys.modules['pyspark'] = None; "          # cualquier 'import pyspark' falla
        "sys.argv = ['validar_repo.py']; sys.path.insert(0, 'scripts'); "
        "import validar_repo; sys.exit(validar_repo.main())"
    )
    r = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert "CORRECTO: 0 error(es)" in r.stdout
