-- Verificación de permisos (SOLO LECTURA). Sustituye los marcadores <...>.
-- Los GRANT se aplican desde proceso/04_grants.py; este script solo consulta.
-- <catalogo> = workspace. <esquema_gold>: gold en prod, dev_gold en dev.
-- Captura para evidencias/: DEV_GRANTS_GOLD.png (ver evidencias/README.md).

SHOW GRANTS ON CATALOG `<catalogo>`;
SHOW GRANTS ON SCHEMA `<catalogo>`.`<esquema_gold>`;
SHOW GRANTS ON TABLE `<catalogo>`.`<esquema_gold>`.`ecommerce_ventas_mensuales_categoria`;
SHOW GRANTS ON TABLE `<catalogo>`.`<esquema_gold>`.`ecommerce_ventas_segmento_categoria`;
SHOW GRANTS ON TABLE `<catalogo>`.`<esquema_gold>`.`automobiles_resumen_marca`;
SHOW GRANTS ON TABLE `<catalogo>`.`<esquema_gold>`.`automobiles_resumen_carroceria_combustible`;
SHOW GRANTS `<grant_principal>` ON SCHEMA `<catalogo>`.`<esquema_gold>`;
SHOW GRANTS `<grant_principal>` ON TABLE `<catalogo>`.`<esquema_gold>`.`automobiles_resumen_marca`;

-- El tipo (EXTERNAL) y la ubicación de las tablas se comprueban en evidencias/consultas_evidencia.sql (E2 y E3).
