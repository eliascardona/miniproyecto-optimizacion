# API — Sistema de Optimizacion de Filtros Analogicos

API Backend-for-Frontend (BFF) + Worker para optimizacion de filtros activos usando algoritmos geneticos (AG) y enjambre de particulas (PSO).

---

## Arquitectura

```
Frontend (React)
       |
       v
  Express API (port 3000)       <-- BFF, validacion Nivel 1
       |
       v
  FastAPI Worker (port 8001)    <-- validacion Nivel 2, ejecucion
       |
       v
  subprocess (Python script)    <-- caja negra del equipo de Computacion Inteligente
       |
       v
  ngspice + PostgreSQL
```

**Responsabilidades:**
- **Express API**: sirve como punto de entrada unico para el frontend. Valida tipos, rangos y seriedades basicos (Nivel 1). Persiste ejecuciones en PostgreSQL.
- **FastAPI Worker**: valida reglas avanzadas (orden de frecuencias, margenes de decade, hiperparametros) y ejecuta los scripts de optimizacion via subprocess.
- **PostgreSQL**: almacena plantillas de parametros (seeds del DDL) y historial de ejecuciones.

---

## Dependencias

### Express API (Node.js)

Versiones declaradas en `API/package.json`:

| Paquete | Version | Descripcion |
|---------|---------|-------------|
| express | ^4.21.0 | Framework HTTP |
| axios | ^1.7.0 | Cliente HTTP para FastAPI |
| pg | ^8.13.0 | Cliente PostgreSQL |
| dotenv | ^16.4.0 | Variables de entorno |
| morgan | ^1.10.0 | Logger HTTP (dev) |

### FastAPI Worker (Python)

`fastapi-worker/requirements.txt` no fija versiones exactas (`pip install -r` toma la mas reciente). Versiones con las que se ha probado el sistema:

| Paquete | Probado con | Descripcion |
|---------|-------------|-------------|
| fastapi | 0.139.2 | Framework API asincrono |
| uvicorn[standard] | 0.51.0 | Servidor ASGI |
| pydantic | 2.13.4 | Validacion de modelos |
| python-dotenv | 1.2.2 | Variables de entorno |

Los scripts de `ALGORITMOS_DE_OPTIMIZACION/` usan ademas **numpy** (se instala aparte si el script lo requiere).

### Requisitos del sistema

- **Node.js** >= 18.x
- **Python** >= 3.13
- **PostgreSQL** >= 17 (con usuario `postgres` y password `abc123`)
- **ngspice** en una ruta accesible (ver seccion ngspice mas abajo)

### Instalacion de prerequisitos (desde cero)

Si instalas desde cero en Windows:

1. **Node.js LTS** — descargar e instalar desde https://nodejs.org/ . Verificar con `node --version`.
2. **Python 3.13+** — descargar desde https://www.python.org/downloads/ . **Importante:** activar la casilla *Add python.exe to PATH* durante la instalacion. Verificar con `python --version`.
3. **PostgreSQL 17** — instalar con el instalador EDB desde https://www.postgresql.org/download/windows/ . Durante la instalacion te pide una password para el superusuario `postgres`; usa `abc123` (o pon la tuya y ajusta `API/.env`). Deja el puerto por defecto `5432`. Verificar con `pg_isready -h localhost -p 5432`.
4. **ngspice** — descargar desde https://sourceforge.net/projects/ngspice/files/ng-spice-rework/ (version 41 o superior). Se recomienda descomprimirlo en una ruta sin espacios, por ejemplo `C:\PROGRAMAS_UNI\Spice64\`, y apuntar `NGSPICE_PATH` del `.env` del worker a su `bin\ngspice.exe`.

---

## Estructura de archivos

