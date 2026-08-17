/**
 * Middleware de CORS (Cross-Origin Resource Sharing).
 *
 * Permite requests desde el frontend que se ejecute en otro dominio/puerto.
 * Responde automaticamente a preflight requests (OPTIONS) con 204.
 */

const corsMiddleware = (req, res, next) => {
    const origin = process.env.CORS_ORIGIN || '*';

    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

    // Preflight: el navegador envia OPTIONS antes de requests complejos (POST, PUT, DELETE)
    if (req.method === 'OPTIONS') {
        return res.status(204).end();
    }

    next();
};

module.exports = { corsMiddleware };
