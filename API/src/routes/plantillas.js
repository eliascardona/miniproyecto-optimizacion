/**
 * Rutas: /api/plantillas
 *
 * Endpoints de solo lectura para consultar las plantillas de filtro.
 * Las plantillas definen que parametros espera cada tipo de filtro
 * y se cargan como seeds en el DDL (no se crean desde la API).
 *
 * GET /              - Lista todas las plantillas.
 * GET /:tipo         - Obtiene la plantilla de un tipo especifico (PASA_BAJA, PASA_ALTA, etc.)
 */

const express = require('express');
const router = express.Router();
const pool = require('../config/postgrs');

// GET /api/plantillas - Lista todas las plantillas ordenadas por tipo de filtro
router.get('/', async (req, res) => {
    try {
        const { rows } = await pool.query(
            `SELECT plantilla_id, tipo_filtro, numero_version, nombre_plantilla,
                    descripcion, esquema_parametros, creado_en
             FROM plantilla_filtro ORDER BY tipo_filtro`
        );
        res.json(rows);
    } catch (err) {
        console.error('Error al listar plantillas:', err);
        res.status(500).json({ error: 'Error interno al consultar plantillas' });
    }
});

// GET /api/plantillas/:tipo - Busca plantilla por tipo de filtro
router.get('/:tipo', async (req, res) => {
    try {
        const { tipo } = req.params;
        const { rows } = await pool.query(
            `SELECT plantilla_id, tipo_filtro, numero_version, nombre_plantilla,
                    descripcion, esquema_parametros, creado_en
             FROM plantilla_filtro WHERE tipo_filtro = $1`,
            [tipo.toUpperCase()]
        );

        if (rows.length === 0) {
            return res.status(404).json({ error: `No existe plantilla para el tipo "${tipo}"` });
        }

        res.json(rows[0]);
    } catch (err) {
        console.error('Error al obtener plantilla:', err);
        res.status(500).json({ error: 'Error interno al consultar plantilla' });
    }
});

module.exports = router;