```
API/
├── package.json
├── .env                          <-- credenciales DB + URL FastAPI (gitignored, crearlo manualmente)
├── README.md                     <-- este archivo
└── src/
    ├── index.js                  <-- punto de entrada Express
    ├── config/
    │   └── postgrs.js            <-- pool PostgreSQL (pg)
    ├── middlewares/
    │   ├── cors.js               <-- CORS para desarrollo local
    │   └── notFound.js           <-- 404 generico
    ├── routes/
    │   ├── health.js             <-- GET /api/health
    │   ├── plantillas.js         <-- GET /api/plantillas
    │   └── ejecuciones.js        <-- CRUD + POST ejecutar
    └── services/
        ├── validation.js         <-- validacion Nivel 1
        └── fastapi.client.js     <-- cliente FastAPI

fastapi-worker/
├── requirements.txt
├── .env                          <-- NGSPICE_PATH, WORKSPACE_DIR (gitignored, crearlo manualmente)
├── run.ps1                       <-- arranque independiente del worker
└── app/
    ├── main.py                   <-- FastAPI app + lifespan
    ├── config.py                 <-- rutas, enums, SCRIPT_MAP
    ├── state.py                  <-- asyncio.Lock global
    ├── models/
    │   └── schemas.py            <-- Pydantic models
    ├── routes/
    │   └── optimization.py       <-- /health, /validate, /optimize
    ├── services/
    │   ├── validation.py         <-- validacion Nivel 2
    │   ├── config_builder.py     <-- genera config.json limpio
    │   └── script_runner.py      <-- subprocess + workspace
    └── validation/
        ├── e12.py                <-- serie E12
        ├── frequencies.py        <-- reglas por tipo+modo
        └── optimizer_params.py   <-- hiperparametros AG/PSO
```

---

## Base de datos

### Creacion paso a paso (primera vez)

Si la base de datos todavia no existe en tu maquina local:

```powershell
# 1. Crea la base de datos (usa la password que configuraste al instalar PostgreSQL)
$env:PGPASSWORD = 'abc123'
psql -U postgres -c "CREATE DATABASE optimizacion_circuitos;"

# 2. Carga el DDL (crea las tablas y siembra las 4 plantillas de filtro)
psql -U postgres -d optimizacion_circuitos -f MODELOS_DE_DATOS\VERSIONADO_INTERNO\postgres-ddl-v2.sql

# 3. Verifica: deberia listar PASA_BAJA, PASA_ALTA, PASA_BANDA, RECHAZO_BANDA
psql -U postgres -d optimizacion_circuitos -c "SELECT tipo_filtro FROM plantilla_filtro;"
```

> Ejecuta los comandos desde la raiz del repositorio (`C:\miniproyecto-optimizacion`). El DDL **no** incluye `CREATE DATABASE`; esa se crea manualmente como en el paso 1.

### Esquema

El DDL se encuentra en `MODELOS_DE_DATOS/VERSIONADO_INTERNO/postgres-ddl-v2.sql`.

```sql
-- ENUMs
tipo_filtro_circuito:  PASA_BAJA | PASA_ALTA | PASA_BANDA | RECHAZO_BANDA
estado_ejecucion:      PENDIENTE | VALIDANDO | EJECUTANDOSE | COMPLETADO | ERROR
modo_operacion:        BASICO | AVANZADO
algoritmo_optimizacion: AG | PSO

-- Tablas
plantilla_filtro  (1) ----> (N) ejecucion_filtro
  - plantilla_id (UUID PK)
  - tipo_filtro
  - esquema_parametros (JSONB)

ejecucion_filtro
  - ejecucion_id (UUID PK)
  - plantilla_id (UUID FK)
  - configuracion_ejecucion (JSONB) <-- config completo del usuario
  - resultado (JSONB)               <-- resultado.json del script
  - estado_ejecucion
```

### Configuracion de conexion (`API/.env`)

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=optimizacion_circuitos
DB_USER=postgres
DB_PASSWORD=abc123
PORT=3000
FASTAPI_URL=http://localhost:8001
```

Si falta alguna variable, `postgrs.js` usa estos fallbacks:

| Variable | Fallback |
|----------|----------|
| `DB_HOST` | `localhost` |
| `DB_PORT` | `5432` |
| `DB_NAME` | `optimizacion_circuitos` |
| `DB_USER` | `postgres` |
| `DB_PASSWORD` | `""` (vacio) |

El pool tiene un maximo de **10 conexiones simultaneas** y cierra conexiones idle despues de **30 segundos**.

Si PostgreSQL no esta disponible al arrancar Express, el proceso **termina inmediatamente** (`process.exit(1)`). No arranca el server si la DB no responde.

---

## Endpoints

### Express API (port 3000)

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/api/health` | Estado de API + DB + FastAPI |
| GET | `/api/plantillas` | Lista las 4 plantillas de filtro |
| GET | `/api/plantillas/:tipo` | Plantilla por tipo (PASA_BAJA, etc.) |
| POST | `/api/ejecuciones` | Crea una ejecucion nueva |
| GET | `/api/ejecuciones` | Lista ejecuciones (paginado) |
| GET | `/api/ejecuciones/:id` | Detalle de una ejecucion |
| PATCH | `/api/ejecuciones/:id` | Actualiza nombre/descripcion |
| DELETE | `/api/ejecuciones/:id` | Elimina una ejecucion |
| POST | `/api/ejecuciones/:id/ejecutar` | **Ejecuta la optimizacion** |

