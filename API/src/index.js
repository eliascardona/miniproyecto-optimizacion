/**
 * Punto de entrada de la API REST (BFF - Backend for Frontend).
 *
 * Arquitectura:
 *   Frontend -> Express (port 3000) -> FastAPI Worker (port 8000) -> Scripts Python
 *
 * Express actua como capa intermedia que:
 *   1. Expone endpoints REST para el frontend.
 *   2. Valida el config.json antes de enviarlo al worker (Nivel 1).
 *   3. Persiste ejecuciones en PostgreSQL.
 *   4. Delega la ejecucion del algoritmo al FastAPI Worker.
 */

require("dotenv").config();
const express = require("express");
const morgan = require("morgan");
const { corsMiddleware } = require("./middlewares/cors.js");
const { notFoundMiddleware } = require("./middlewares/notFound.js");
const pool = require("./config/postgrs");

const healthRoutes = require("./routes/health.js");
const plantillasRoutes = require("./routes/plantillas.js");
const ejecucionesRoutes = require("./routes/ejecuciones.js");

const app = express();

// Middlewares globales
app.use(morgan("common"));       // Logging de requests HTTP
app.use(express.json());         // Parseo de bodies JSON
app.use(corsMiddleware);         // Headers CORS para preflight y requests normales

// Ruta raiz: informacion general de la API
app.get("/", (req, res) => {
    res.json({
        nombre: "API de Optimizacion de Filtros Activos Analogicos",
        version: "1.0.0",
        arquitectura: "Express (BFF) -> FastAPI Worker -> Scripts Python (AG/PSO)",
        documentacion: "API/README.md",
        swagger_worker: "http://localhost:8001/docs",
        endpoints: {
            health: "GET /api/health",
            plantillas: "GET /api/plantillas",
            plantilla_por_tipo: "GET /api/plantillas/:tipo",
            ejecuciones: "GET /api/ejecuciones",
            ejecucion_por_id: "GET /api/ejecuciones/:id",
            crear_ejecucion: "POST /api/ejecuciones",
            ejecutar_optimizacion: "POST /api/ejecuciones/:id/ejecutar",
            eliminar_ejecucion: "DELETE /api/ejecuciones/:id"
        }
    });
});

// Rutas de la API
app.use("/api", healthRoutes);
app.use("/api/plantillas", plantillasRoutes);
app.use("/api/ejecuciones", ejecucionesRoutes);

// Ruta no encontrada (debe ir despues de todas las rutas)
app.use(notFoundMiddleware);

// Handler global de errores no capturados
app.use((err, req, res, next) => {
    console.error("Error capturado por middleware global:", err.message);
    res.status(500).json({ error: "Error interno del servidor" });
});

const PORT = process.env.PORT || 3000;

/**
 * Inicializacion:
 * 1. Verifica conexion a PostgreSQL.
 * 2. Levanta el servidor Express.
 */
(async () => {
    try {
        await pool.query('SELECT 1');
        console.log("PostgreSQL conectado");

        app.listen(PORT, () => {
            console.log(`API ejecutandose en puerto ${PORT}`);
        });
    } catch (err) {
        console.error("No se pudo iniciar el servidor:", err.message);
        process.exit(1);
    }
})();
