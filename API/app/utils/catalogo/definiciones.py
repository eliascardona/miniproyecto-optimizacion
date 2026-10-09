"""
Definiciones DECLARATIVAS del catálogo filtro × algoritmo (solo datos; la lógica está en construir.py).

De dónde sale cada dato:
  · Claves, tipos, reglas duras y rangos ideales de AG y PSO, y claves/orden de las frecuencias por filtro y
    modo: ALGORITMOS_DE_OPTIMIZACION/README.md (el contrato de entrada del equipo de algoritmos).
  · Valores iniciales de los hiperparámetros: los config.json de ejemplo de cada algoritmo × filtro (los 16).
  · BO y RS no están en ese README. Sus mínimos duros salen de lo que el código necesita para no fallar ni
    ciclar (se explica junto a cada uno); no hay "rango ideal" porque no está documentado.

Qué significa cada límite de un campo:
  · minimo / maximo (con *_exclusivo)  -> regla DURA: fuera de ahí la corrida falla o no tiene sentido. El
                                           cliente debe bloquear el envío.
  · ideal_min / ideal_max              -> rango RECOMENDADO: fuera de ahí se puede enviar, pero el cliente
                                           debería avisar.
  · serie                              -> serie comercial que se pide (hoy solo "E12"); es un aviso.

Las "relaciones" comparan dos campos entre sí (orden de frecuencias, elitismo < población, ...). Cada una
trae su severidad: "error" bloquea y "aviso" solo advierte.

Hay un cuarto dato que depende de varios campos a la vez, y por eso vive en `reglas`: el margen de una década
entre las frecuencias de interés y el barrido (sección 5.2 del README). Es "aviso" porque los propios
config.json de ejemplo del equipo no siempre lo cumplen (p. ej. PSO pasa-altas: 4500 Hz con barrido hasta
30 kHz) y el backend nunca lo ha exigido. Para volverlo bloqueante basta cambiar su severidad aquí.
"""
from typing import Optional

VERSION_CATALOGO = 1

# --------------------------------------------------------------------------------------------------
# Constructores de campos (todos los campos llevan SIEMPRE las mismas claves: el cliente no adivina)
# --------------------------------------------------------------------------------------------------


def _campo(
    clave: str,
    etiqueta: str,
    tipo: str,
    *,
    unidad: Optional[str] = None,
    minimo: Optional[float] = None,
    minimo_exclusivo: bool = False,
    maximo: Optional[float] = None,
    maximo_exclusivo: bool = False,
    ideal_min: Optional[float] = None,
    ideal_max: Optional[float] = None,
    serie: Optional[str] = None,
    paso: float = 1,
    descripcion: str = "",
) -> dict:
    assert tipo in ("entero", "decimal"), tipo
    return {
        "clave": clave,
        "etiqueta": etiqueta,
        "tipo": tipo,
        "unidad": unidad,
        "minimo": minimo,
        "minimo_exclusivo": minimo_exclusivo,
        "maximo": maximo,
        "maximo_exclusivo": maximo_exclusivo,
        "ideal_min": ideal_min,
        "ideal_max": ideal_max,
        "serie": serie,
        "paso": paso,
        "descripcion": descripcion,
    }


def _relacion(izquierda: str, operador: str, derecha: str, mensaje: str, severidad: str = "error") -> dict:
    assert operador in ("<", "<="), operador
    assert severidad in ("error", "aviso"), severidad
    return {
        "izquierda": izquierda,
        "operador": operador,
        "derecha": derecha,
        "severidad": severidad,
        "mensaje": mensaje,
    }


# --------------------------------------------------------------------------------------------------
# Lo que NO depende ni del filtro ni del algoritmo: modo, entorno y barrido
# --------------------------------------------------------------------------------------------------

MODOS = [
    {
        "id": "BASICO",
        "etiqueta": "Básico (frecuencia de corte)",
        "descripcion": "Busca que la frecuencia de corte real del filtro caiga en la(s) frecuencia(s) objetivo, "
                       "con la pendiente y la amplitud adecuadas.",
    },
    {
        "id": "AVANZADO",
        "etiqueta": "Avanzado (banda de paso y de atenuación)",
        "descripcion": "Busca amplitud máxima en la banda de paso y mínima en la de atenuación, "
                       "en las frecuencias indicadas.",
    },
]