#### GET `/api/health`

Verifica los 3 componentes del sistema. Retorna HTTP **200** si todos estan UP, HTTP **503** si alguno falla.

```json
{
  "api": "UP",
  "database": "UP",
  "fastapi": "UP"
}
```

- `database`: ejecuta `SELECT 1` contra PostgreSQL.
- `fastapi`: llama a `GET {FASTAPI_URL}/health` con timeout de **5 segundos**.

#### GET `/api/plantillas`

Retorna las 4 plantillas semilla ordenadas por `tipo_filtro`. Estas vienen del DDL, no se crean desde la API.

#### GET `/api/plantillas/:tipo`

El param `:tipo` se convierte automaticamente a mayusculas (`.toUpperCase()`).

#### POST `/api/ejecuciones`

Body:

```json
{
  "tipo_filtro": "PASA_BAJA",
  "algoritmo": "AG",
  "nombre_ejecucion": "Mi optimizacion",
  "configuracion": { ... }
}
```

- Ejecuta validacion Nivel 1 antes de guardar.
- Busca la plantilla mas reciente para el `tipo_filtro` (`ORDER BY numero_version DESC LIMIT 1`).
- Si `nombre_ejecucion` no se provee, usa `"Optimizacion {TIPO_FILTRO}"`.
- Estado inicial: `PENDIENTE`.

#### GET `/api/ejecuciones`

Soporta paginacion:

| Query param | Default | Restriccion |
|-------------|---------|-------------|
| `page` | `1` | minimo 1 |
| `limit` | `10` | minimo 1, maximo 50 |

Respuesta:

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 42,
    "pages": 5
  }
}
```

#### POST `/api/ejecuciones/:id/ejecutar`

- Si la ejecucion ya esta en estado `EJECUTANDOSE`, retorna HTTP **409**.
- Cambia estado a `EJECUTANDOSE`, envia la configuracion al FastAPI Worker.
- Si el worker falla, cambia estado a `ERROR`.
- Si termina bien, cambia estado a `COMPLETADO` y guarda el `resultado`.
- Timeout del worker: **5 minutos** (300,000 ms).

### FastAPI Worker (port 8001)

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/health` | Estado del worker |
| POST | `/validate` | Valida sin ejecutar (debug) |
| POST | `/optimize` | Valida + ejecuta el algoritmo |

Swagger UI: http://localhost:8001/docs

---

## ngspice

El ejecutable de ngspice se configura en `fastapi-worker/.env`. Este archivo **no viene en el repo** (esta en `.gitignore`); crealo en `fastapi-worker/.env` con:

```env
NGSPICE_PATH=C:\PROGRAMAS_UNI\Spice64\bin\ngspice.exe
WORKSPACE_DIR=tempwork
```

| Variable | Default si falta | Descripcion |
|----------|------------------|-------------|
| `NGSPICE_PATH` | `C:\PROGRAMAS_UNI\Spice64\bin\ngspice.exe` | Ruta completa al ejecutable de ngspice |
| `WORKSPACE_DIR` | `tempwork` | Directorio base de trabajo temporal |

Si ngspice esta en otra ubicacion, **cambiar el valor de `NGSPICE_PATH`**. El directorio del ejecutable se inyecta automaticamente al `PATH` del subprocess que ejecuta cada script Python.

**ngspice no es thread-safe.** El FastAPI Worker usa un `asyncio.Lock` global para garantizar que solo un subprocess de ngspice se ejecute a la vez. Si se envian dos solicitudes de optimizacion simultaneas, la segunda espera a que termine la primera.

---

## Config.json (formato que consumen los scripts)

El `config.json` que escriben los scripts **NO incluye** `tipo_filtro` ni `algoritmo`. Estos campos se usan solo para seleccionar que script ejecutar, y se ignoran dentro de el.

El `config_builder.py` transforma el formato HTTP (arreglos `{clave, valor}`) al formato de diccionario plano que los scripts esperan via su funcion `_buscar_etiqueta()`:

**Entrada HTTP (parametros_optimizador):**
```json
[
  {"clave": "tam_poblacion", "valor": 50},
  {"clave": "num_generaciones", "valor": 200}
]
```

**Salida config.json (lo que ve el script):**
```json
{
  "parametros_optimizador": {
    "tam_poblacion": 50,
    "num_generaciones": 200
  }
}
```

Lo mismo aplica para `frecuencias`. Los bloques `modo`, `entorno` y `barrido_ac` pasan sin transformacion.

---

