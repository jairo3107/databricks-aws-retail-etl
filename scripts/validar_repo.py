"""Validación estática del repositorio (sin Databricks ni AWS).

Comprueba:
  - YAML sin claves duplicadas (bundle, job y workflows).
  - Opcional (--schema): bundle completo contra el JSON Schema oficial,
    generado con `databricks bundle schema`.
  - Referencias ${...} bien formadas y variables declaradas; {{...}} conocidas.
  - Por target: valores resueltos, aislamiento dev/prod y raíz RAW compartida.
  - Tareas -> notebooks existentes en proceso/, sincronizados por el bundle,
    con los módulos comunes también sincronizados.
  - Widgets leídos por cada notebook == parámetros declarados en el job.
  - Etapas del job, DAG sin ciclos, sin schedule y sin clusters (serverless).
  - Acciones de GitHub fijadas a SHA y despliegue solo manual.
  - Estructura de carpetas de entrega y ausencia de DBFS o Volúmenes.
  - Privacidad y credenciales: sin correos, tokens ni claves en los archivos publicables;
    principal enmascarado en Actions.
  - Escrituras solo hacia lakehouse/ (ruta_tabla) y sin borrado de archivos en proceso/.
  - Permisos separados: 04_grants solo concede USE CATALOG/USE SCHEMA/SELECT a
    grant_principal; los privilegios de ejecución (PrepAmb) no forman parte del job.
  - Enlaces Markdown relativos (archivo y ancla) y bloques de código cerrados.
  - Atributos git de los CSV (-text -whitespace) para que `git diff --check` del CI no falle.
  - Diagramas Mermaid coherentes con el job y las tablas; dashboard solo sobre Gold.

Uso: python scripts/validar_repo.py [--schema bundle_schema.json]
"""

import argparse
import ast
import fnmatch
import glob
import json
import os
import re
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "proceso"))

BUCKET = "databricks-retail-etl-2026-smart"
TARGETS = ("dev", "prod")
VARS_EXTERNAS = {"grant_principal"}  # sin default: llegan por --var / BUNDLE_VAR_*
REFS_DINAMICAS = {"job.run_id", "job.id", "job.name", "task.run_id", "task.name",
                  "job.start_time.iso_date", "job.start_time.iso_datetime", "job.trigger.type"}
ETAPAS = ("PrepAmb", "Extract_ecommerce", "Extract_automobiles", "Transform_ecommerce",
          "Transform_automobiles", "Load", "Grants")
CARPETAS = ("datasets", "dashboard", "reversion", ".github/workflows", "seguridad",
            "PrepAmb", "proceso", "certificaciones", "evidencias")

errores = []


def error(msg):
    errores.append(msg)
    print(f"ERROR  {msg}")


def ok(msg):
    print(f"OK     {msg}")


# --- YAML estricto ---------------------------------------------------------------
class CargadorEstricto(yaml.SafeLoader):
    pass


def _mapping_sin_duplicados(loader, node, deep=False):
    vistos = {}
    for k_node, _ in node.value:
        k = loader.construct_object(k_node, deep=deep)
        if k in vistos:
            raise yaml.constructor.ConstructorError(
                None, None, f"clave duplicada '{k}' (líneas {vistos[k] + 1} y {k_node.start_mark.line + 1})",
                k_node.start_mark)
        vistos[k] = k_node.start_mark.line
    return loader.construct_mapping(node, deep)


CargadorEstricto.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping_sin_duplicados)


def cargar_yaml(ruta):
    with open(ruta, encoding="utf-8") as f:
        return yaml.load(f, Loader=CargadorEstricto)


# --- Utilidades ---------------------------------------------------------------------
def recorrer_strings(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from recorrer_strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from recorrer_strings(v)
    elif isinstance(o, str):
        yield o


def resolver(texto, variables, target):
    def rep(m):
        ref = m.group(1)
        if ref == "bundle.target":
            return target
        if ref.startswith("var."):
            v = variables.get(ref[4:])
            return v if v is not None else f"<{ref[4:]}>"
        return m.group(0)
    return re.sub(r"\$\{([^}]+)\}", rep, texto)


def parametros_notebook(ruta):
    """Nombres de widget que lee un notebook (literales y comun.leer_parametros)."""
    import comun
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    nombres = set()
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call) or not isinstance(nodo.func, ast.Attribute):
            continue
        f = nodo.func
        if f.attr == "leer_parametros" and len(nodo.args) >= 2:
            valor = eval(compile(ast.Expression(nodo.args[1]), str(ruta), "eval"), {"comun": comun})
            nombres.update(valor)
            nombres.add("entorno")
        elif (f.attr in ("text", "get", "dropdown") and isinstance(f.value, ast.Attribute)
              and f.value.attr == "widgets" and nodo.args and isinstance(nodo.args[0], ast.Constant)):
            nombres.add(nodo.args[0].value)
    return nombres