ENTORNO = [
    _campo("v_fuente", "Tensión de la fuente", "decimal", unidad="V", minimo=0, minimo_exclusivo=True,
           ideal_max=10, paso=0.1,
           descripcion="Amplitud de la fuente AC. Debe ser > 0. El op-amp se alimenta con ±(v_fuente + 10 V): "
                       "por encima de 10 V se sale del rango recomendado del LM741 (±5 a ±15 V)."),
    _campo("r_fuente", "Resistencia de la fuente", "entero", unidad="Ω", minimo=1, ideal_min=10, ideal_max=820000,
           serie="E12", paso=1,
           descripcion="Debe ser > 0 y, por consistencia con las resistencias que se optimizan, de la serie E12 "
                       "entre 10 Ω y 820 kΩ."),
    _campo("r_carga", "Resistencia de carga", "entero", unidad="Ω", minimo=1, ideal_min=10, ideal_max=820000,
           serie="E12", paso=1,
           descripcion="Igual que la resistencia de la fuente."),
]

BARRIDO_AC = [
    _campo("f_inicial", "Frecuencia inicial del barrido", "entero", unidad="Hz", minimo=1, paso=1,
           descripcion="Debe ser > 0 y menor que la frecuencia final."),
    _campo("f_final", "Frecuencia final del barrido", "entero", unidad="Hz", minimo=1, maximo=10_000_000, paso=1,
           descripcion="Tope del contrato de la API: 10 MHz."),
]

RELACIONES_BARRIDO = [
    _relacion("f_inicial", "<", "f_final", "La frecuencia inicial debe ser menor que la final."),
]

REGLAS = {
    "margen_decada": {
        "factor": 10,
        "severidad": "aviso",
        "descripcion": "La frecuencia de interés más baja debe quedar al menos una década por encima de "
                       "f_inicial y la más alta al menos una década por debajo de f_final; si no, el punto de "
                       "referencia de la pendiente cae fuera del barrido y la métrica deja de ser fiable.",
    },
}

# --------------------------------------------------------------------------------------------------
# Filtros: lo que depende del TIPO DE FILTRO y del MODO (las frecuencias objetivo)
# --------------------------------------------------------------------------------------------------


def _frec(clave: str, etiqueta: str, descripcion: str = "") -> dict:
    return _campo(clave, etiqueta, "decimal", unidad="Hz", minimo=0, minimo_exclusivo=True, paso=10,
                  descripcion=descripcion)


