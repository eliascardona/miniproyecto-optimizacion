/**
 * Configuracion del pool de conexiones a PostgreSQL.
 *
 * Lee las credenciales desde variables de entorno (.env).
 * Exporta una instancia de Pool que se reutiliza en toda la aplicacion.
 */

const { Pool } = require('pg');

const pool = new Pool({
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT || '5432'),
    database: process.env.DB_NAME || 'optimizacion_circuitos',
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || '',
    max: 10,                        // Maximo de conexiones simultaneas en el pool
    idleTimeoutMillis: 30000,       // Cierra conexiones inactivas despues de 30s
});

// Manejador de errores inesperados en conexiones del pool
pool.on('error', (err) => {
    console.error('Error inesperado en el pool de PostgreSQL:', err);
});

module.exports = pool;
