# ====================================================================
# postgres-ddl-v2.sql — Esquema de base de datos para optimizacion
# ====================================================================
#
# Este script crea el esquema completo de PostgreSQL para el sistema
# de optimizacion de filtros analogicos activos.
#
# Componentes:
#   - 4 ENUMs: tipo_filtro_circuito, estado_ejecucion,
#     modo_operacion, algoritmo_optimizacion
#   - 2 tablas: plantilla_filtro (padre), ejecucion_filtro (hija)
#   - 4 registros semilla: una plantilla por cada tipo de filtro
#
# Relacion:
#   plantilla_filtro (1) -> (N) ejecucion_filtro
#
# Para ejecutar:
#   psql -U postgres -d optimizacion_filtros -f postgres-ddl-v2.sql
# ====================================================================

-- ENUM polimorfico: tipo de filtro de circuito analogico.
-- Determina que script de optimizacion se invoca y que claves
-- de frecuencias son validas para esa combinacion tipo+modo.
CREATE TYPE tipo_filtro_circuito AS ENUM (
    'PASA_BAJA',
    'PASA_ALTA',
    'PASA_BANDA',
    'RECHAZO_BANDA'
);

-- ENUM de estado de ejecucion. Maquina de estados:
-- PENDIENTE -> VALIDANDO -> EJECUTANDOSE -> COMPLETADO
--                                     \-> ERROR
CREATE TYPE estado_ejecucion AS ENUM (
    'PENDIENTE',
    'VALIDANDO',
    'EJECUTANDOSE',
    'COMPLETADO',
    'ERROR'
);

-- ENUM de modo de operacion del filtro.
-- BASICO: 1 frecuencia clave (fc_objetivo o fc_inferior+fc_superior).
-- AVANZADO: multiples frecuencias (f_paso, f_aten, etc.).
CREATE TYPE modo_operacion AS ENUM (
    'BASICO',
    'AVANZADO'
);

-- ENUM de algoritmo de optimizacion.
-- AG: Algoritmo Genetico (4 scripts disponibles).
-- PSO: Enjambre de Particulas (4 scripts disponibles).
-- NOTA: SA y Simulated Annealing y Bayesian Optimization solo
-- tienen templates SPICE, no scripts Python implementados.
CREATE TYPE algoritmo_optimizacion AS ENUM (
    'AG',
    'PSO'
);

