-- =============================================================================
-- VALIDACIÓN POST CARGA
-- =============================================================================

SET search_path TO f1_dw;

-- =============================================================================
-- SCRIPT 1 — INTEGRIDAD DEL MODELO
-- Valida estructura, conteos y relaciones del esquema estrella
-- =============================================================================
 
-- -----------------------------------------------------------------------------
-- 1.1 Conteo de filas por tabla
--     Esperado: 6 tablas con los volúmenes del dataset Ergast
-- -----------------------------------------------------------------------------
SELECT 'dim_piloto'             AS tabla, COUNT(*) AS filas FROM dim_piloto
UNION ALL
SELECT 'dim_constructor',                COUNT(*)           FROM dim_constructor
UNION ALL
SELECT 'dim_circuito',                   COUNT(*)           FROM dim_circuito
UNION ALL
SELECT 'dim_tiempo',                     COUNT(*)           FROM dim_tiempo
UNION ALL
SELECT 'dim_estado',                     COUNT(*)           FROM dim_estado
UNION ALL
SELECT 'fact_resultado_carrera',         COUNT(*)           FROM fact_resultado_carrera
ORDER BY tabla;
-- Esperado:
--   dim_circuito            →    77 filas
--   dim_constructor         →   212 filas
--   dim_estado              →   139 filas
--   dim_piloto              →   861 filas
--   dim_tiempo              → 1,125 filas
--   fact_resultado_carrera  → 26,668 filas
 
 
-- -----------------------------------------------------------------------------
-- 1.2 PKs duplicadas en fact_resultado_carrera
--     Esperado: 0 filas (ningún duplicado en la PK compuesta)
-- -----------------------------------------------------------------------------
SELECT
    piloto_sk,
    tiempo_sk,
    COUNT(*) AS duplicados
FROM fact_resultado_carrera
GROUP BY piloto_sk, tiempo_sk
HAVING COUNT(*) > 1
ORDER BY duplicados DESC;
-- Esperado: 0 filas
 
 
-- -----------------------------------------------------------------------------
-- 1.3 FKs huérfanas en fact_resultado_carrera
--     Esperado: 0 huérfanas en las 5 relaciones
-- -----------------------------------------------------------------------------
SELECT 'piloto_sk'      AS fk, COUNT(*) AS huerfanas
FROM fact_resultado_carrera f
LEFT JOIN dim_piloto d ON f.piloto_sk = d.piloto_sk
WHERE d.piloto_sk IS NULL
 
UNION ALL
SELECT 'constructor_sk', COUNT(*)
FROM fact_resultado_carrera f
LEFT JOIN dim_constructor d ON f.constructor_sk = d.constructor_sk
WHERE d.constructor_sk IS NULL
 
UNION ALL
SELECT 'circuito_sk', COUNT(*)
FROM fact_resultado_carrera f
LEFT JOIN dim_circuito d ON f.circuito_sk = d.circuito_sk
WHERE d.circuito_sk IS NULL
 
UNION ALL
SELECT 'tiempo_sk', COUNT(*)
FROM fact_resultado_carrera f
LEFT JOIN dim_tiempo d ON f.tiempo_sk = d.tiempo_sk
WHERE d.tiempo_sk IS NULL
 
UNION ALL
SELECT 'estado_sk', COUNT(*)
FROM fact_resultado_carrera f
LEFT JOIN dim_estado d ON f.estado_sk = d.estado_sk
WHERE d.estado_sk IS NULL;
-- Esperado: 0 huérfanas en las 5 FKs
 
 
-- -----------------------------------------------------------------------------
-- 1.4 Nulos en columnas críticas de fact_resultado_carrera
--     Esperado: 0 nulos en SKs y puntos
-- -----------------------------------------------------------------------------
SELECT
    COUNT(*) FILTER (WHERE piloto_sk      IS NULL) AS nulos_piloto_sk,
    COUNT(*) FILTER (WHERE constructor_sk IS NULL) AS nulos_constructor_sk,
    COUNT(*) FILTER (WHERE circuito_sk    IS NULL) AS nulos_circuito_sk,
    COUNT(*) FILTER (WHERE tiempo_sk      IS NULL) AS nulos_tiempo_sk,
    COUNT(*) FILTER (WHERE estado_sk      IS NULL) AS nulos_estado_sk,
    COUNT(*) FILTER (WHERE puntos         IS NULL) AS nulos_puntos
FROM fact_resultado_carrera;
-- Esperado: 0 en todas las columnas
 
 
-- -----------------------------------------------------------------------------
-- 1.5 Cobertura temporal del dataset
--     Esperado: desde 1950 hasta 2024
-- -----------------------------------------------------------------------------
SELECT
    MIN(anio)   AS primer_anio,
    MAX(anio)   AS ultimo_anio,
    COUNT(*)    AS total_carreras,
    COUNT(DISTINCT temporada) AS total_temporadas
FROM dim_tiempo;
-- Esperado: 1950 → 2024 | ~1,125 carreras | 75 temporadas
 
 
-- =============================================================================
-- SCRIPT 2 — VALIDACIÓN ANALÍTICA
-- Verifica que los datos responden correctamente la pregunta de negocio
-- =============================================================================
 
