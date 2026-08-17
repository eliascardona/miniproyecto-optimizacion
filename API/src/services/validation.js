/**
 * Servicio de validacion Nivel 1 (Express).
 *
 * Valida la configuracion de optimizacion ANTES de guardarla en la DB
 * y antes de enviarla al FastAPI Worker.
 *
 * Este nivel verifica:
 *   - Tipos de dato y presencia de claves obligatorias.
 *   - Enums estrictos (modo, tipo_filtro, algoritmo).
 *   - Rangos fijos (v_fuente > 0, f_final <= 10M, probabilidades en [0,1]).
 *   - Serie E12 para resistencias (r_fuente, r_carga).
 *   - Orden de frecuencias segun tipo de filtro y modo (Nivel 1 basico).
 *   - Margen minimo de una decade entre frecuencias y barrido AC.
 *
 * Reglas detalladas en: ALGORITMOS_DE_OPTIMIZACION/README.md
 */

const pool = require('../config/postgrs');

// Enums validos para tipo de filtro, algoritmo y modo
const VALID_FILTER_TYPES = ['PASA_BAJA', 'PASA_ALTA', 'PASA_BANDA', 'RECHAZO_BANDA'];
const VALID_ALGORITHMS = ['AG', 'PSO'];
const VALID_MODES = ['BASICO', 'AVANZADO'];

// Mantisas de la serie E12: valor = mantisa * 10^n, n = 1..5 (10 a 820,000 Ohm)
const E12_MANTISAS = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2];

/**
 * Verifica si un valor pertenece a la serie E12 comercial.
 * Descompone el valor en mantisa * 10^n y compara la mantisa contra la tabla.
 */
function esE12(valor) {
    if (typeof valor !== 'number' || valor <= 0) return false;
    const exp = Math.floor(Math.log10(valor));
    const mantisa = Math.round(valor / Math.pow(10, exp) * 1000) / 1000;
    return E12_MANTISAS.some(m => Math.abs(mantisa - m) < 0.01);
}

/**
 * Verifica si una frecuencia es "redonda": un solo digito significativo seguido de ceros.
 * Ejemplos validos: 10, 20, 500, 1000, 10000. Invalidos: 37, 150, 3300.
 * Convencion adoptada del proyecto (ver README seccion 5.1).
 */
function esFrecuenciaRedonda(valor) {
    if (typeof valor !== 'number' || valor <= 0) return false;
    if (!Number.isInteger(valor)) return false;
    const str = valor.toString();
    const primerDigito = str[0];
    const resto = str.slice(1);
    return parseInt(primerDigito) >= 1 && parseInt(primerDigito) <= 9 && /^0*$/.test(resto);
}

/**
 * Valida el bloque entorno del config.json.
 * Reglas: v_fuente > 0 y <= 10V, r_fuente y r_carga > 0 y en serie E12.
 */
function validarEntorno(entorno) {
    const errores = [];

    if (!entorno || typeof entorno !== 'object') {
        return { valido: false, errores: ['entorno es requerido y debe ser un objeto'] };
    }

    if (entorno.v_fuente === undefined) {
        errores.push('entorno.v_fuente es requerido');
    } else if (typeof entorno.v_fuente !== 'number' || entorno.v_fuente <= 0) {
        errores.push('entorno.v_fuente debe ser un numero mayor a 0');
    } else if (entorno.v_fuente > 10) {
        errores.push('entorno.v_fuente no debe exceder 10 V (recomendado para LM741)');
    }

    if (entorno.r_fuente === undefined) {
        errores.push('entorno.r_fuente es requerido');
    } else if (typeof entorno.r_fuente !== 'number' || entorno.r_fuente <= 0) {
        errores.push('entorno.r_fuente debe ser un numero mayor a 0');
    } else if (!esE12(entorno.r_fuente)) {
        errores.push(`entorno.r_fuente (${entorno.r_fuente}) no pertenece a la serie E12`);
    }

    if (entorno.r_carga === undefined) {
        errores.push('entorno.r_carga es requerido');
    } else if (typeof entorno.r_carga !== 'number' || entorno.r_carga <= 0) {
        errores.push('entorno.r_carga debe ser un numero mayor a 0');
    } else if (!esE12(entorno.r_carga)) {
        errores.push(`entorno.r_carga (${entorno.r_carga}) no pertenece a la serie E12`);
    }

    return { valido: errores.length === 0, errores };
}

