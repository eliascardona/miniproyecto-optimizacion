# ENUM polimorfico

```sql id="9zv1yk"
CREATE TYPE tipo_filtro_circuito AS ENUM (
    'PASA_BAJA',
    'PASA_ALTA',
    'PASA_BANDA'
);
```

---

# Tabla padre — plantilla_filtro

```sql id="g3m5rp"
CREATE TABLE plantilla_filtro (
    plantilla_id UUID PRIMARY KEY,

    tipo_filtro tipo_filtro_circuito NOT NULL,

    numero_version INTEGER NOT NULL,

    nombre_plantilla TEXT NOT NULL,

    descripcion TEXT NOT NULL,

    esquema_parametros JSONB NOT NULL,

    creado_en TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

# Tabla hija — ejecucion_filtro

```sql id="y0n8fd"
CREATE TABLE ejecucion_filtro (
    ejecucion_id UUID PRIMARY KEY,

    plantilla_id UUID NOT NULL
        REFERENCES plantilla_filtro(plantilla_id),

    tipo_filtro tipo_filtro_circuito NOT NULL,

    nombre_ejecucion TEXT NOT NULL,

    configuracion_ejecucion JSONB NOT NULL,

    estado_ejecucion TEXT NOT NULL,

    creado_en TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

# INSERT — plantilla PASA_BAJA

```sql id="z4x7lu"
INSERT INTO plantilla_filtro (
    plantilla_id,
    tipo_filtro,
    numero_version,
    nombre_plantilla,
    descripcion,
    esquema_parametros
)
VALUES (
    '11111111-1111-1111-1111-111111111111',

    'PASA_BAJA',

    1,

    'Plantilla Filtro Pasa-Baja v1',

    'Optimizacion genetica para filtro pasa-baja',

    '{
        "parametros_requeridos": [
            "frecuencia_corte",
            "voltaje_entrada",
            "resistencia"
        ],
        "tipos_parametros": {
            "frecuencia_corte": "number",
            "voltaje_entrada": "number",
            "resistencia": "number"
        },
        "unidades": {
            "frecuencia_corte": "Hz",
            "voltaje_entrada": "V",
            "resistencia": "Ohm"
        }
    }'
);
```

| plantilla_id                         | tipo_filtro | numero_version | nombre_plantilla              | descripcion                                 |
| ------------------------------------ | ----------- | -------------- | ----------------------------- | ------------------------------------------- |
| 11111111-1111-1111-1111-111111111111 | PASA_BAJA   | 1              | Plantilla Filtro Pasa-Baja v1 | Optimizacion genetica para filtro pasa-baja |

---

# INSERT — plantilla PASA_BANDA

```sql id="l2q6js"
INSERT INTO plantilla_filtro (
    plantilla_id,
    tipo_filtro,
    numero_version,
    nombre_plantilla,
    descripcion,
    esquema_parametros
)
VALUES (
    '22222222-2222-2222-2222-222222222222',

    'PASA_BANDA',

    1,

    'Plantilla Filtro Pasa-Banda v1',

    'Optimizacion genetica para filtro pasa-banda',

    '{
        "parametros_requeridos": [
            "frecuencia_corte_baja",
            "frecuencia_corte_alta",
            "ganancia",
            "voltaje_entrada"
        ],
        "tipos_parametros": {
            "frecuencia_corte_baja": "number",
            "frecuencia_corte_alta": "number",
            "ganancia": "number",
            "voltaje_entrada": "number"
        },
        "unidades": {
            "frecuencia_corte_baja": "Hz",
            "frecuencia_corte_alta": "Hz",
            "ganancia": "dB",
            "voltaje_entrada": "V"
        }
    }'
);
```

| plantilla_id                         | tipo_filtro | numero_version | nombre_plantilla               | descripcion                                  |
| ------------------------------------ | ----------- | -------------- | ------------------------------ | -------------------------------------------- |
| 22222222-2222-2222-2222-222222222222 | PASA_BANDA  | 1              | Plantilla Filtro Pasa-Banda v1 | Optimizacion genetica para filtro pasa-banda |

---

# INSERT — ejecucion PASA_BAJA

```sql id="x1k5hv"
INSERT INTO ejecucion_filtro (
    ejecucion_id,
    plantilla_id,
    tipo_filtro,
    nombre_ejecucion,
    configuracion_ejecucion,
    estado_ejecucion
)
VALUES (
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',

    '11111111-1111-1111-1111-111111111111',

    'PASA_BAJA',

    'Optimizacion Pasa-Baja #1',

    '{
        "frecuencia_corte": 1200,
        "voltaje_entrada": 5,
        "resistencia": 220
    }',

    'PENDIENTE'
);
```

| ejecucion_id                         | plantilla_id                         | tipo_filtro | nombre_ejecucion          | estado_ejecucion |
| ------------------------------------ | ------------------------------------ | ----------- | ------------------------- | ---------------- |
| aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa | 11111111-1111-1111-1111-111111111111 | PASA_BAJA   | Optimizacion Pasa-Baja #1 | PENDIENTE        |

---

# INSERT — ejecucion PASA_BANDA

```sql id="d7n4pe"
INSERT INTO ejecucion_filtro (
    ejecucion_id,
    plantilla_id,
    tipo_filtro,
    nombre_ejecucion,
    configuracion_ejecucion,
    estado_ejecucion
)
VALUES (
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',

    '22222222-2222-2222-2222-222222222222',

    'PASA_BANDA',

    'Optimizacion Pasa-Banda #1',

    '{
        "frecuencia_corte_baja": 500,
        "frecuencia_corte_alta": 5000,
        "ganancia": 12,
        "voltaje_entrada": 9
    }',

    'EJECUTANDOSE'
);
```

| ejecucion_id                         | plantilla_id                         | tipo_filtro | nombre_ejecucion           | estado_ejecucion |
| ------------------------------------ | ------------------------------------ | ----------- | -------------------------- | ---------------- |
| bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb | 22222222-2222-2222-2222-222222222222 | PASA_BANDA  | Optimizacion Pasa-Banda #1 | EJECUTANDOSE     |

---

# Ejemplo JSON REST API — PASA_BAJA

```json id="s8r0jq"
{
  "ejecucion_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",

  "nombre_ejecucion": "Optimizacion Pasa-Baja #1",

  "estado_ejecucion": "PENDIENTE",

  "plantilla": {
    "plantilla_id": "11111111-1111-1111-1111-111111111111",

    "tipo_filtro": "PASA_BAJA",

    "numero_version": 1,

    "descripcion": "Optimizacion genetica para filtro pasa-baja"
  },

  "configuracion_recibida": {
    "frecuencia_corte": 1200,
    "voltaje_entrada": 5,
    "resistencia": 220
  }
}
```

---

# Ejemplo JSON REST API — PASA_BANDA

```json id="v6m9cf"
{
  "ejecucion_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",

  "nombre_ejecucion": "Optimizacion Pasa-Banda #1",

  "estado_ejecucion": "EJECUTANDOSE",

  "plantilla": {
    "plantilla_id": "22222222-2222-2222-2222-222222222222",

    "tipo_filtro": "PASA_BANDA",

    "numero_version": 1,

    "descripcion": "Optimizacion genetica para filtro pasa-banda"
  },

  "configuracion_recibida": {
    "frecuencia_corte_baja": 500,
    "frecuencia_corte_alta": 5000,
    "ganancia": 12,
    "voltaje_entrada": 9
  }
}
```