-- ============================================================
-- Tabla padre: plantilla_filtro
-- Define que parametros espera cada tipo de filtro.
-- El esquema_parametros documenta las claves requeridas,
-- sus tipos y unidades. Es de solo lectura (se carga con seeds).
-- ============================================================
CREATE TABLE plantilla_filtro (
    plantilla_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo_filtro tipo_filtro_circuito NOT NULL,
    numero_version INTEGER NOT NULL,
    nombre_plantilla TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    esquema_parametros JSONB NOT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Tabla hija: ejecucion_filtro
-- Una ejecucion concreta de optimizacion, con sus parametros
-- reales, estado, y resultado.
--
-- configuracion_ejecucion: almacena el config.json completo
--   que se envio al FastAPI Worker (los 5 bloques raiz).
-- resultado: almacena el resultado.json del script Python
--   (fitness, componentes, grafica base64, etc.).
--
-- El tipo_filtro se repite aqui para facilitar queries directas
-- sin JOIN a plantilla_filtro.
-- ============================================================
CREATE TABLE ejecucion_filtro (
    ejecucion_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plantilla_id UUID NOT NULL
        REFERENCES plantilla_filtro(plantilla_id),
    tipo_filtro tipo_filtro_circuito NOT NULL,
    algoritmo algoritmo_optimizacion NOT NULL,
    modo modo_operacion NOT NULL,
    nombre_ejecucion TEXT NOT NULL,
    configuracion_ejecucion JSONB NOT NULL,
    estado_ejecucion estado_ejecucion NOT NULL DEFAULT 'PENDIENTE',
    resultado JSONB,
    creado_en TIMESTAMP NOT NULL DEFAULT NOW(),
    actualizado_en TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- SEEDS: plantillas para cada tipo de filtro
-- Cada plantilla documenta su esquema_parametros en JSONB,
-- describiendo que claves son requeridas, sus tipos y reglas.
-- ============================================================

-- PASA_BAJA: Atenua frecuencias altas, deja pasar las bajas.
-- BASICO: solo necesita fc_objetivo.
-- AVANZADO: necesita f_paso < f_aten.
INSERT INTO plantilla_filtro (
    plantilla_id, tipo_filtro, numero_version, nombre_plantilla,
    descripcion, esquema_parametros
) VALUES (
    '11111111-1111-1111-1111-111111111111',
    'PASA_BAJA',
    1,
    'Plantilla Filtro Pasa-Baja v1',
    'Optimizacion para filtro pasa-baja. Atenua frecuencias altas y deja pasar las bajas.',
    '{
        "modo": { "tipo": "enum", "valores": ["BASICO", "AVANZADO"] },
        "entorno": {
            "v_fuente": { "tipo": "number", "unidad": "V", "regla": "> 0, recomendado <= 10" },
            "r_fuente": { "tipo": "number", "unidad": "Ohm", "regla": "> 0, serie E12" },
            "r_carga": { "tipo": "number", "unidad": "Ohm", "regla": "> 0, serie E12" }
        },
        "barrido_ac": {
            "f_inicial": { "tipo": "integer", "unidad": "Hz", "regla": "> 0" },
            "f_final": { "tipo": "integer", "unidad": "Hz", "regla": "<= 10000000" }
        },
        "frecuencias": {
            "BASICO": {
                "fc_objetivo": { "tipo": "number", "unidad": "Hz" }
            },
            "AVANZADO": {
                "f_paso": { "tipo": "number", "unidad": "Hz", "regla": "< f_aten" },
                "f_aten": { "tipo": "number", "unidad": "Hz", "regla": "> f_paso" }
            }
        }
    }'
);

-- PASA_ALTA: Atenua frecuencias bajas, deja pasar las altas.
-- BASICO: solo necesita fc_objetivo.
-- AVANZADO: necesita f_aten < f_paso.
INSERT INTO plantilla_filtro (
    plantilla_id, tipo_filtro, numero_version, nombre_plantilla,
    descripcion, esquema_parametros
) VALUES (
    '22222222-2222-2222-2222-222222222222',
    'PASA_ALTA',
    1,
    'Plantilla Filtro Pasa-Alta v1',
    'Optimizacion para filtro pasa-alta. Atenua frecuencias bajas y deja pasar las altas.',
    '{
        "modo": { "tipo": "enum", "valores": ["BASICO", "AVANZADO"] },
        "entorno": {
            "v_fuente": { "tipo": "number", "unidad": "V", "regla": "> 0, recomendado <= 10" },
            "r_fuente": { "tipo": "number", "unidad": "Ohm", "regla": "> 0, serie E12" },
            "r_carga": { "tipo": "number", "unidad": "Ohm", "regla": "> 0, serie E12" }
        },
        "barrido_ac": {
            "f_inicial": { "tipo": "integer", "unidad": "Hz", "regla": "> 0" },
            "f_final": { "tipo": "integer", "unidad": "Hz", "regla": "<= 10000000" }
        },
        "frecuencias": {
            "BASICO": {
                "fc_objetivo": { "tipo": "number", "unidad": "Hz" }
            },
            "AVANZADO": {
                "f_aten": { "tipo": "number", "unidad": "Hz", "regla": "< f_paso" },
                "f_paso": { "tipo": "number", "unidad": "Hz", "regla": "> f_aten" }
            }
        }
    }'
);

