/**
 * Ruta: GET /api/health
 *
 * Verifica el estado de los 3 componentes del sistema:
 *   - API (Express): siempre UP si responde.
 *   - Database (PostgreSQL): prueba con SELECT 1.
 *   - FastAPI Worker: consulta su endpoint /health interno.
 *
 * Retorna HTTP 200 si todo esta UP, 503 si algun componente falla.
 */

const express = require('express');
const router = express.Router();
const pool = require('../config/postgrs');
const { fastapiHealth } = require('../services/fastapi.client');

router.get('/health', async (req, res) => {
    const health = { api: 'UP', database: 'DOWN', fastapi: 'DOWN' };

    try {
        await pool.query('SELECT 1');
        health.database = 'UP';
    } catch (e) {
        health.database = 'DOWN';
    }

    try {
        const fapi = await fastapiHealth();
        health.fastapi = fapi.status === 'UP' ? 'UP' : 'DOWN';
    } catch (e) {
        health.fastapi = 'DOWN';
    }

    const allUp = Object.values(health).every(v => v === 'UP');
    res.status(allUp ? 200 : 503).json(health);
});

module.exports = router;