# Para cada (filtro, modo): campos en orden ASCENDENTE de frecuencia, relaciones de orden, y cuáles son la
# frecuencia más baja y la más alta (a ellas se aplica el margen de una década). `valores` = valor inicial; se
# eligieron para cumplir el margen con el barrido por defecto de la app (1 Hz a 100 kHz).
FRECUENCIAS = {
    "pasa_altas": {
        "BASICO": {
            "campos": [_frec("fc_objetivo", "Frecuencia de corte objetivo")],
            "relaciones": [],
            "extremos": ("fc_objetivo", "fc_objetivo"),
            "valores": {"fc_objetivo": 2000},
        },
        "AVANZADO": {
            "campos": [
                _frec("f_aten", "Frecuencia de atenuación", "Donde se espera amplitud ≈ 0 (baja frecuencia)."),
                _frec("f_paso", "Frecuencia de paso", "Donde se espera la amplitud máxima (alta frecuencia)."),
            ],
            "relaciones": [
                _relacion("f_aten", "<", "f_paso",
                          "En un pasa altas la frecuencia de atenuación debe ser menor que la de paso."),
            ],
            "extremos": ("f_aten", "f_paso"),
            "valores": {"f_aten": 1000, "f_paso": 10000},
        },
    },
    "pasa_bajas": {
        "BASICO": {
            "campos": [_frec("fc_objetivo", "Frecuencia de corte objetivo")],
            "relaciones": [],
            "extremos": ("fc_objetivo", "fc_objetivo"),
            "valores": {"fc_objetivo": 5000},
        },
        "AVANZADO": {
            "campos": [
                _frec("f_paso", "Frecuencia de paso", "Donde se espera la amplitud máxima (baja frecuencia)."),
                _frec("f_aten", "Frecuencia de atenuación", "Donde se espera amplitud ≈ 0 (alta frecuencia)."),
            ],
            "relaciones": [
                _relacion("f_paso", "<", "f_aten",
                          "En un pasa bajas la frecuencia de paso debe ser menor que la de atenuación."),
            ],
            "extremos": ("f_paso", "f_aten"),
            "valores": {"f_paso": 500, "f_aten": 10000},
        },
    },
    "pasa_banda": {
        "BASICO": {
            "campos": [
                _frec("fc_inferior", "Frecuencia de corte inferior"),
                _frec("fc_superior", "Frecuencia de corte superior"),
            ],
            "relaciones": [
                _relacion("fc_inferior", "<", "fc_superior",
                          "La frecuencia de corte inferior debe ser menor que la superior."),
            ],
            "extremos": ("fc_inferior", "fc_superior"),
            "valores": {"fc_inferior": 1000, "fc_superior": 8000},
        },
        "AVANZADO": {
            "campos": [
                _frec("f_aten_1", "Atenuación inferior", "Debajo de la banda de paso: amplitud ≈ 0."),
                _frec("f_paso_1", "Inicio de la banda de paso"),
                _frec("f_paso_2", "Fin de la banda de paso",
                      "Puede ser igual al inicio si la banda se reduce a un punto."),
                _frec("f_aten_2", "Atenuación superior", "Encima de la banda de paso: amplitud ≈ 0."),
            ],
            "relaciones": [
                _relacion("f_aten_1", "<", "f_paso_1", "Debe cumplirse atenuación inferior < inicio de paso."),
                _relacion("f_paso_1", "<=", "f_paso_2", "El inicio de la banda de paso no puede pasar de su fin."),
                _relacion("f_paso_2", "<", "f_aten_2", "Debe cumplirse fin de paso < atenuación superior."),
            ],
            "extremos": ("f_aten_1", "f_aten_2"),
            "valores": {"f_aten_1": 10, "f_paso_1": 100, "f_paso_2": 1000, "f_aten_2": 10000},
        },
    },
    "rechaza_banda": {
        "BASICO": {
            "campos": [
                _frec("fc_inferior", "Frecuencia de corte inferior"),
                _frec("fc_superior", "Frecuencia de corte superior"),
            ],
            "relaciones": [
                _relacion("fc_inferior", "<", "fc_superior",
                          "La frecuencia de corte inferior debe ser menor que la superior."),
            ],
            "extremos": ("fc_inferior", "fc_superior"),
            "valores": {"fc_inferior": 200, "fc_superior": 800},
        },
        "AVANZADO": {
            "campos": [
                _frec("f_paso_1", "Paso inferior", "Debajo de la banda rechazada: amplitud máxima."),
                _frec("f_aten_1", "Inicio de la banda de rechazo"),
                _frec("f_aten_2", "Fin de la banda de rechazo",
                      "Puede ser igual al inicio si el rechazo se reduce a una muesca puntual."),
                _frec("f_paso_2", "Paso superior", "Encima de la banda rechazada: amplitud máxima."),
            ],
            "relaciones": [
                _relacion("f_paso_1", "<", "f_aten_1", "Debe cumplirse paso inferior < inicio de rechazo."),
                _relacion("f_aten_1", "<=", "f_aten_2", "El inicio de la banda de rechazo no puede pasar de su fin."),
                _relacion("f_aten_2", "<", "f_paso_2", "Debe cumplirse fin de rechazo < paso superior."),
            ],
            "extremos": ("f_paso_1", "f_paso_2"),
            "valores": {"f_paso_1": 10, "f_aten_1": 100, "f_aten_2": 500, "f_paso_2": 10000},
        },
    },
}

FILTROS = [
    {"id": "pasa_altas", "etiqueta": "Pasa altas", "familia": "corte_simple",
     "descripcion": "Sallen-Key de 4.º orden"},
    {"id": "pasa_bajas", "etiqueta": "Pasa bajas", "familia": "corte_simple",
     "descripcion": "Sallen-Key de 4.º orden"},
    {"id": "pasa_banda", "etiqueta": "Pasa banda", "familia": "banda",
     "descripcion": "4.º orden (pasa altas + pasa bajas)"},
    {"id": "rechaza_banda", "etiqueta": "Rechaza banda", "familia": "banda",
     "descripcion": "Twin-T aislado (2 buffers)"},
]

# --------------------------------------------------------------------------------------------------
# Algoritmos: lo que depende del ALGORITMO (los hiperparámetros)
# --------------------------------------------------------------------------------------------------