/**
 * Valida el bloque barrido_ac del config.json.
 * Reglas: f_inicial y f_final enteros > 0, f_final <= 10M, f_inicial < f_final.
 */
function validarBarridoAc(barrido) {
    const errores = [];

    if (!barrido || typeof barrido !== 'object') {
        return { valido: false, errores: ['barrido_ac es requerido y debe ser un objeto'] };
    }

    if (barrido.f_inicial === undefined) {
        errores.push('barrido_ac.f_inicial es requerido');
    } else if (!Number.isInteger(barrido.f_inicial) || barrido.f_inicial <= 0) {
        errores.push('barrido_ac.f_inicial debe ser un entero mayor a 0');
    }

    if (barrido.f_final === undefined) {
        errores.push('barrido_ac.f_final es requerido');
    } else if (!Number.isInteger(barrido.f_final) || barrido.f_final <= 0) {
        errores.push('barrido_ac.f_final debe ser un entero mayor a 0');
    } else if (barrido.f_final > 10000000) {
        errores.push('barrido_ac.f_final no debe exceder 10,000,000 Hz');
    }

    if (barrido.f_inicial !== undefined && barrido.f_final !== undefined) {
        if (Number.isInteger(barrido.f_inicial) && Number.isInteger(barrido.f_final)) {
            if (barrido.f_inicial >= barrido.f_final) {
                errores.push('barrido_ac.f_inicial debe ser menor que barrido_ac.f_final');
            }
        }
    }

    return { valido: errores.length === 0, errores };
}

/**
 * Valida los hiperparametros del algoritmo de optimizacion.
 * AG: tam_poblacion, num_generaciones, prob_cruce, prob_mutacion, elitismo, torneo_k.
 * PSO: num_particulas, num_iteraciones, w, c1, c2.
 *
 * Valida tanto presencia de claves como rangos de valores.
 */
function validarParametrosOptimizador(params, algoritmo) {
    const errores = [];

    if (!Array.isArray(params)) {
        return { valido: false, errores: ['parametros_optimizador debe ser un arreglo de objetos {clave, valor}'] };
    }

    // --- Algoritmo Genetico (AG) ---
    if (algoritmo === 'AG') {
        const requeridas = ['tam_poblacion', 'num_generaciones', 'prob_cruce', 'prob_mutacion', 'elitismo', 'torneo_k'];
        const claves = {};

        for (const item of params) {
            if (!item.clave || typeof item.valor === 'undefined') {
                errores.push('Cada elemento de parametros_optimizador debe tener "clave" y "valor"');
                continue;
            }
            claves[item.clave] = item.valor;
        }

        for (const req of requeridas) {
            if (!(req in claves)) {
                errores.push(`parametros_optimizador: falta la clave "${req}" para el Algoritmo Genetico`);
            }
        }

        if (claves.tam_poblacion !== undefined) {
            if (!Number.isInteger(claves.tam_poblacion) || claves.tam_poblacion < 1) {
                errores.push('tam_poblacion debe ser un entero >= 1');
            }
        }
        if (claves.num_generaciones !== undefined) {
            if (!Number.isInteger(claves.num_generaciones) || claves.num_generaciones < 1) {
                errores.push('num_generaciones debe ser un entero >= 1');
            }
        }
        if (claves.prob_cruce !== undefined) {
            if (typeof claves.prob_cruce !== 'number' || claves.prob_cruce < 0 || claves.prob_cruce > 1) {
                errores.push('prob_cruce debe ser un numero entre 0 y 1');
            }
        }
        if (claves.prob_mutacion !== undefined) {
            if (typeof claves.prob_mutacion !== 'number' || claves.prob_mutacion < 0 || claves.prob_mutacion > 1) {
                errores.push('prob_mutacion debe ser un numero entre 0 y 1');
            }
        }
        if (claves.elitismo !== undefined && claves.tam_poblacion !== undefined) {
            if (!Number.isInteger(claves.elitismo) || claves.elitismo < 0 || claves.elitismo >= claves.tam_poblacion) {
                errores.push('elitismo debe ser un entero >= 0 y menor que tam_poblacion');
            }
        }
        if (claves.torneo_k !== undefined) {
            if (!Number.isInteger(claves.torneo_k) || claves.torneo_k < 1) {
                errores.push('torneo_k debe ser un entero >= 1');
            }
        }
    }

    // --- Enjambre de Particulas (PSO) ---
    if (algoritmo === 'PSO') {
        const requeridas = ['num_particulas', 'num_iteraciones', 'w', 'c1', 'c2'];
        const claves = {};

        for (const item of params) {
            if (!item.clave || typeof item.valor === 'undefined') {
                errores.push('Cada elemento de parametros_optimizador debe tener "clave" y "valor"');
                continue;
            }
            claves[item.clave] = item.valor;
        }

        for (const req of requeridas) {
            if (!(req in claves)) {
                errores.push(`parametros_optimizador: falta la clave "${req}" para PSO`);
            }
        }

        if (claves.num_particulas !== undefined) {
            if (!Number.isInteger(claves.num_particulas) || claves.num_particulas < 1) {
                errores.push('num_particulas debe ser un entero >= 1');
            }
        }
        if (claves.num_iteraciones !== undefined) {
            if (!Number.isInteger(claves.num_iteraciones) || claves.num_iteraciones < 0) {
                errores.push('num_iteraciones debe ser un entero >= 0');
            }
        }
        if (claves.w !== undefined) {
            if (typeof claves.w !== 'number' || claves.w < 0 || claves.w > 1) {
                errores.push('w debe ser un numero entre 0 y 1');
            }
        }
        if (claves.c1 !== undefined) {
            if (typeof claves.c1 !== 'number' || claves.c1 <= 0) {
                errores.push('c1 debe ser un numero mayor a 0');
            }
        }
        if (claves.c2 !== undefined) {
            if (typeof claves.c2 !== 'number' || claves.c2 <= 0) {
                errores.push('c2 debe ser un numero mayor a 0');
            }
        }
    }

    return { valido: errores.length === 0, errores };
}