def archivos_publicables():
    """Archivos que se publicarían: versionados o nuevos no ignorados por .gitignore.

    Excluye .venv/, .databricks/ y demás rutas ignoradas, que nunca llegan a GitHub.
    """
    import subprocess
    r = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                       cwd=RAIZ, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git ls-files falló: {r.stderr.strip()}")
    return [RAIZ / x for x in sorted(set(r.stdout.split("\0"))) if x and (RAIZ / x).is_file()]


def ancla_github(titulo):
    """Ancla que GitHub genera para un encabezado Markdown."""
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", titulo.strip())   # [texto](url) -> texto
    t = t.lower()
    t = re.sub(r"[^\w\- ]", "", t)                                       # quita puntuación (conserva letras con tilde)
    return t.replace(" ", "-")


def anclas_markdown(ruta):
    vistas, anclas = {}, set()
    en_codigo = False
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if linea.lstrip().startswith("```"):
            en_codigo = not en_codigo
            continue
        m = None if en_codigo else re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", linea)
        if m:
            base = ancla_github(m.group(2))
            n = vistas.get(base, 0)
            anclas.add(base if n == 0 else f"{base}-{n}")
            vistas[base] = n + 1
    return anclas


def excluido(rel, patrones):
    return any(fnmatch.fnmatch(rel, p) for p in patrones)