ALGORITMOS = [
    {
        "id": "algoritmo_genetico",
        "etiqueta": "Algoritmo genético",
        "descripcion": "Población de circuitos que se cruzan y mutan; cada gen es el índice de un valor comercial.",
        "parametros": [
            _campo("tam_poblacion", "Tamaño de la población", "entero", minimo=1, ideal_min=20, ideal_max=50,
                   descripcion="Individuos por generación; cada uno cuesta una simulación completa."),
            _campo("num_generaciones", "Generaciones", "entero", minimo=1, ideal_min=30, ideal_max=50,
                   descripcion="Pasado cierto punto la población converge y más generaciones solo añaden tiempo."),
            _campo("prob_cruce", "Probabilidad de cruce", "decimal", minimo=0, maximo=1, ideal_min=0.7,
                   ideal_max=0.9, paso=0.05),
            _campo("prob_mutacion", "Probabilidad de mutación", "decimal", minimo=0, maximo=1, ideal_min=0.2,
                   ideal_max=0.35, paso=0.01,
                   descripcion="Más alta que en los libros porque el cromosoma tiene pocos genes (6 a 8)."),
            _campo("elitismo", "Elitismo", "entero", minimo=0, ideal_min=2, ideal_max=4,
                   descripcion="Mejores individuos que pasan intactos a la siguiente generación."),
            _campo("torneo_k", "Tamaño del torneo", "entero", minimo=1, ideal_min=2, ideal_max=5,
                   descripcion="Candidatos que compiten para ser padre; más alto = más presión selectiva."),
        ],
        "relaciones": [
            _relacion("elitismo", "<", "tam_poblacion",
                      "El elitismo debe ser menor que el tamaño de la población; si no, la población deja de "
                      "evolucionar."),
        ],
    },
    {
        "id": "enjambre_particulas",
        "etiqueta": "Enjambre de partículas",
        "descripcion": "Partículas que se desplazan por el espacio de índices guiadas por su mejor posición y "
                       "la del enjambre.",
        "parametros": [
            _campo("num_particulas", "Número de partículas", "entero", minimo=1, ideal_min=20, ideal_max=40),
            _campo("num_iteraciones", "Iteraciones", "entero", minimo=0, ideal_min=30, ideal_max=50,
                   descripcion="Con 0 solo se evalúa el enjambre inicial aleatorio."),
            _campo("w", "Inercia (w)", "decimal", minimo=0, ideal_min=0.4, ideal_max=0.9, paso=0.05,
                   descripcion="Por encima de 1 la velocidad puede crecer sin control."),
            _campo("c1", "Coeficiente cognitivo (c1)", "decimal", minimo=0, ideal_min=1.0, ideal_max=2.0, paso=0.1,
                   descripcion="Atracción hacia la mejor posición propia."),
            _campo("c2", "Coeficiente social (c2)", "decimal", minimo=0, ideal_min=1.0, ideal_max=2.0, paso=0.1,
                   descripcion="Atracción hacia la mejor posición del enjambre."),
        ],
        "relaciones": [],
    },
    {
        "id": "optimizacion_bayesiana",
        "etiqueta": "Optimización bayesiana",
        "descripcion": "Proceso gaussiano (Matérn) con mejora esperada: pocas simulaciones, más cómputo por "
                       "iteración.",
        "parametros": [
            # Con 1 solo punto el GP normaliza con desviación 0 y la mejora esperada se degenera: mínimo 2.
            _campo("n_iniciales", "Puntos iniciales", "entero", minimo=2,
                   descripcion="Muestras aleatorias con las que se ajusta el primer modelo."),
            _campo("n_iteraciones", "Iteraciones", "entero", minimo=0),
            _campo("xi", "Exploración (xi)", "decimal", minimo=0, paso=0.01,
                   descripcion="Margen exigido a la mejora esperada; más alto = más exploración."),
            _campo("n_candidatos", "Candidatos por iteración", "entero", minimo=1, paso=100),
            # Con 0 no queda ningún candidato que refinar y el código falla con IndexError.
            _campo("n_restarts", "Reinicios de L-BFGS-B", "entero", minimo=1,
                   descripcion="Cuántos de los mejores candidatos se refinan localmente."),
            # sklearn exige random_state en [0, 2^32 - 1].
            _campo("semilla", "Semilla aleatoria", "entero", minimo=0, maximo=4294967295,
                   descripcion="Fija el azar para que dos corridas iguales den el mismo resultado."),
        ],
        "relaciones": [],
    },
    {
        "id": "recocido_simulado",
        "etiqueta": "Recocido simulado",
        "descripcion": "Una sola solución que se perturba aceptando empeoramientos con probabilidad decreciente "
                       "según la temperatura.",
        "parametros": [
            _campo("temp_inicial", "Temperatura inicial", "decimal", minimo=0, minimo_exclusivo=True, paso=1),
            # El ciclo es `while temperatura > temp_final: ...; temperatura *= factor`: con temp_final <= 0 la
            # temperatura nunca baja de ese valor y el servidor se queda ciclando.
            _campo("temp_final", "Temperatura final", "decimal", minimo=0, minimo_exclusivo=True, paso=0.001,
                   descripcion="Debe ser > 0, o el enfriamiento no termina nunca."),
            # Con factor >= 1 la temperatura no baja y el ciclo anterior tampoco termina.
            _campo("factor_enfriamiento", "Factor de enfriamiento", "decimal", minimo=0, minimo_exclusivo=True,
                   maximo=1, maximo_exclusivo=True, paso=0.01,
                   descripcion="Entre 0 y 1 (sin incluir). Con 1 o más la temperatura no baja y la corrida "
                               "no termina."),
            _campo("iteraciones_por_temp", "Iteraciones por temperatura", "entero", minimo=1),
        ],
        "relaciones": [
            _relacion("temp_final", "<", "temp_inicial",
                      "La temperatura final debe ser menor que la inicial; si no, no hay enfriamiento."),
        ],
    },
]