/**
 * Valida las frecuencias segun el tipo de filtro y modo seleccionado.
 *
 * Cada combinacion tipo_filtro + modo tiene un esquema distinto de claves
 * requeridas y un orden numerico obligatorio entre ellas.
 *
 * Tambien verifica el margen minimo de una decade entre las frecuencias
 * de interes y los limites del barrido AC.
 */
function validarFrecuencias(frecuencias, tipoFiltro, modo, barrido) {
    const errores = [];

    if (!Array.isArray(frecuencias)) {
        return { valido: false, errores: ['frecuencias debe ser un arreglo de objetos {clave, valor}'] };
    }

    const claves = {};
    for (const item of frecuencias) {
        if (!item.clave || typeof item.valor === 'undefined') {
            errores.push('Cada elemento de frecuencias debe tener "clave" y "valor"');
            continue;
        }
        claves[item.clave] = item.valor;
    }

    // Claves requeridas por tipo de filtro y modo (ver README seccion 7)
    const claveFiltroModo = {
        'PASA_BAJA': { 'BASICO': ['fc_objetivo'], 'AVANZADO': ['f_paso', 'f_aten'] },
        'PASA_ALTA': { 'BASICO': ['fc_objetivo'], 'AVANZADO': ['f_aten', 'f_paso'] },
        'PASA_BANDA': { 'BASICO': ['fc_inferior', 'fc_superior'], 'AVANZADO': ['f_aten_1', 'f_paso_1', 'f_paso_2', 'f_aten_2'] },
        'RECHAZO_BANDA': { 'BASICO': ['fc_inferior', 'fc_superior'], 'AVANZADO': ['f_paso_1', 'f_aten_1', 'f_aten_2', 'f_paso_2'] }
    };

    const clavesRequeridas = claveFiltroModo[tipoFiltro]?.[modo] || [];
    for (const req of clavesRequeridas) {
        if (!(req in claves)) {
            errores.push(`frecuencias: falta la clave "${req}" para ${tipoFiltro} modo ${modo}`);
        }
    }

    // Verifica margen de una decade respecto al barrido AC
    const frecs = Object.values(claves).filter(v => typeof v === 'number');
    const fInicial = barrido?.f_inicial;
    const fFinal = barrido?.f_final;

    if (fInicial !== undefined && fFinal !== undefined && frecs.length > 0) {
        const masBaja = Math.min(...frecs);
        const masAlta = Math.max(...frecs);

        if (masBaja < fInicial * 10) {
            errores.push(`La frecuencia mas baja (${masBaja} Hz) debe ser al menos una decade por encima de f_inicial (${fInicial} Hz = ${fInicial * 10} Hz)`);
        }
        if (masAlta > fFinal / 10) {
            errores.push(`La frecuencia mas alta (${masAlta} Hz) debe ser al menos una decade por debajo de f_final (${fFinal} Hz = ${fFinal / 10} Hz)`);
        }
    }

    // Verifica el orden numerico entre frecuencias segun tipo+modo
    const orden = {
        'PASA_BAJA': { 'AVANZADO': (c) => c.f_paso < c.f_aten },
        'PASA_ALTA': { 'AVANZADO': (c) => c.f_aten < c.f_paso },
        'PASA_BANDA': {
            'BASICO': (c) => c.fc_inferior < c.fc_superior,
            'AVANZADO': (c) => c.f_aten_1 < c.f_paso_1 && c.f_paso_1 <= c.f_paso_2 && c.f_paso_2 < c.f_aten_2
        },
        'RECHAZO_BANDA': {
            'BASICO': (c) => c.fc_inferior < c.fc_superior,
            'AVANZADO': (c) => c.f_paso_1 < c.f_aten_1 && c.f_aten_1 <= c.f_aten_2 && c.f_aten_2 < c.f_paso_2
        }
    };

    const reglaOrden = orden[tipoFiltro]?.[modo];
    if (reglaOrden && Object.keys(claves).length >= clavesRequeridas.length) {
        if (!reglaOrden(claves)) {
            const ordenEsperado = {
                'PASA_BAJA+AVANZADO': 'f_paso < f_aten',
                'PASA_ALTA+AVANZADO': 'f_aten < f_paso',
                'PASA_BANDA+BASICO': 'fc_inferior < fc_superior',
                'PASA_BANDA+AVANZADO': 'f_aten_1 < f_paso_1 <= f_paso_2 < f_aten_2',
                'RECHAZO_BANDA+BASICO': 'fc_inferior < fc_superior',
                'RECHAZO_BANDA+AVANZADO': 'f_paso_1 < f_aten_1 <= f_aten_2 < f_paso_2'
            };
            const key = `${tipoFiltro}+${modo}`;
            errores.push(`Orden de frecuencias invalido: se esperaba ${ordenEsperado[key] || 'verificar documentacion'}`);
        }
    }

    return { valido: errores.length === 0, errores };
}