## Validacion (dos niveles)

### Nivel 1 (Express — antes de guardar en DB)

Se ejecuta en `POST /api/ejecuciones` antes de persistir.

**Enums estrictos:**
- `tipo_filtro`: PASA_BAJA, PASA_ALTA, PASA_BANDA, RECHAZO_BANDA
- `algoritmo`: AG, PSO
- `modo`: BASICO, AVANZADO (se normaliza a mayusculas, acepta entrada case-insensitive)

**Entorno:**
| Campo | Regla | Nota |
|-------|-------|------|
| `v_fuente` | > 0, numero | Recomendado <= 10 V (limitacion del LM741) |
| `r_fuente` | > 0, serie E12 | mantisa tolerancia < 0.01 |
| `r_carga` | > 0, serie E12 | mantisa tolerancia < 0.01 |

**Barrido AC:**
| Campo | Regla |
|-------|-------|
| `f_inicial` | entero > 0 |
| `f_final` | entero > 0, <= 10,000,000 Hz |
| ambos | `f_inicial < f_final` |

**Frecuencias — claves requeridas por tipo+modo:**

| Tipo | BASICO | AVANZADO |
|------|--------|----------|
| PASA_BAJA | `fc_objetivo` | `f_paso`, `f_aten` |
| PASA_ALTA | `fc_objetivo` | `f_aten`, `f_paso` |
| PASA_BANDA | `fc_inferior`, `fc_superior` | `f_aten_1`, `f_paso_1`, `f_paso_2`, `f_aten_2` |
| RECHAZO_BANDA | `fc_inferior`, `fc_superior` | `f_paso_1`, `f_aten_1`, `f_aten_2`, `f_paso_2` |

**Orden de frecuencias (modo AVANZADO):**
- PASA_BAJA: `f_paso < f_aten`
- PASA_ALTA: `f_aten < f_paso`
- PASA_BANDA: `f_aten_1 < f_paso_1 <= f_paso_2 < f_aten_2`
- RECHAZO_BANDA: `f_paso_1 < f_aten_1 <= f_aten_2 < f_paso_2`

**Margen de una decade:**
La frecuencia de interes mas baja debe ser >= `f_inicial * 10`, y la mas alta <= `f_final / 10`.

**Hiperparametros AG:**

| Parametro | Tipo | Rango |
|-----------|------|-------|
| `tam_poblacion` | entero | >= 1 |
| `num_generaciones` | entero | >= 1 |
| `prob_cruce` | number | [0, 1] |
| `prob_mutacion` | number | [0, 1] |
| `elitismo` | entero | >= 0, **< tam_poblacion** |
| `torneo_k` | entero | >= 1 |

**Hiperparametros PSO:**

| Parametro | Tipo | Rango |
|-----------|------|-------|
| `num_particulas` | entero | >= 1 |
| `num_iteraciones` | entero | >= 0 |
| `w` | number | [0, 1] |
| `c1` | number | **> 0** (estricto) |
| `c2` | number | **> 0** (estricto) |

### Nivel 2 (FastAPI — antes de ejecutar)

Se ejecuta dentro del worker antes de generar el `config.json`. Las reglas son iguales a Nivel 1 pero sobre el formato ya transformado (objetos planos, no arreglos). Tambien verifica que `frecuencias` y `parametros_optimizador` **no** sean arreglos.

---

## Ejecucion de scripts (script_runner)

Cuando el worker recibe `POST /optimize`:

1. **Busca el script** en `SCRIPT_MAP` usando `tipo_filtro` + `algoritmo`.
2. **Crea un directorio temporal** (`tempfile.mkdtemp(prefix="opt_")`).
3. **Copia el script** al workspace temporal (no modifica los archivos originales).
4. **Escribe `config.json`** con la configuracion del usuario.
5. **Inyecta ngspice al PATH**: copia `os.environ` y prepone el directorio de `NGSPICE_PATH` al PATH.
6. **Ejecuta**: `python -u {script}` con `cwd=workspace`. Flag `-u` = output sin buffer.
7. **Lee `resultado.json`** generado por el script.
8. **Elimina el workspace** en el bloque `finally` (siempre, incluso si falla).

Si el script retorna codigo distinto de 0, o no genera `resultado.json`, retorna error con el stderr.

---

## CORS

Configurado en `src/middlewares/cors.js`:

- **Origen permitido**: `process.env.CORS_ORIGIN` o `*` (wildcard por defecto).
- **Metodos**: GET, POST, PUT, DELETE, OPTIONS.
- **Headers**: Content-Type, Authorization.
- Los requests OPTIONS (preflight) retornan 204 inmediatamente sin pasar al siguiente middleware.