# Valores iniciales de los hiperparámetros por (filtro, algoritmo): los config.json de ejemplo del equipo.
VALORES_INICIALES = {
    ("pasa_altas", "algoritmo_genetico"): {"tam_poblacion": 30, "num_generaciones": 30, "prob_cruce": 0.8,
                                           "prob_mutacion": 0.3, "elitismo": 3, "torneo_k": 3},
    ("pasa_bajas", "algoritmo_genetico"): {"tam_poblacion": 30, "num_generaciones": 30, "prob_cruce": 0.7,
                                           "prob_mutacion": 0.25, "elitismo": 2, "torneo_k": 4},
    ("pasa_banda", "algoritmo_genetico"): {"tam_poblacion": 35, "num_generaciones": 30, "prob_cruce": 0.8,
                                           "prob_mutacion": 0.3, "elitismo": 3, "torneo_k": 3},
    ("rechaza_banda", "algoritmo_genetico"): {"tam_poblacion": 35, "num_generaciones": 35, "prob_cruce": 0.8,
                                              "prob_mutacion": 0.25, "elitismo": 3, "torneo_k": 3},

    ("pasa_altas", "enjambre_particulas"): {"num_particulas": 30, "num_iteraciones": 30, "w": 0.6, "c1": 1.5,
                                            "c2": 1.5},
    ("pasa_bajas", "enjambre_particulas"): {"num_particulas": 40, "num_iteraciones": 30, "w": 0.5, "c1": 2,
                                            "c2": 2},
    ("pasa_banda", "enjambre_particulas"): {"num_particulas": 35, "num_iteraciones": 30, "w": 0.8, "c1": 2,
                                            "c2": 1},
    ("rechaza_banda", "enjambre_particulas"): {"num_particulas": 35, "num_iteraciones": 35, "w": 0.6, "c1": 1,
                                               "c2": 2},

    ("pasa_altas", "optimizacion_bayesiana"): {"n_iniciales": 10, "n_iteraciones": 30, "xi": 0.01,
                                               "n_candidatos": 3000, "n_restarts": 5, "semilla": 42},
    ("pasa_bajas", "optimizacion_bayesiana"): {"n_iniciales": 10, "n_iteraciones": 30, "xi": 0.01,
                                               "n_candidatos": 3000, "n_restarts": 5, "semilla": 42},
    ("pasa_banda", "optimizacion_bayesiana"): {"n_iniciales": 10, "n_iteraciones": 30, "xi": 0.01,
                                               "n_candidatos": 3000, "n_restarts": 5, "semilla": 42},
    ("rechaza_banda", "optimizacion_bayesiana"): {"n_iniciales": 10, "n_iteraciones": 30, "xi": 0.01,
                                                  "n_candidatos": 3000, "n_restarts": 5, "semilla": 42},

    ("pasa_altas", "recocido_simulado"): {"temp_inicial": 5.0, "temp_final": 0.001, "factor_enfriamiento": 0.9,
                                          "iteraciones_por_temp": 20},
    ("pasa_bajas", "recocido_simulado"): {"temp_inicial": 100.0, "temp_final": 0.01, "factor_enfriamiento": 0.794,
                                          "iteraciones_por_temp": 30},
    ("pasa_banda", "recocido_simulado"): {"temp_inicial": 100.0, "temp_final": 0.01, "factor_enfriamiento": 0.794,
                                          "iteraciones_por_temp": 30},
    ("rechaza_banda", "recocido_simulado"): {"temp_inicial": 100.0, "temp_final": 0.01,
                                             "factor_enfriamiento": 0.794, "iteraciones_por_temp": 30},
}