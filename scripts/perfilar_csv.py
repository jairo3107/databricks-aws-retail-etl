"""Perfilado local, de solo lectura, de los CSV en datasets/.

Usa solo la biblioteca estándar. No modifica los archivos de entrada.

Uso:
    python -I scripts/perfilar_csv.py [datasets] [--muestra N] [--json salida.json]
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

NULOS = {"", "na", "n/a", "nan", "null", "none", "?", "-"}
RE_INT = re.compile(r"^[+-]?\d+$")
RE_DEC = re.compile(r"^[+-]?(\d+[.,]\d*|[.,]\d+)([eE][+-]?\d+)?$")
RE_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?$|^\d{1,2}/\d{1,2}/\d{2,4}$")
RE_BOOL = re.compile(r"^(true|false|yes|no|si|sí|y|n)$", re.IGNORECASE)
ENCODINGS = ("utf-8-sig", "latin-1")


def detectar_encoding(ruta):
    for enc in ENCODINGS:
        try:
            with open(ruta, encoding=enc) as f:
                f.read(1 << 20)
            return enc
        except UnicodeDecodeError:
            continue
    return "desconocido"


def tipo_valor(v):
    if RE_INT.match(v):
        return "entero"
    if RE_DEC.match(v):
        return "decimal"
    if RE_FECHA.match(v):
        return "fecha/hora"
    if RE_BOOL.match(v):
        return "booleano"
    return "texto"


def tipo_columna(tipos):
    if not tipos:
        return "vacía"
    if tipos <= {"entero"}:
        return "entero"
    if tipos <= {"entero", "decimal"}:
        return "decimal"
    if len(tipos) == 1:
        return next(iter(tipos))
    return "texto (mixto: " + ", ".join(sorted(tipos)) + ")"


def perfilar(ruta, muestra):
    enc = detectar_encoding(ruta)
    with open(ruta, encoding=enc, newline="") as f:
        cabecera_txt = f.read(64 * 1024)
        f.seek(0)
        sniffer = csv.Sniffer()
        try:
            dialecto = sniffer.sniff(cabecera_txt, delimiters=",;|\t")
            sep = dialecto.delimiter
        except csv.Error:
            dialecto, sep = csv.excel, ","
        try:
            tiene_cabecera = sniffer.has_header(cabecera_txt)
        except csv.Error:
            tiene_cabecera = None

        lector = csv.reader(f, dialecto)
        primera = next(lector, [])
        nombres = primera if tiene_cabecera is not False else [f"_c{i}" for i in range(len(primera))]
        n_cols = len(nombres)
        nulos = [0] * n_cols
        tipos = [set() for _ in range(n_cols)]
        ejemplos = [[] for _ in range(n_cols)]
        filas = filas_irregulares = 0

        filas_datos = lector if tiene_cabecera is not False else _encadenar(primera, lector)
        for fila in filas_datos:
            filas += 1
            if len(fila) != n_cols:
                filas_irregulares += 1
            if muestra and filas > muestra:
                continue  # sigue contando filas, deja de perfilar
            for i in range(min(n_cols, len(fila))):
                v = fila[i].strip()
                if v.lower() in NULOS:
                    nulos[i] += 1
                    continue
                tipos[i].add(tipo_valor(v))
                if len(ejemplos[i]) < 3 and v not in ejemplos[i]:
                    ejemplos[i].append(v)

    perfiladas = min(filas, muestra) if muestra else filas
    return {
        "archivo": str(ruta),
        "tamano_bytes": ruta.stat().st_size,
        "encoding": enc,
        "separador": sep,
        "cabecera_detectada": tiene_cabecera,
        "filas_datos": filas,
        "filas_perfiladas": perfiladas,
        "filas_con_n_columnas_distinto": filas_irregulares,
        "columnas": [
            {
                "nombre": nombres[i],
                "tipo_aparente": tipo_columna(tipos[i]),
                "nulos": nulos[i],
                "pct_nulos": round(100 * nulos[i] / perfiladas, 2) if perfiladas else None,
                "ejemplos": ejemplos[i],
            }
            for i in range(n_cols)
        ],
    }


def _encadenar(primera, resto):
    yield primera
    yield from resto


def main():
    p = argparse.ArgumentParser()
    p.add_argument("raiz", nargs="?", default="datasets")
    p.add_argument("--muestra", type=int, default=0, help="filas a perfilar (0 = todas)")
    p.add_argument("--json", help="ruta para guardar el resultado en JSON")
    args = p.parse_args()

    archivos = sorted(Path(args.raiz).rglob("*.csv"))
    if not archivos:
        print(f"No se encontraron archivos .csv en {args.raiz}/", file=sys.stderr)
        return 1

    resultados = [perfilar(a, args.muestra) for a in archivos]
    for r in resultados:
        print(f"\n## {r['archivo']}  ({r['tamano_bytes']} bytes, {r['encoding']})")
        print(f"separador={r['separador']!r} cabecera={r['cabecera_detectada']} "
              f"filas={r['filas_datos']} irregulares={r['filas_con_n_columnas_distinto']}")
        for c in r["columnas"]:
            print(f"  - {c['nombre']:<30} {c['tipo_aparente']:<22} "
                  f"nulos={c['nulos']} ({c['pct_nulos']}%)  ej={c['ejemplos']}")

    if args.json:
        Path(args.json).write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