-- PASA_BANDA: Solo deja pasar un rango de frecuencias.
-- BASICO: fc_inferior < fc_superior.
-- AVANZADO: f_aten_1 < f_paso_1 <= f_paso_2 < f_aten_2.
INSERT INTO plantilla_filtro (
    plantilla_id, tipo_filtro, numero_version, nombre_plantilla,
    descripcion, esquema_parametros
) VALUES (
    '33333333-3333-3333-3333-333333333333',
    'PASA_BANDA',
    1,
    'Plantilla Filtro Pasa-Banda v1',
    'Optimizacion para filtro pasa-banda. Solo deja pasar un rango de frecuencias.',
    '{
        "modo": { "tipo": "enum", "valores": ["BASICO", "AVANZADO"] },
        "entorno": {
            "v_fuente": { "tipo": "number", "unidad": "V", "regla": "> 0, recomendado <= 10" },
            "r_fuente": { "tipo": "number", "unidad": "Ohm", "regla": "> 0, serie E12" },
            "r_carga": { "tipo": "number", "unidad": "Ohm", "regla": "> 0, serie E12" }
        },
        "barrido_ac": {
            "f_inicial": { "tipo": "integer", "unidad": "Hz", "regla": "> 0" },
            "f_final": { "tipo": "integer", "unidad": "Hz", "regla": "<= 10000000" }
        },
        "frecuencias": {
            "BASICO": {
                "fc_inferior": { "tipo": "number", "unidad": "Hz", "regla": "< fc_superior" },
                "fc_superior": { "tipo": "number", "unidad": "Hz", "regla": "> fc_inferior" }
            },
            "AVANZADO": {
                "f_aten_1": { "tipo": "number", "unidad": "Hz", "regla": "< f_paso_1" },
                "f_paso_1": { "tipo": "number", "unidad": "Hz", "regla": ">= f_aten_1, <= f_paso_2" },
                "f_paso_2": { "tipo": "number", "unidad": "Hz", "regla": ">= f_paso_1, < f_aten_2" },
                "f_aten_2": { "tipo": "number", "unidad": "Hz", "regla": "> f_paso_2" }
            }
        }
    }'
);

-- RECHAZO_BANDA (notch): Atenua un rango de frecuencias, deja pasar el resto.
-- BASICO: fc_inferior < fc_superior.
-- AVANZADO: f_paso_1 < f_aten_1 <= f_aten_2 < f_paso_2.
INSERT INTO plantilla_filtro (
    plantilla_id, tipo_filtro, numero_version, nombre_plantilla,
    descripcion, esquema_parametros
) VALUES (
    '44444444-4444-4444-4444-444444444444',
    'RECHAZO_BANDA',
    1,
    'Plantilla Filtro Rechazo-Banda v1',
    'Optimizacion para filtro rechazo-banda (notch). Atenua un rango de frecuencias y deja pasar el resto.',
    '{
        "modo": { "tipo": "enum", "valores": ["BASICO", "AVANZADO"] },
        "entorno": {
            "v_fuente": { "tipo": "number", "unidad": "V", "regla": "> 0, recomendado <= 10" },
            "r_fuente": { "tipo": "number", "unidad": "Ohm", "regla": "> 0, serie E12" },
            "r_carga": { "tipo": "number", "unidad": "Ohm", "regla": "> 0, serie E12" }
        },
        "barrido_ac": {
            "f_inicial": { "tipo": "integer", "unidad": "Hz", "regla": "> 0" },
            "f_final": { "tipo": "integer", "unidad": "Hz", "regla": "<= 10000000" }
        },
        "frecuencias": {
            "BASICO": {
                "fc_inferior": { "tipo": "number", "unidad": "Hz", "regla": "< fc_superior" },
                "fc_superior": { "tipo": "number", "unidad": "Hz", "regla": "> fc_inferior" }
            },
            "AVANZADO": {
                "f_paso_1": { "tipo": "number", "unidad": "Hz", "regla": "< f_aten_1" },
                "f_aten_1": { "tipo": "number", "unidad": "Hz", "regla": "> f_paso_1, <= f_aten_2" },
                "f_aten_2": { "tipo": "number", "unidad": "Hz", "regla": ">= f_aten_1, < f_paso_2" },
                "f_paso_2": { "tipo": "number", "unidad": "Hz", "regla": "> f_aten_2" }
            }
        }
    }'
);
