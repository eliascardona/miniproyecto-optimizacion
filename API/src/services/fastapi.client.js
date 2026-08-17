/**
 * Cliente HTTP interno para comunicarse con el FastAPI Worker.
 *
 * Express (BFF) delega la ejecucion del algoritmo de optimizacion
 * al FastAPI Worker que corre en el puerto 8000.
 *
 * Endpoints consumidos:
 *   GET  /health   - Verifica que el worker este activo.
 *   POST /optimize - Envia la configuracion y recibe el resultado.
 */

const axios = require('axios');

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8001';

/**
 * Verifica el health del FastAPI Worker.
 * Timeout: 5 segundos (el worker responde casi instantaneamente).
 */
async function fastapiHealth() {
    const { data } = await axios.get(`${FASTAPI_URL}/health`, { timeout: 5000 });
    return data;
}

/**
 * Envia una solicitud de optimizacion al FastAPI Worker.
 * El worker valida Nivel 2, genera config.json, ejecuta el script Python,
 * y retorna el resultado (fitness, componentes optimizados, grafica).
 *
 * Timeout: 300 segundos (5 minutos) por si el algoritmo tarda.
 */
async function optimizeCircuit(config) {
    const { data } = await axios.post(`${FASTAPI_URL}/optimize`, config, { timeout: 300000 });
    return data;
}

module.exports = { fastapiHealth, optimizeCircuit };
