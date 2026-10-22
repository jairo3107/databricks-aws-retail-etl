# Diagramas

Fuente editable en [Mermaid](https://mermaid.js.org/), que GitHub muestra directamente. `scripts/validar_repo.py` comprueba
que el diagrama del job coincide con las dependencias de [resources/wf_prod_etl_retail.job.yml](../resources/wf_prod_etl_retail.job.yml)
y que aparecen todas las tablas de `comun.TABLAS`. Si cambia el job o las tablas, hay que actualizar este archivo.

## 1. Arquitectura

```mermaid
flowchart LR
    subgraph gh["GitHub"]
        ci["ci.yml<br/>validación local, sin secretos"]
        dp["deploy-prod.yml<br/>manual: validate → deploy → run"]
    end

    subgraph aws["AWS"]
        iam["IAM Role<br/>trust policy hacia UC + External ID"]
        subgraph s3["S3: databricks-retail-etl-2026-smart"]
            raw["raw/<br/>ecommerce/ · automobiles/"]
            ldev["lakehouse/dev/<br/>bronze · silver · gold"]
            lprod["lakehouse/prod/<br/>bronze · silver · gold"]
        end
    end

    subgraph dbx["Databricks Free Edition (un solo workspace)"]
        subgraph uc["Unity Catalog · catálogo workspace"]
            sc["Storage Credential"]
            el["External Location<br/>raíz del bucket: lectura, escritura y borrado"]
            edev["dev_bronze · dev_silver · dev_gold"]
            eprod["bronze · silver · gold"]
        end
        job["Job serverless<br/>WF_DEV_ETL_RETAIL / WF_PROD_ETL_RETAIL"]
        dash["Dashboard AI/BI<br/>(pendiente)"]
    end

    readers["retail_etl_readers<br/>grupo de cuenta"]

    dp -- "bundle deploy / run (-t prod)" --> job
    sc -- "asume" --> iam
    el --> sc
    iam -. "acceso al bucket" .-> s3
    job -- "lee (spark.read s3://)" --> raw
    job -- "escribe Delta externas" --> ldev
    job -- "escribe Delta externas" --> lprod
    ldev --- edev
    lprod --- eprod
    job -- "GRANT USE CATALOG / USE SCHEMA / SELECT sobre Gold" --> readers
    readers -- "SELECT Gold" --> dash
```

- RAW se lee directamente desde S3, gobernado por la External Location: no se usan DBFS ni Volúmenes.
- La External Location cubre la raíz del bucket con lectura, escritura y borrado. Que los notebooks solo lean `raw/` y solo
  escriban en `lakehouse/<entorno>/` lo garantiza el código, no el almacenamiento.
- IAM Role y Managed Identity no son el mismo mecanismo ([D1](decisiones_y_pendientes.md#d1-acceso-a-raw-managed-identity-enunciado-frente-a-iam-role-de-aws-implementación)).
- La ejecución de prod y de GitHub Actions todavía no ha ocurrido. dev se despliega desde el CLI local.

## 2. Flujo del job (tareas y dependencias)

```mermaid
flowchart LR
    %% dag-job: los identificadores son los task_key del job; validar_repo.py compara estas aristas con depends_on
    PrepAmb["PrepAmb<br/>00_prep_amb.py"]
    Extract_ecommerce["Extract_ecommerce<br/>01_extract_ecommerce.py"]
    Extract_automobiles["Extract_automobiles<br/>01_extract_automobiles.py"]
    Transform_ecommerce["Transform_ecommerce<br/>02_transform_ecommerce.py"]
    Transform_automobiles["Transform_automobiles<br/>02_transform_automobiles.py"]
    Load["Load<br/>03_load_gold.py"]
    Grants["Grants<br/>04_grants.py"]

    PrepAmb --> Extract_ecommerce
    PrepAmb --> Extract_automobiles
    Extract_ecommerce --> Transform_ecommerce
    Extract_automobiles --> Transform_automobiles
    Transform_ecommerce --> Load
    Transform_automobiles --> Load
    Load --> Grants
```

## 3. Medallion por fuente (sin cruces entre fuentes)

```mermaid
flowchart LR
    subgraph eco["E-commerce"]
        e_raw["raw/ecommerce/<br/>Ecommerce_Sales_Prediction_Dataset.csv"]
        e_b["bronze.ecommerce_ventas<br/>todo string + auditoría"]
        e_s["silver.ecommerce_ventas<br/>fecha dd-MM-yyyy → date, decimales, int"]
        e_g1["gold.ecommerce_ventas_mensuales_categoria"]
        e_g2["gold.ecommerce_ventas_segmento_categoria"]
        e_raw --> e_b --> e_s
        e_s --> e_g1
        e_s --> e_g2
    end

    subgraph aut["Automobiles"]
        a_raw["raw/automobiles/<br/>Automobile_data.csv"]
        a_b["bronze.automobiles_specs<br/>todo string, snake_case + auditoría"]
        a_s["silver.automobiles_specs<br/>'?' → null, tipos explícitos, registro_hash"]
        a_g1["gold.automobiles_resumen_marca"]
        a_g2["gold.automobiles_resumen_carroceria_combustible"]
        a_raw --> a_b --> a_s
        a_s --> a_g1
        a_s --> a_g2
    end
```

En dev, los esquemas se llaman `dev_bronze`, `dev_silver` y `dev_gold`, y los datos van a `lakehouse/dev/`. En prod se usan
`bronze`, `silver` y `gold`, en `lakehouse/prod/`.
