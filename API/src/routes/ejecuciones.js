/**
 * Rutas: /api/ejecuciones
 *
 * CRUD completo para ejecuciones de optimizacion de filtros.
 * Cada ejecucion representa una configuracion concreta de filtro + algoritmo
 * que se envia al FastAPI Worker para ser resuelta.
 *
 * Flujo tipico:
 *   POST /             - Crear ejecucion (valida Nivel 1, guarda en DB).
 *   POST /:id/ejecutar - Ejecutar la optimizacion (delega al FastAPI Worker).
 *   GET /              - Listar ejecuciones (paginado).
 *   GET /:id           - Detalle de una ejecucion + resultado.
 *   DELETE /:id        - Eliminar ejecucion.
 */

const express = require('express');
const router = express.Router();
const pool = require('../config/postgrs');
const { validarConfigCompleta } = require('../services/validation');
const { optimizeCircuit } = require('../services/fastapi.client');

/**
 * GET /api/ejecuciones
 * Lista ejecuciones con paginacion.
 * Query params: page (default 1), limit (default 10, max 50).
 */
router.get('/', async (req, res) => {
    try {
        const page = Math.max(1, parseInt(req.query.page) || 1);
        const limit = Math.min(50, Math.max(1, parseInt(req.query.limit) || 10));
        const offset = (page - 1) * limit;

        const countResult = await pool.query('SELECT COUNT(*) FROM ejecucion_filtro');
        const total = parseInt(countResult.rows[0].count);

        const { rows } = await pool.query(
            `SELECT ejecucion_id, plantilla_id, tipo_filtro, algoritmo, modo,
                    nombre_ejecucion, estado_ejecucion, creado_en, actualizado_en
             FROM ejecucion_filtro
             ORDER BY creado_en DESC
             LIMIT $1 OFFSET $2`,
            [limit, offset]
        );

        res.json({
            data: rows,
            pagination: { page, limit, total, pages: Math.ceil(total / limit) }
        });
    } catch (err) {
        console.error('Error al listar ejecuciones:', err);
        res.status(500).json({ error: 'Error interno al consultar ejecuciones' });
    }
});

/**
 * GET /api/ejecuciones/:id
 * Detalle completo de una ejecucion, incluyendo resultado y datos de la plantilla.
 */
router.get('/:id', async (req, res) => {
    try {
        const { id } = req.params;
        const { rows } = await pool.query(
            `SELECT e.*, p.nombre_plantilla, p.descripcion as plantilla_descripcion
             FROM ejecucion_filtro e
             JOIN plantilla_filtro p ON e.plantilla_id = p.plantilla_id
             WHERE e.ejecucion_id = $1`,
            [id]
        );

        if (rows.length === 0) {
            return res.status(404).json({ error: 'Ejecucion no encontrada' });
        }

        res.json(rows[0]);
    } catch (err) {
        console.error('Error al obtener ejecucion:', err);
        res.status(500).json({ error: 'Error interno al consultar ejecucion' });
    }
});

/**
 * POST /api/ejecuciones
 * Crea una nueva ejecucion de optimizacion.
 *
 * Body esperado:
 *   { tipo_filtro, algoritmo, nombre_ejecucion, configuracion }
 *
 * Flujo:
 *   1. Valida la configuracion completa (Nivel 1: tipos, rangos, E12, etc.)
 *   2. Busca la plantilla vigente para el tipo de filtro.
 *   3. Inserta la ejecucion en estado PENDIENTE.
 */
router.post('/', async (req, res) => {
    try {
        const { tipo_filtro, algoritmo, nombre_ejecucion, configuracion } = req.body;

        // Validacion Nivel 1: forma, tipos de dato, rangos fijos, serie E12
        const validacion = validarConfigCompleta(configuracion, tipo_filtro, algoritmo);
        if (!validacion.valido) {
            return res.status(400).json({
                error: 'Error de validacion',
                detalles: validacion.errores
            });
        }

        const tipoFiltroUpper = tipo_filtro.toUpperCase();
        const algoritmoUpper = algoritmo.toUpperCase();
        const modo = configuracion.modo;

        // Busca la plantilla mas reciente para este tipo de filtro
        const plantillaResult = await pool.query(
            'SELECT plantilla_id FROM plantilla_filtro WHERE tipo_filtro = $1 ORDER BY numero_version DESC LIMIT 1',
            [tipoFiltroUpper]
        );

        if (plantillaResult.rows.length === 0) {
            return res.status(400).json({ error: `No existe plantilla para el tipo "${tipoFiltroUpper}"` });
        }

        const plantilla_id = plantillaResult.rows[0].plantilla_id;

        const { rows } = await pool.query(
            `INSERT INTO ejecucion_filtro
                (plantilla_id, tipo_filtro, algoritmo, modo, nombre_ejecucion, configuracion_ejecucion, estado_ejecucion)
             VALUES ($1, $2, $3, $4, $5, $6, 'PENDIENTE')
             RETURNING ejecucion_id, plantilla_id, tipo_filtro, algoritmo, modo,
                       nombre_ejecucion, configuracion_ejecucion, estado_ejecucion, creado_en`,
            [plantilla_id, tipoFiltroUpper, algoritmoUpper, modo,
             nombre_ejecucion || `Optimizacion ${tipoFiltroUpper}`, JSON.stringify(configuracion)]
        );

        res.status(201).json(rows[0]);
    } catch (err) {
        console.error('Error al crear ejecucion:', err);
        res.status(500).json({ error: 'Error interno al crear ejecucion' });
    }
});