# --- Comprobaciones -------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", help="JSON Schema de `databricks bundle schema`")
    args = ap.parse_args()
    os.chdir(RAIZ)

    # 1. YAML sin duplicados
    archivos = ["databricks.yml", *sorted(glob.glob("resources/*.yml")), *sorted(glob.glob(".github/workflows/*.yml"))]
    docs = {}
    for a in archivos:
        try:
            docs[a] = cargar_yaml(RAIZ / a)
            ok(f"YAML sin claves duplicadas: {a}")
        except yaml.YAMLError as e:
            error(f"{a}: {e}")
    if errores:
        return 1

    bundle = docs["databricks.yml"]
    recursos = [a for a in archivos if a.startswith("resources/")]
    includes = bundle.get("include", [])
    for a in recursos:
        if not any(fnmatch.fnmatch(a, p) for p in includes):
            error(f"{a} no está incluido por 'include' de databricks.yml")

    jobs = {}
    for a in recursos:
        for k, v in (docs[a].get("resources", {}).get("jobs") or {}).items():
            if k in jobs:
                error(f"job '{k}' definido dos veces")
            jobs[k] = (a, v)
    if len(jobs) != 1:
        error(f"se esperaba un único job, hay {list(jobs)}")
        return 1
    clave_job, (archivo_job, job) = next(iter(jobs.items()))

    # 2. JSON Schema oficial
    if args.schema:
        import jsonschema
        completo = dict(bundle)
        completo["resources"] = {"jobs": {clave_job: job}}
        try:
            esquema = json.loads(Path(args.schema).read_text())
        except (OSError, json.JSONDecodeError) as e:
            error(f"--schema '{args.schema}' no es un JSON válido ({e}); genéralo con `databricks bundle schema`")
            return 1
        fallos = list(jsonschema.Draft7Validator(esquema).iter_errors(completo))
        for e in fallos[:20]:
            error(f"schema {'/'.join(map(str, e.absolute_path))}: {e.message[:200]}")
        if not fallos:
            ok("bundle conforme al JSON Schema oficial del CLI")

    # 3. Interpolaciones
    declaradas = set(bundle.get("variables", {}))
    usadas = set()
    for nombre, doc in [("databricks.yml", bundle), (archivo_job, docs[archivo_job])]:
        for s in recorrer_strings(doc):
            if s.count("${") != len(re.findall(r"\$\{[^{}]+\}", s)):
                error(f"{nombre}: referencia ${{...}} mal formada en '{s}'")
            for ref in re.findall(r"\$\{([^}]+)\}", s):
                if not re.fullmatch(r"(var|bundle|workspace|resources)(\.[A-Za-z0-9_\-]+)+", ref):
                    error(f"{nombre}: referencia desconocida ${{{ref}}}")
                elif ref.startswith("var."):
                    usadas.add(ref[4:])
                    if ref[4:] not in declaradas:
                        error(f"{nombre}: variable no declarada ${{{ref}}}")
            for ref in re.findall(r"\{\{\s*([^}]*?)\s*\}\}", s):
                if ref not in REFS_DINAMICAS:
                    error(f"{nombre}: referencia dinámica desconocida {{{{{ref}}}}}")
    if declaradas - usadas:
        error(f"variables declaradas sin uso: {sorted(declaradas - usadas)}")
    ok(f"interpolaciones revisadas; variables usadas = {sorted(usadas)}")

    # 4. Targets y aislamiento
    import comun
    params_job = {p["name"]: p.get("default", "") for p in job.get("parameters", [])}
    resueltos = {}
    for t in TARGETS:
        conf = bundle.get("targets", {}).get(t)
        if conf is None:
            error(f"falta el target '{t}'")
            continue
        valores = {k: (v or {}).get("default") for k, v in bundle["variables"].items()}
        valores.update(conf.get("variables") or {})
        sin_valor = sorted(k for k, v in valores.items() if v is None and k not in VARS_EXTERNAS)
        if sin_valor:
            error(f"target {t}: variables sin valor {sin_valor}")
        p = {k: resolver(str(v), valores, t) for k, v in params_job.items()}
        resueltos[t] = p
        try:
            comun.validar_aislamiento(p)
            ok(f"target {t}: aislamiento ({p['esquema_bronze']}, {p['esquema_silver']}, {p['esquema_gold']}, {p['lakehouse_root']})")
        except ValueError as e:
            error(f"target {t}: {e}")
        for k in ("raw_root", "lakehouse_root"):
            if not p[k].startswith(f"s3://{BUCKET}/"):
                error(f"target {t}: {k}='{p[k]}' fuera del bucket {BUCKET}")
        if (p["lakehouse_root"] + "/").startswith(p["raw_root"] + "/") or (p["raw_root"] + "/").startswith(p["lakehouse_root"] + "/"):
            error(f"target {t}: raw_root y lakehouse_root se solapan")
    if len(resueltos) == 2:
        d, pr = resueltos["dev"], resueltos["prod"]
        if d["raw_root"] != pr["raw_root"]:
            error("raw_root distinto entre dev y prod (debe ser compartido)")
        for k in ("esquema_bronze", "esquema_silver", "esquema_gold", "lakehouse_root"):
            if d[k] == pr[k]:
                error(f"dev y prod comparten {k}='{d[k]}'")
        if (d["lakehouse_root"] + "/").startswith(pr["lakehouse_root"] + "/") or \
           (pr["lakehouse_root"] + "/").startswith(d["lakehouse_root"] + "/"):
            error("lakehouse_root de dev y prod se solapan")
        ok(f"RAW compartido {d['raw_root']}; lakehouse dev/prod separados")
    if "root_path" not in (bundle["targets"]["prod"].get("workspace") or {}):
        error("prod: falta workspace.root_path (obligatorio en mode: production)")

    # 5. Tareas, notebooks y sincronización
    exclusiones = (bundle.get("sync") or {}).get("exclude", [])
    tareas = {t["task_key"]: t for t in job.get("tasks", [])}
    faltan = [e for e in ETAPAS if e not in tareas]
    if faltan:
        error(f"faltan etapas en el job: {faltan}")
    for clave in ("schedule", "trigger", "continuous", "job_clusters"):
        if clave in job:
            error(f"el job no debe declarar '{clave}'")
    leidos_total = set()
    for k, t in tareas.items():
        for clave in ("new_cluster", "existing_cluster_id", "job_cluster_key", "environment_key"):
            if clave in t:
                error(f"tarea {k}: declara '{clave}' (se espera serverless sin cluster)")
        for d in t.get("depends_on", []):
            if d["task_key"] not in tareas:
                error(f"tarea {k}: depende de '{d['task_key']}', que no existe")
        nb = (RAIZ / archivo_job).parent / t["notebook_task"]["notebook_path"]
        rel = nb.resolve().relative_to(RAIZ).as_posix()
        if not rel.startswith("proceso/"):
            error(f"tarea {k}: {rel} no está en proceso/")
        if not nb.exists():
            error(f"tarea {k}: no existe {rel}")
            continue
        if nb.read_text(encoding="utf-8").splitlines()[0] != "# Databricks notebook source":
            error(f"{rel}: falta la cabecera '# Databricks notebook source'")
        if excluido(rel, exclusiones):
            error(f"{rel} está excluido por sync.exclude")
        leidos = parametros_notebook(nb)
        leidos_total |= leidos
        no_declarados = sorted(leidos - set(params_job))
        if no_declarados:
            error(f"tarea {k}: {rel} lee widgets que no son parámetros del job: {no_declarados}")
        else:
            ok(f"tarea {k:22} -> {rel}  widgets={sorted(leidos)}")
    sin_uso = sorted(set(params_job) - leidos_total)
    if sin_uso:
        error(f"parámetros del job que ningún notebook lee: {sin_uso}")
    for modulo in ("proceso/comun.py", "proceso/transformaciones.py"):
        if not (RAIZ / modulo).exists() or excluido(modulo, exclusiones):
            error(f"{modulo} no existe o no se sincroniza")
    # DAG sin ciclos
    visitado, en_curso = set(), set()

    def visitar(k):
        if k in en_curso:
            error(f"ciclo en el DAG en {k}")
            return
        if k in visitado or k not in tareas:
            return
        en_curso.add(k)
        for d in tareas[k].get("depends_on", []):
            visitar(d["task_key"])
        en_curso.discard(k)
        visitado.add(k)
    for k in tareas:
        visitar(k)
    if tareas["Extract_ecommerce"].get("depends_on") != tareas["Extract_automobiles"].get("depends_on"):
        error("las dos ingestas deberían depender solo de PrepAmb (paralelas)")
    if {d["task_key"] for d in tareas["Load"].get("depends_on", [])} != {"Transform_ecommerce", "Transform_automobiles"}:
        error("Load debe esperar a las dos transformaciones")

    # 6. Workflows de GitHub
    for a in [x for x in archivos if x.startswith(".github/")]:
        texto = (RAIZ / a).read_text(encoding="utf-8")
        for uso in re.findall(r"uses:\s*(\S+)", texto):
            if not re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", uso):
                error(f"{a}: acción sin SHA fijado: {uso}")
        disparadores = docs[a].get(True) or docs[a].get("on")  # PyYAML lee 'on' como True
        if a.endswith("deploy-prod.yml"):
            if set(disparadores) != {"workflow_dispatch"}:
                error(f"{a}: el despliegue debe ser solo manual (workflow_dispatch); tiene {list(disparadores)}")
        elif "secrets." in texto:
            error(f"{a}: el CI local no debe usar secretos")
    ok("workflows: acciones fijadas a SHA; despliegue solo manual; CI sin secretos")

    # 7. Estructura y RAW
    for c in CARPETAS:
        d = RAIZ / c
        if not d.is_dir() or not any(d.iterdir()):
            error(f"carpeta requerida ausente o vacía: {c}/")
    if not list((RAIZ / "PrepAmb").glob("*.sql")):
        error("PrepAmb/ debe contener un archivo SQL")
    for f in (RAIZ / "proceso").glob("*.py"):
        if re.search(r"dbfs:|/dbfs/|/Volumes/", f.read_text(encoding="utf-8")):
            error(f"{f.relative_to(RAIZ)} usa DBFS o Volúmenes")
    for f in list((RAIZ / "reversion").glob("*")) + list((RAIZ / "seguridad").glob("*")):
        if f.name in json.dumps(job):
            error(f"{f.relative_to(RAIZ)} no debe formar parte del job")
    ok("estructura de entrega presente; sin DBFS ni Volúmenes; reversión y seguridad fuera del job")

    # 8. Privacidad: el repo es público; no debe contener correos ni el principal lector
    patron_correo = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
    for f in archivos_publicables():
        rel = f.relative_to(RAIZ).as_posix()
        if f.suffix.lower() not in (
                ".py", ".md", ".yml", ".yaml", ".sql", ".txt", ".toml", ".json", ".lock", ""):
            continue
        for n, linea in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            for m in patron_correo.finditer(linea):
                if re.search(r"@example\.(com|org|net)$", m.group(0), re.IGNORECASE):
                    continue  # dominios reservados RFC 2606, solo para pruebas
                error(f"{rel}:{n}: dirección de correo en el repositorio ({m.group(0)[:3]}…)")
    patron_credencial = re.compile(
        r"dapi[0-9a-f]{32}|\b(AKIA|ASIA)[0-9A-Z]{16}\b|aws_secret_access_key|"
        r"\b(ghp_|gho_|ghs_|github_pat_)[A-Za-z0-9_]{20,}|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY")
    for f in archivos_publicables():
        rel = f.relative_to(RAIZ).as_posix()
        if rel == "scripts/validar_repo.py" or f.suffix.lower() == ".csv":
            continue  # este archivo contiene los patrones; los CSV no son texto de configuración
        for n, linea in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if patron_credencial.search(linea):
                error(f"{rel}:{n}: posible credencial versionada (valor no mostrado)")
    deploy = (RAIZ / ".github/workflows/deploy-prod.yml").read_text(encoding="utf-8")
    if "::add-mask::$BUNDLE_VAR_grant_principal" not in deploy:
        error("deploy-prod.yml debe enmascarar BUNDLE_VAR_grant_principal en los logs")
    if "current-user me" in deploy and "::add-mask::$v" not in deploy:
        error("deploy-prod.yml imprime la identidad sin enmascararla")
    if "default" in (bundle["variables"].get("grant_principal") or {}):
        error("grant_principal no debe tener default en databricks.yml")
    ok("privacidad: sin correos ni credenciales en archivos publicables; principal e identidad enmascarados en Actions")

    # 9. Escrituras y permisos
    for f in sorted((RAIZ / "proceso").glob("*.py")):
        rel = f.relative_to(RAIZ).as_posix()
        texto = f.read_text(encoding="utf-8")
        if re.search(r"dbutils\.fs\.(rm|mv|cp|put|mkdirs)\b|\bshutil\.|os\.remove", texto):
            error(f"{rel}: operación de archivos (borrado, copia o escritura) no permitida en proceso/")
        if f.name != "comun.py" and re.search(r"\.write\b|\.save\(|\.saveAsTable\(|insertInto\(", texto):
            error(f"{rel}: escribe sin pasar por comun.escribir_tabla_externa")
        codigo = "\n".join(l for l in texto.splitlines() if not l.lstrip().startswith("#"))
        if re.search(r"\b(DROP|TRUNCATE|DELETE\s+FROM)\b", codigo):
            error(f"{rel}: DROP/TRUNCATE/DELETE en la ejecución normal")
        # Cada escritura debe ir a comun.ruta_tabla (lakehouse/<entorno>/...), nunca a ruta_raw
        arbol = ast.parse(texto)
        asignadas = {}
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Assign) and len(nodo.targets) == 1 and isinstance(nodo.targets[0], ast.Name):
                asignadas[nodo.targets[0].id] = ast.unparse(nodo.value)
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute) \
                    and nodo.func.attr == "escribir_tabla_externa" and len(nodo.args) == 4:
                destino = ast.unparse(nodo.args[3])
                destino = asignadas.get(destino, destino)
                if not destino.startswith("comun.ruta_tabla("):
                    error(f"{rel}: escribir_tabla_externa con ruta '{destino}' (debe ser comun.ruta_tabla)")
    grants = (RAIZ / "proceso/04_grants.py").read_text(encoding="utf-8")
    privilegios = {x.strip() for m in re.findall(r"GRANT\s+([A-Z_ ,]+?)\s+ON\b", grants) for x in m.split(",")}
    if not privilegios or privilegios - {"USE CATALOG", "USE SCHEMA", "SELECT"}:
        error(f"04_grants.py concede privilegios fuera del mínimo: {sorted(privilegios)}")
    destinos = set(re.findall(r"\bTO\s+`\{(\w+)\}`", grants))
    if destinos != {"principal"} or 'principal = p["grant_principal"]' not in grants:
        error(f"04_grants.py debe conceder solo a grant_principal (destinos: {sorted(destinos)})")
    if "validar_principal(" not in grants:
        error("04_grants.py debe validar grant_principal antes de conceder")
    if any(f.name in json.dumps(job) for f in (RAIZ / "PrepAmb").glob("*")):
        error("PrepAmb/ (permisos de ejecución, manual) no debe formar parte del job")
    ok(f"escrituras solo a lakehouse vía ruta_tabla; 04_grants concede {sorted(privilegios)} solo a grant_principal")

    # 10. Enlaces Markdown relativos (archivo y ancla) y bloques de código cerrados
    total = 0
    for f in archivos_publicables():
        if f.suffix.lower() != ".md":
            continue
        rel = f.relative_to(RAIZ).as_posix()
        texto = f.read_text(encoding="utf-8")
        if sum(1 for l in texto.splitlines() if l.lstrip().startswith("```")) % 2:
            error(f"{rel}: bloque de código ``` sin cerrar")
        sin_codigo = re.sub(r"```.*?```", "", texto, flags=re.S)
        sin_codigo = re.sub(r"``.*?``|`[^`\n]*`", "", sin_codigo)
        for destino in re.findall(r"\]\(([^)\s]+)\)", sin_codigo):
            if re.match(r"^[a-z]+://|^mailto:", destino):
                continue
            total += 1
            ruta, _, ancla = destino.partition("#")
            objetivo = (f.parent / ruta).resolve() if ruta else f
            if not objetivo.exists():
                error(f"{rel}: enlace roto a '{destino}' (no existe)")
            elif ancla and objetivo.suffix == ".md" and ancla not in anclas_markdown(objetivo):
                error(f"{rel}: ancla inexistente '#{ancla}' en {objetivo.relative_to(RAIZ).as_posix()}")
    ok(f"enlaces Markdown relativos revisados: {total}")

    # 11. Los CSV (CRLF) deben quedar fuera de `git diff --check` y sin normalizar, o el CI falla
    import subprocess
    csvs = sorted(str(p.relative_to(RAIZ)) for p in (RAIZ / "datasets").rglob("*.csv"))
    r = subprocess.run(["git", "check-attr", "text", "whitespace", "--", *csvs],
                       cwd=RAIZ, capture_output=True, text=True)
    for linea in r.stdout.splitlines():
        if not linea.endswith(": unset"):
            error(f".gitattributes: se esperaba '-text -whitespace' para los CSV ({linea})")
    ok(f"{len(csvs)} CSV con '-text -whitespace' en .gitattributes")

    # 12. Diagramas y dashboard coherentes con el job y con comun.TABLAS
    diag = RAIZ / "docs/diagramas.md"
    if not diag.exists():
        error("falta docs/diagramas.md")
    else:
        texto = diag.read_text(encoding="utf-8")
        bloques = re.findall(r"```mermaid\n(.*?)```", texto, flags=re.S)
        dag = [b for b in bloques if "%% dag-job" in b]
        if len(dag) != 1:
            error("docs/diagramas.md: debe haber exactamente un bloque mermaid con '%% dag-job'")
        else:
            aristas = set(re.findall(r"^\s*(\w+)\s*-->\s*(\w+)\s*$", dag[0], flags=re.M))
            esperadas = {(d["task_key"], k) for k, t in tareas.items() for d in t.get("depends_on", [])}
            if aristas != esperadas:
                error(f"diagrama del job desalineado: sobran {sorted(aristas - esperadas)}, faltan {sorted(esperadas - aristas)}")
            for k, t in tareas.items():
                if Path(t["notebook_task"]["notebook_path"]).name not in dag[0]:
                    error(f"diagrama del job: falta el notebook de {k}")
        for capa, tablas in comun.TABLAS.items():
            for t in tablas:
                if f"{capa}.{t}" not in texto:
                    error(f"docs/diagramas.md: falta la tabla {capa}.{t}")
        ok(f"diagramas: {len(bloques)} bloques mermaid; DAG del job y tablas coherentes")
    sql_dash = sorted((RAIZ / "dashboard/sql").glob("*.sql"))
    usadas_dash = {t for f in sql_dash for t in re.findall(r"workspace\.\w+\.(\w+)", f.read_text(encoding="utf-8"))}
    if not sql_dash or usadas_dash != set(comun.TABLAS["gold"]):
        error(f"dashboard/sql: debe consultar exactamente las tablas Gold (usa {sorted(usadas_dash)})")
    for f in sql_dash:
        if re.search(r"workspace\.(?!dev_gold\.|gold\.)\w+\.", f.read_text(encoding="utf-8")):
            error(f"{f.relative_to(RAIZ)}: el dashboard solo debe leer esquemas Gold")
    for requerido in ("evidencias/consultas_evidencia.sql", "dashboard/README.md", "certificaciones/README.md"):
        if not (RAIZ / requerido).exists():
            error(f"falta {requerido}")
    ok(f"dashboard: {len(sql_dash)} consultas solo sobre Gold; archivos de entrega presentes")

    print(f"\n{'FALLÓ' if errores else 'CORRECTO'}: {len(errores)} error(es)")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
