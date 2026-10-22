# Decisiones arquitectónicas y cuestiones por confirmar

Aquí se registran las diferencias con el enunciado o con el repositorio de referencia. **No están resueltas en el código**:
cada una necesita una confirmación humana (del equipo o del profesor). No se ha cambiado nada para «resolverlas» por cuenta propia.

## D1. Acceso a RAW: Managed Identity (enunciado) frente a IAM Role de AWS (implementación)

**Pendiente de confirmar con el profesor.**

El enunciado menciona **Managed Identity** para acceder a Raw, que es el mecanismo de Azure (Access Connector para Azure
Databricks con identidad administrada sobre ADLS Gen2). El encargo del equipo fijó **AWS S3** como almacenamiento, así que la
implementación usa el mecanismo análogo de AWS en Unity Catalog (que no es el mismo, como se explica después):

| | Enunciado (Azure) | Implementación actual (AWS) |
|---|---|---|
| Almacenamiento | ADLS Gen2 | Amazon S3, bucket `databricks-retail-etl-2026-smart` |
| Identidad hacia el almacenamiento | Managed Identity del Access Connector | **IAM Role** de AWS, con trust policy hacia Unity Catalog y External ID |
| Objeto de UC | Storage Credential (Managed Identity) + External Location | Storage Credential (IAM Role) + External Location sobre la raíz del bucket |
| Claves en notebooks | Ninguna | Ninguna |

**No son mecanismos idénticos.** Los dos evitan secretos en el código y delegan la autorización en Unity Catalog, pero difieren en
la nube, en el tipo de identidad (una identidad administrada de Entra ID frente a un rol asumido mediante STS) y en la configuración
(Access Connector frente a trust policy con External ID). Que el IAM Role satisfaga el requisito «Managed Identity» lo tiene que
confirmar el profesor. Si exige Azure, haría falta otro workspace y otro almacenamiento; eso no se ha hecho.

## D2. Datasets: E-commerce y Automobiles frente a los del ejemplo

**Pendiente de confirmar contra el enunciado completo.**

- El proyecto usa **dos fuentes independientes, E-commerce y Automobiles**, elegidas en el encargo inicial («al menos dos fuentes»).
- Se ha señalado que el material del profesor muestra `matriculados.csv` y `placement (1).csv`. En el repositorio de referencia
  `Enrykiel/databricks_project`, consultado el 2026-10-21 en sus ramas `main` y `dev`, **esos dos nombres no aparecen**: su `datasets/`
  contiene `ps_enrollment-1.csv`, `ps_enrollment-2.csv`, `ps_enrollment-3.csv`, `ps_prog_tbl.csv` y `ps_term_tbl.csv`. Esos nombres
  podrían venir del PDF o de otra versión del ejemplo.
- Falta confirmar si el enunciado **exige** datasets concretos o solo «al menos dos fuentes». No se han cambiado los datasets.

## D3. Licencias de los CSV

**Parcialmente resuelto.** Ver [datasets/README.md](../datasets/README.md):
- **E-commerce: procedencia confirmada.** El propietario del proyecto lo descargó directamente de la ficha de Kaggle de Nevil Dhinoja
  y su SHA-256 coincide exactamente con el de la copia del repositorio. La ficha declara **CC0: Public Domain**; esa licencia se
  atribuye a la fuente y no es una verificación legal independiente.
- **Automobiles: pendiente.** Deriva de UCI (CC BY 4.0, verificado por contenido), pero no se ha identificado el intermediario de la copia.

Esto no resuelve **D2**: que la procedencia esté documentada no significa que el profesor acepte estos datasets.

## D4. Almacenamiento sin restricción de solo lectura

**Decisión aceptada, con endurecimiento opcional.** La External Location cubre la raíz del bucket con lectura, escritura y borrado.
Los notebooks solo leen RAW y escriben en `lakehouse/`, pero eso lo garantiza el código, no el almacenamiento
(ver [seguridad/README.md](../seguridad/README.md#acceso-al-almacenamiento-qué-está-restringido-y-qué-no)).

## D5. dev y prod en un solo workspace

**Decisión aceptada.** Free Edition ofrece un único workspace. dev y prod se separan lógicamente (esquemas `dev_*` frente a
`bronze/silver/gold`, y `lakehouse/dev` frente a `lakehouse/prod`) dentro del catálogo `workspace`. No son dos workspaces físicos.

## D6. Producción y CI/CD sin ejecutar

**Pendiente.**
- Producción no se ha desplegado ni ejecutado. dev sí: `validate --strict`, `deploy` y run correctos (ver el [README](../README.md#estado-del-proyecto-2026-10-21)).
- GitHub Actions no se ha ejecutado nunca: no hay remoto ni commits.
- Está sin decidir la autenticación de CI, OAuth M2M o PAT (ver [configuracion_pendiente.md](configuracion_pendiente.md#autenticación-de-github-actions-no-verificada-todavía)).