/**
 * POST /api/ejecuciones/:id/ejecutar
 * Envia la ejecucion al FastAPI Worker para optimizar.
 *
 * Flujo:
 *   1. Recupera la ejecucion de la DB.
 *   2. Verifica que no este ya en curso.
 *   3. Marca como EJECUTANDOSE.
 *   4. Envia tipo_filtro + algoritmo + configuracion al FastAPI Worker.
 *   5. El worker valida Nivel 2, genera config.json, ejecuta el script Python.
 *   6. Guarda el resultado y marca como COMPLETADO o ERROR.
 *
 * Nota: tipo_filtro y algoritmo se envian al worker para que este seleccione
 * el script correcto, pero NO se incluyen dentro del config.json que lee el script.
 */
router.post('/:id/ejecutar', async (req, res) => {
    try {
        const { id } = req.params;

        const ejecResult = await pool.query(
            `SELECT configuracion_ejecucion, estado_ejecucion, tipo_filtro, algoritmo
             FROM ejecucion_filtro WHERE ejecucion_id = $1`,
            [id]
        );

        if (ejecResult.rows.length === 0) {
            return res.status(404).json({ error: 'Ejecucion no encontrada' });
        }

        const ejecucion = ejecResult.rows[0];

        if (ejecucion.estado_ejecucion === 'EJECUTANDOSE') {
            return res.status(409).json({ error: 'La ejecucion ya esta en curso' });
        }

        // Marca la ejecucion como en curso
        await pool.query(
            `UPDATE ejecucion_filtro SET estado_ejecucion = 'EJECUTANDOSE', actualizado_en = NOW()
             WHERE ejecucion_id = $1`,
            [id]
        );

        // Delega al FastAPI Worker (valida Nivel 2 + ejecuta script)
        let resultado;
        try {
            resultado = await optimizeCircuit({
                tipo_filtro: ejecucion.tipo_filtro,
                algoritmo: ejecucion.algoritmo,
                configuracion: ejecucion.configuracion_ejecucion,
            });
        } catch (execErr) {
            await pool.query(
                `UPDATE ejecucion_filtro SET estado_ejecucion = 'ERROR', actualizado_en = NOW()
                 WHERE ejecucion_id = $1`,
                [id]
            );
            return res.status(500).json({
                error: 'Error durante la ejecucion del algoritmo de optimizacion',
                detalles: execErr.message
            });
        }

        // Guarda el resultado y marca como completada
        const { rows } = await pool.query(
            `UPDATE ejecucion_filtro
             SET estado_ejecucion = 'COMPLETADO',
                 resultado = $1,
                 actualizado_en = NOW()
             WHERE ejecucion_id = $2
             RETURNING ejecucion_id, tipo_filtro, algoritmo, modo,
                       nombre_ejecucion, configuracion_ejecucion, estado_ejecucion,
                       resultado, creado_en, actualizado_en`,
            [JSON.stringify(resultado), id]
        );

        res.json(rows[0]);
    } catch (err) {
        console.error('Error al ejecutar:', err);
        res.status(500).json({ error: 'Error interno al ejecutar optimizacion' });
    }
});

/**
 * DELETE /api/ejecuciones/:id
 * Elimina una ejecucion por su ID.
 */
router.delete('/:id', async (req, res) => {
    try {
        const { id } = req.params;

        const { rows } = await pool.query(
            `DELETE FROM ejecucion_filtro WHERE ejecucion_id = $1
             RETURNING ejecucion_id`,
            [id]
        );

        if (rows.length === 0) {
            return res.status(404).json({ error: 'Ejecucion no encontrada' });
        }

        res.json({ message: 'Ejecucion eliminada', ejecucion_id: rows[0].ejecucion_id });
    } catch (err) {
        console.error('Error al eliminar ejecucion:', err);
        res.status(500).json({ error: 'Error interno al eliminar ejecucion' });
    }
});

module.exports = router;
