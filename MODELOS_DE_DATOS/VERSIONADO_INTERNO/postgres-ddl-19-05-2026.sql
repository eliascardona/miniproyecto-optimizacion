-- Código de ejemplo SQL

CREATE TABLE plantilla_filtro (
    plantilla_id UUID PRIMARY KEY,

    tipo_filtro tipo_filtro_circuito NOT NULL,

    numero_version INTEGER NOT NULL,

    nombre_plantilla TEXT NOT NULL,

    descripcion TEXT NOT NULL,

    esquema_parametros JSONB NOT NULL,

    creado_en TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE ejecucion_filtro (
    ejecucion_id UUID PRIMARY KEY,

    plantilla_id UUID NOT NULL
        REFERENCES plantilla_filtro(plantilla_id),

    tipo_filtro tipo_filtro_circuito NOT NULL,

    nombre_ejecucion TEXT NOT NULL,

    configuracion_de_ejecucion JSONB NOT NULL,

    estado_ejecucion TEXT NOT NULL,

    creado_en TIMESTAMP NOT NULL DEFAULT NOW()
);