-- -----------------------------------------------------------------------------
-- 2.1 Muestra de registros con joins completos
--     Verifica que los JOINs entre fact y todas las dims funcionan
-- -----------------------------------------------------------------------------
SELECT
    p.nombre_completo                   AS piloto,
    c.nombre                            AS constructor,
    ci.nombre                           AS circuito,
    ci.pais                             AS pais,
    t.anio,
    t.era_f1,
    f.posicion_salida,
    f.posicion_final,
    f.puntos,
    f.delta_posicion,
    f.num_pitstops,
    f.es_abandono,
    e.categoria                         AS estado
FROM fact_resultado_carrera f
JOIN dim_piloto      p  ON f.piloto_sk      = p.piloto_sk
JOIN dim_constructor c  ON f.constructor_sk = c.constructor_sk
JOIN dim_circuito    ci ON f.circuito_sk    = ci.circuito_sk
JOIN dim_tiempo      t  ON f.tiempo_sk      = t.tiempo_sk
JOIN dim_estado      e  ON f.estado_sk      = e.estado_sk
ORDER BY t.anio DESC, f.puntos DESC
LIMIT 20;
 
 
-- -----------------------------------------------------------------------------
-- 2.2 Top 10 pilotos por puntos históricos
--     Verifica agregaciones sobre la fact table
-- -----------------------------------------------------------------------------
SELECT
    p.nombre_completo               AS piloto,
    p.nacionalidad,
    COUNT(*)                        AS carreras_disputadas,
    SUM(f.puntos)                   AS puntos_totales,
    COUNT(*) FILTER (WHERE f.posicion_final = 1) AS victorias,
    COUNT(*) FILTER (WHERE f.es_abandono)        AS abandonos,
    ROUND(AVG(f.posicion_salida), 1)             AS avg_posicion_salida
FROM fact_resultado_carrera f
JOIN dim_piloto p ON f.piloto_sk = p.piloto_sk
GROUP BY p.piloto_sk, p.nombre_completo, p.nacionalidad
ORDER BY puntos_totales DESC
LIMIT 10;
 
 
-- -----------------------------------------------------------------------------
-- 2.3 Dominancia de constructores por era
--     Verifica el atributo era_f1 calculado en el ETL
-- -----------------------------------------------------------------------------
SELECT
    c.era_f1,
    c.nombre                        AS constructor,
    COUNT(*)                        AS carreras,
    SUM(f.puntos)                   AS puntos_totales,
    COUNT(*) FILTER (WHERE f.posicion_final = 1) AS victorias
FROM fact_resultado_carrera f
JOIN dim_constructor c ON f.constructor_sk = c.constructor_sk
WHERE f.posicion_final IS NOT NULL
GROUP BY c.era_f1, c.constructor_sk, c.nombre
ORDER BY c.era_f1, victorias DESC;
 
 
-- -----------------------------------------------------------------------------
-- 2.4 Distribución de categorías de abandono
--     Verifica el mapeo de 140+ status a 5 categorías en dim_estado
-- -----------------------------------------------------------------------------
SELECT
    e.categoria,
    COUNT(*)                                AS total,
    ROUND(COUNT(*) * 100.0 /
        SUM(COUNT(*)) OVER (), 1)           AS porcentaje
FROM fact_resultado_carrera f
JOIN dim_estado e ON f.estado_sk = e.estado_sk
GROUP BY e.categoria
ORDER BY total DESC;
-- Esperado: Finalizado ~50%, Abandono mecánico ~25%, Accidente ~10%, etc.
 
 
-- -----------------------------------------------------------------------------
-- 2.5 Impacto de la posición de salida en la victoria
--     Responde directamente la pregunta analítica del proyecto
-- -----------------------------------------------------------------------------
SELECT
    f.posicion_salida                       AS grid,
    COUNT(*)                                AS total_carreras,
    COUNT(*) FILTER (WHERE f.posicion_final = 1) AS victorias,
    ROUND(
        COUNT(*) FILTER (WHERE f.posicion_final = 1) * 100.0
        / NULLIF(COUNT(*), 0), 1
    )                                       AS pct_victoria
FROM fact_resultado_carrera f
WHERE f.posicion_salida BETWEEN 1 AND 10
GROUP BY f.posicion_salida
ORDER BY f.posicion_salida;
-- Esperado: pole position (~40-45% victorias), decreciente hacia grid 10
 
-- =============================================================================
-- FIN DE VALIDACIÓN
-- Si todas las queries devuelven resultados coherentes, el modelo dimensional
-- =============================================================================


SELECT
    p.nombre_completo,
    c.nombre        AS constructor,
    ci.nombre       AS circuito,
    t.anio,
    f.posicion_salida,
    f.posicion_final,
    f.puntos,
    f.delta_posicion,
    f.es_abandono
FROM fact_resultado_carrera f
JOIN dim_piloto      p  ON f.piloto_sk      = p.piloto_sk
JOIN dim_constructor c  ON f.constructor_sk = c.constructor_sk
JOIN dim_circuito    ci ON f.circuito_sk    = ci.circuito_sk
JOIN dim_tiempo      t  ON f.tiempo_sk      = t.tiempo_sk
ORDER BY t.anio DESC, f.puntos DESC
LIMIT 20;