---

## Como ejecutar

### Inicio completo (desde la raiz del proyecto)

```powershell
.\run.ps1
```

Esto:
1. Verifica que PostgreSQL este corriendo (`pg_isready -h localhost -p 5432`). Si no responde, **detiene todo**.
2. Inicia FastAPI Worker en ventana separada (con `--reload` para desarrollo).
3. Espera hasta **15 segundos** a que el worker responda en `/health`. Si no responde,continua de todas formas con un warning.
4. Inicia Express API en ventana separada.

### Inicio individual

**Solo FastAPI Worker:**

Primera vez (crear entorno virtual):
```powershell
cd fastapi-worker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Si ya existe `.venv`:
```powershell
cd fastapi-worker
.\run.ps1
```

**Solo Express API:**

Primera vez (instalar dependencias):
```powershell
cd API
npm install
node src/index.js
```

Si ya existen `node_modules`:
```powershell
cd API
node src/index.js
```

Si PostgreSQL no esta disponible, el proceso termina inmediatamente.

### Verificar que funciona

```powershell
# Health check (deberia mostrar los 3 componentes UP)
Invoke-RestMethod http://localhost:3000/api/health

# Obtener las 4 plantillas
Invoke-RestMethod http://localhost:3000/api/plantillas

# Crear ejecucion
$body = @{
    nombre_ejecucion = "Test GA basico 1kHz"
    tipo_filtro = "PASA_BAJA"
    algoritmo = "AG"
    configuracion = @{
        modo = "BASICO"
        entorno = @{ v_fuente = 10; r_fuente = 10000; r_carga = 10000 }
        barrido_ac = @{ f_inicial = 100; f_final = 10000000 }
        parametros_optimizador = @(
            @{ clave = "tam_poblacion"; valor = 5 }
            @{ clave = "num_generaciones"; valor =  10 }
            @{ clave = "prob_cruce"; valor = 0.9 }
            @{ clave = "prob_mutacion"; valor = 0.1 }
            @{ clave = "elitismo"; valor = 2 }
            @{ clave = "torneo_k"; valor = 3 }
        )
        frecuencias = @(
            @{ clave = "fc_objetivo"; valor = 1000 }
        )
    }
} | ConvertTo-Json -Depth 10

# Copia el ID que retorna la respuesta
$ejecucion = Invoke-RestMethod -Uri "http://localhost:3000/api/ejecuciones" -Method POST -Body $body -ContentType "application/json"
$id = $ejecucion.ejecucion_id
Write-Host "ID: $id"

# Ejecutar la optimizacion reemplazando "$id" por el ID copiado en el paso anterior
Invoke-RestMethod -Uri "http://localhost:3000/api/ejecuciones/$id/ejecutar" -Method POST
```

---

## Observaciones

### Seguridad

- La password de PostgreSQL (`abc123`) esta en texto plano en `.env`. No commitear este archivo a repositorios publicos (ambos `.env`, API y worker, estan en `.gitignore`).

### Comportamiento al fallo

- Si Express no puede conectar a PostgreSQL al arrancar, **termina el proceso** (`process.exit(1)`).
- Si el FastAPI Worker no responde en 15 segundos durante el arranque de `run.ps1`, continua con un warning pero Express no podra ejecutar optimizaciones.
- Si una ejecucion ya esta corriendo (`EJECUTANDOSE`) y se intenta ejecutar de nuevo, retorna HTTP 409.
- Los scripts Python se ejecutan en un workspace temporal que se elimina siempre, incluso si falla.
- Si el script retorna error o no genera `resultado.json`, la ejecucion se marca como `ERROR`.

### Timeout de optimizacion

El timeout de Express hacia FastAPI es de **5 minutos** (300,000 ms). Si un algoritmo tarda mas que eso, Express corta la conexion y la ejecucion queda en estado inconsistente (el worker seguira corriendo en background pero Express no recibira respuesta).

### Concurrencia

El `asyncio.Lock` en el worker garantiza que solo un subprocess de ngspice se ejecute a la vez. Si se envian dos solicitudes simultaneas, la segunda encola. No hay limite de cola implementado.

### Scripts como cajas negras

Los scripts Python dentro de `ALGORITMOS_DE_OPTIMIZACION/` son mantenidos por el equipo de Computacion Inteligente. La API no los modifica; los copia a un workspace temporal, ejecuta, y lee `resultado.json`. Si los scripts cambian su formato de entrada o salida, la API se rompera silenciosamente.