/**
 * Orquestador de validacion Nivel 1.
 * Ejecuta todas las sub-validaciones en orden y acumula errores.
 * Retorna { valido: boolean, errores: string[] }.
 */
function validarConfigCompleta(config, tipoFiltro, algoritmo) {
    const errores = [];

    if (!config || typeof config !== 'object') {
        return { valido: false, errores: ['El body debe ser un objeto JSON valido'] };
    }

    if (!tipoFiltro) {
        errores.push('tipo_filtro es requerido');
    } else if (!VALID_FILTER_TYPES.includes(tipoFiltro)) {
        errores.push(`tipo_filtro debe ser uno de: ${VALID_FILTER_TYPES.join(', ')}`);
    }

    if (!algoritmo) {
        errores.push('algoritmo es requerido');
    } else if (!VALID_ALGORITHMS.includes(algoritmo)) {
        errores.push(`algoritmo debe ser uno de: ${VALID_ALGORITHMS.join(', ')}`);
    }

    // Normaliza modo a mayusculas, rechaza valores no validos
    if (!config.modo) {
        errores.push('modo es requerido');
    } else {
        const modoNormalizado = config.modo.toString().trim().toUpperCase();
        if (modoNormalizado !== 'BASICO' && modoNormalizado !== 'AVANZADO') {
            errores.push('modo debe ser "BASICO" o "AVANZADO"');
        } else {
            config.modo = modoNormalizado;
        }
    }

    const rEntorno = validarEntorno(config.entorno);
    errores.push(...rEntorno.errores);

    const rBarrido = validarBarridoAc(config.barrido_ac);
    errores.push(...rBarrido.errores);

    const rParams = validarParametrosOptimizador(config.parametros_optimizador, algoritmo);
    errores.push(...rParams.errores);

    // Solo valida frecuencias si modo, tipo_filtro y barrido son validos
    if (config.modo && tipoFiltro && rBarrido.valido) {
        const rFreqs = validarFrecuencias(config.frecuencias, tipoFiltro, config.modo, config.barrido_ac);
        errores.push(...rFreqs.errores);
    }

    return { valido: errores.length === 0, errores };
}

module.exports = {
    validarConfigCompleta,
    esE12,
    esFrecuenciaRedonda,
    VALID_FILTER_TYPES,
    VALID_ALGORITHMS,
    VALID_MODES
};
