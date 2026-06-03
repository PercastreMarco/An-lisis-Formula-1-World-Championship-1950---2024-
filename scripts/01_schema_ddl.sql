-- =============================================================================
-- Proyecto Final — Módulo 4: Inteligencia de Negocios y SQL Avanzado
-- Archivo   : 01_schema_ddl.sql
-- Propósito : Crear el modelo dimensional (esquema estrella) en Aurora PostgreSQL
-- Schema    : f1_dw  (separado del OLTP para buenas prácticas)
-- Grano     : Un registro por piloto por carrera
-- Autor     : Proyecto Final BI
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0. SCHEMA
--    Separamos el Data Warehouse del esquema público (OLTP) siguiendo
--    buenas prácticas de naming en ambientes multi-esquema.
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS f1_dw;

SET search_path TO f1_dw;


-- -----------------------------------------------------------------------------
-- 1. DIMENSIÓN: dim_piloto
--    Grano     : Un registro por piloto único
--    SCD       : Tipo 1 (sobrescritura simple; historial de cambios no requerido)
--    Decisiones: nombre_completo desnormalizado (forename + surname del CSV)
--                fecha_nacimiento incluida para análisis age-performance
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS f1_dw.dim_piloto (
    piloto_sk           SERIAL          PRIMARY KEY,           -- Surrogate key generada en ETL
    driver_id           INT             NOT NULL UNIQUE,       -- Natural key del dataset Ergast
    driver_ref          VARCHAR(50),                           -- Slug/referencia (ej. "hamilton")
    numero_permanente   INT,                                   -- Número permanente (desde 2014)
    codigo_piloto       CHAR(3),                               -- Código de 3 letras (ej. "HAM")
    nombre_completo     VARCHAR(100)    NOT NULL,              -- forename + surname desnormalizado
    fecha_nacimiento    DATE,
    nacionalidad        VARCHAR(50),
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE  f1_dw.dim_piloto IS 'Dimensión de pilotos. SCD Tipo 1.';
COMMENT ON COLUMN f1_dw.dim_piloto.driver_id IS 'Natural key del dataset Ergast — conservada para auditoría y joins externos.';
COMMENT ON COLUMN f1_dw.dim_piloto.nombre_completo IS 'forename + surname desnormalizados para simplificar GROUP BY y filtros.';


-- -----------------------------------------------------------------------------
-- 2. DIMENSIÓN: dim_constructor
--    Grano     : Un registro por constructor único
--    SCD       : Tipo 1
--    Decisiones: era_f1 es atributo calculado en ETL para análisis de dominancia
--                por período sin CTEs complejos en cada consulta analítica
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS f1_dw.dim_constructor (
    constructor_sk      SERIAL          PRIMARY KEY,
    constructor_id      INT             NOT NULL UNIQUE,       -- Natural key Ergast
    constructor_ref     VARCHAR(50),                           -- Slug (ej. "red_bull")
    nombre              VARCHAR(100)    NOT NULL,
    nacionalidad        VARCHAR(50),
    era_f1              VARCHAR(50),                           -- Calculado en ETL: "Era híbrida 2014+", etc.
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE  f1_dw.dim_constructor IS 'Dimensión de constructores/equipos. SCD Tipo 1.';
COMMENT ON COLUMN f1_dw.dim_constructor.era_f1 IS 'Era técnica calculada en ETL según el año de actividad del constructor.';


-- -----------------------------------------------------------------------------
-- 3. DIMENSIÓN: dim_circuito
--    Grano     : Un registro por circuito único
--    SCD       : Tipo 1
--    Decisiones: colapsa circuits.csv + metadata de races.csv
--                latitud/longitud incluidas para visualizaciones de mapa
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS f1_dw.dim_circuito (
    circuito_sk         SERIAL          PRIMARY KEY,
    circuit_id          INT             NOT NULL UNIQUE,       -- Natural key Ergast
    circuit_ref         VARCHAR(50),                           -- Slug (ej. "monza")
    nombre              VARCHAR(100)    NOT NULL,
    localidad           VARCHAR(100),
    pais                VARCHAR(50),
    latitud             NUMERIC(9, 6),                         -- Para mapas geográficos
    longitud            NUMERIC(9, 6),
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE  f1_dw.dim_circuito IS 'Dimensión de circuitos. SCD Tipo 1. Incluye coordenadas para mapas.';
COMMENT ON COLUMN f1_dw.dim_circuito.latitud  IS 'Latitud geográfica para visualizaciones de mapa en el dashboard.';
COMMENT ON COLUMN f1_dw.dim_circuito.longitud IS 'Longitud geográfica para visualizaciones de mapa en el dashboard.';


-- -----------------------------------------------------------------------------
-- 4. DIMENSIÓN: dim_tiempo
--    Grano     : Un registro por fecha de carrera (calendario F1 irregular)
--    SCD       : Tipo 1
--    Decisiones: NO se usa calendario diario estándar; el grano es la fecha
--                de cada Gran Premio. numero_ronda permite análisis de momentum
--                dentro de temporada. era_f1 evita CTEs repetitivos.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS f1_dw.dim_tiempo (
    tiempo_sk           SERIAL          PRIMARY KEY,
    race_id             INT             NOT NULL UNIQUE,       -- Natural key: ID de carrera Ergast
    fecha               DATE            NOT NULL,
    anio                SMALLINT        NOT NULL,
    nombre_gp           VARCHAR(100),                         -- "Gran Premio de Mónaco"
    numero_ronda        SMALLINT,                             -- Ronda dentro de la temporada
    temporada           SMALLINT        NOT NULL,             -- Año de la temporada
    era_f1              VARCHAR(50),                          -- "Era híbrida 2014+", etc.
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE  f1_dw.dim_tiempo IS 'Dimensión de tiempo con grano de fecha de carrera (no calendario diario estándar).';
COMMENT ON COLUMN f1_dw.dim_tiempo.era_f1 IS 'Era técnica: Aspiración natural 1950-66 | DFV 1967-76 | Turbo 1977-88 | NA moderno 1989-2005 | V8 2006-13 | Híbrida 2014+.';
COMMENT ON COLUMN f1_dw.dim_tiempo.numero_ronda IS 'Posición en el calendario de la temporada. Útil para análisis de momentum.';


-- -----------------------------------------------------------------------------
-- 5. DIMENSIÓN: dim_estado
--    Grano     : Un registro por código de status único
--    SCD       : Tipo 1
--    Decisiones: mapea los 140+ status codes de Ergast a 4 categorías analíticas.
--                Esta desnormalización es clave para responder "% abandonos mecánicos
--                vs accidentes" sin CASE WHEN complejos en cada consulta.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS f1_dw.dim_estado (
    estado_sk           SERIAL          PRIMARY KEY,
    status_id           INT             NOT NULL UNIQUE,       -- Natural key Ergast
    descripcion         VARCHAR(100)    NOT NULL,              -- Texto original (ej. "Engine")
    categoria           VARCHAR(50)     NOT NULL,              -- Calculada en ETL
    -- Categorías posibles: 'Finalizado' | 'Abandono mecánico' | 'Accidente' | 'Descalificado' | 'Otro'
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE  f1_dw.dim_estado IS '140+ códigos de status Ergast mapeados a 5 categorías analíticas en ETL.';
COMMENT ON COLUMN f1_dw.dim_estado.categoria IS 'Finalizado | Abandono mecánico | Accidente | Descalificado | Otro.';


-- -----------------------------------------------------------------------------
-- 6. TABLA DE HECHOS: fact_resultado_carrera
--    Grano     : Un registro por piloto por carrera
--    PK        : (piloto_sk, tiempo_sk) — unicidad garantizada al nivel del grano
--    Medidas   : posicion_salida, posicion_final, puntos, vueltas_completadas,
--                num_pitstops, tiempo_total_ms, delta_posicion, es_abandono
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS f1_dw.fact_resultado_carrera (
    -- Claves foráneas (dimensiones)
    piloto_sk           INT             NOT NULL REFERENCES f1_dw.dim_piloto(piloto_sk),
    constructor_sk      INT             NOT NULL REFERENCES f1_dw.dim_constructor(constructor_sk),
    circuito_sk         INT             NOT NULL REFERENCES f1_dw.dim_circuito(circuito_sk),
    tiempo_sk           INT             NOT NULL REFERENCES f1_dw.dim_tiempo(tiempo_sk),
    estado_sk           INT             NOT NULL REFERENCES f1_dw.dim_estado(estado_sk),

    -- Medidas
    posicion_salida     SMALLINT,                             -- Grid position (NULL = pit lane start)
    posicion_final      SMALLINT,                             -- Posición oficial (NULL si no clasificado)
    puntos              NUMERIC(5, 2)   NOT NULL DEFAULT 0,   -- Puntos otorgados (varía por era)
    vueltas_completadas SMALLINT        NOT NULL DEFAULT 0,
    num_pitstops        SMALLINT        NOT NULL DEFAULT 0,   -- Calculado en ETL desde pit_stops.csv
    tiempo_total_ms     BIGINT,                               -- Tiempo total en ms (NULL si abandono)
    delta_posicion      SMALLINT,                             -- posicion_salida - posicion_final
    es_abandono         BOOLEAN         NOT NULL DEFAULT FALSE,

    -- Auditoría
    loaded_at           TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    -- Clave primaria compuesta — unicidad al nivel del grano
    PRIMARY KEY (piloto_sk, tiempo_sk)
);

COMMENT ON TABLE  f1_dw.fact_resultado_carrera IS 'Tabla de hechos. Grano: un registro por piloto por carrera.';
COMMENT ON COLUMN f1_dw.fact_resultado_carrera.delta_posicion  IS 'posicion_salida - posicion_final. Positivo = ganó posiciones. Calculado en ETL.';
COMMENT ON COLUMN f1_dw.fact_resultado_carrera.num_pitstops    IS 'Conteo de paradas calculado en ETL desde pit_stops.csv. 0 para carreras anteriores a 1994.';
COMMENT ON COLUMN f1_dw.fact_resultado_carrera.tiempo_total_ms IS 'Tiempo total de carrera en milisegundos. NULL si el piloto no terminó.';


-- -----------------------------------------------------------------------------
-- 7. ÍNDICES
--    Optimizados para los patrones de consulta analítica esperados:
--    - Filtros por temporada/era
--    - Agrupaciones por piloto y constructor
--    - Análisis de abandonos
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_fact_tiempo_sk
    ON f1_dw.fact_resultado_carrera (tiempo_sk);

CREATE INDEX IF NOT EXISTS idx_fact_piloto_sk
    ON f1_dw.fact_resultado_carrera (piloto_sk);

CREATE INDEX IF NOT EXISTS idx_fact_constructor_sk
    ON f1_dw.fact_resultado_carrera (constructor_sk);

CREATE INDEX IF NOT EXISTS idx_fact_circuito_sk
    ON f1_dw.fact_resultado_carrera (circuito_sk);

CREATE INDEX IF NOT EXISTS idx_fact_es_abandono
    ON f1_dw.fact_resultado_carrera (es_abandono)
    WHERE es_abandono = TRUE;                                  -- Índice parcial para filtros de abandono

CREATE INDEX IF NOT EXISTS idx_dim_tiempo_temporada
    ON f1_dw.dim_tiempo (temporada, era_f1);

CREATE INDEX IF NOT EXISTS idx_dim_tiempo_anio
    ON f1_dw.dim_tiempo (anio);

-- =============================================================================
-- FIN DEL DDL
-- Para cargar el esquema en Aurora PostgreSQL:
--   psql -h <aurora-endpoint> -U <usuario> -d <base_de_datos> -f 01_schema_ddl.sql
-- =============================================================================
