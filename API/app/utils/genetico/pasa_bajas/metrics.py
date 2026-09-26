"""
Utilería: cálculo de métricas sobre la curva de respuesta en frecuencia
leída del archivo de datos producido por ngspice, para el filtro PASA-BAJAS.

Adaptado del código fuente del equipo de algoritmos (ALGORITMO_GENETICO/
FILTRO_PASABAJAS/algoritmo.py). La lógica de calcular_f_plano y las
métricas son DELIBERADAMENTE distintas a las de pasa_altas (ver el
docstring de cada función): un pasa-bajas tiene la meseta de paso en baja
frecuencia y la de atenuación en alta frecuencia, justo al revés que un
pasa-altas, así que "hacia dónde mirar" para detectar resonancias/anchura
de meseta también se invierte.

No depende de ninguna otra capa ni de estado global; recibe todo lo que
necesita como argumentos (a diferencia del script original, que usaba
variables globales cargadas una sola vez al importar el módulo).
"""
import numpy as np
import traceback


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _db(x: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(x, 1e-12))


def calcular_f_plano(frecuencias: np.ndarray, amplitudes: np.ndarray) -> float:
    """
    Mide qué tan ancha es la meseta de la banda de ATENUACIÓN, mirando
    desde el mínimo global de la curva hacia frecuencias más altas.

    Un "hueco" angosto (el AG encuentra un mínimo profundo justo en
    F_ATEN/Fc, pero la curva vuelve a subir enseguida después, en vez de
    quedarse atenuada) obtiene un f_plano cercano a 0; una banda de
    atenuación ancha que se mantiene abajo tarda varias décadas en volver
    a subir y se acerca a 1. Si la curva nunca vuelve a subir por encima
    del 5% de la amplitud máxima dentro del barrido, se devuelve 1.0.

    Esto solo mira hacia ADELANTE desde el mínimo global, así que es ciego
    a una resonancia que ocurra ANTES de llegar a ese mínimo (mientras la
    curva todavía desciende desde la banda de paso). Para eso se mide la
    peor "subida" respecto al mínimo acumulado hasta el mínimo global
    (running min). f_plano final es el peor (mínimo) de ambas métricas.
    """
    idx_min = int(np.argmin(amplitudes))
    f_min = frecuencias[idx_min]
    amp_max = np.max(amplitudes)

    umbral_5 = 0.05 * amp_max
    idx_subida = next(
        (i for i in range(idx_min, len(amplitudes)) if amplitudes[i] > umbral_5),
        None,
    )

    if idx_subida is None:
        f_plano_post = 1.0
    else:
        ancho_decadas = np.log10(frecuencias[idx_subida] / f_min)
        f_plano_post = float(ancho_decadas / (ancho_decadas + 1.0))

    # -- Resonancia ANTES del mínimo global --
    if amp_max > 0 and idx_min > 0:
        bajada = amplitudes[: idx_min + 1]
        minimo_acumulado = np.minimum.accumulate(bajada)
        peor_subida = float(np.max(bajada - minimo_acumulado))
        f_plano_pre = 1.0 / (1.0 + (peor_subida / amp_max) * 10.0)
    else:
        f_plano_pre = 1.0

    return min(f_plano_post, f_plano_pre)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def calcular_metricas_fc(
    archivo_datos: str,
) -> tuple[float | None, float, float, float, float]:
    """
    MODO BASICO: interpola la Fc real (cruce por amp_dc/sqrt(2)) y mide la
    pendiente una década POR ENCIMA de Fc (en el pasa-bajas la atenuación
    cae hacia frecuencias altas, al revés que en el pasa-altas).

    Retorna: (fc_real, amp_dc, amp_max, pendiente_db_dec, f_plano)
    """
    try:
        datos = np.loadtxt(archivo_datos)
        frecuencias = datos[:, 0]
        amplitudes = datos[:, 1]

        amp_dc = float(amplitudes[0])
        amp_max = float(np.max(amplitudes))
        nivel_fc = amp_dc / np.sqrt(2)

        fc_real = None
        for i in range(len(amplitudes) - 1):
            a1, a2 = amplitudes[i], amplitudes[i + 1]
            if (a1 <= nivel_fc <= a2) or (a1 >= nivel_fc >= a2):
                f1, f2 = frecuencias[i], frecuencias[i + 1]
                fc_real = f1 + (nivel_fc - a1) * (f2 - f1) / (a2 - a1)
                break

        if fc_real is None:
            fc_real = float(frecuencias[np.argmin(np.abs(amplitudes - nivel_fc))])

        idx_fc = np.argmin(np.abs(frecuencias - fc_real))
        f_ref = fc_real * 10.0  # una década POR ENCIMA de Fc (lado de atenuación)
        idx_ref = np.argmin(np.abs(frecuencias - f_ref))
        pendiente = abs(_db(amplitudes[idx_fc]) - _db(amplitudes[idx_ref]))

        f_plano = calcular_f_plano(frecuencias, amplitudes)

        return float(fc_real), amp_dc, amp_max, float(pendiente), float(f_plano)
    except Exception:
        print("[AVISO] calcular_metricas_fc (pasa_bajas) falló; se usará (None, 0.0, 0.0, 0.0, 0.0):")
        traceback.print_exc()
        return None, 0.0, 0.0, 0.0, 0.0


def calcular_metricas_paso_aten(
    archivo_datos: str,
    f_paso: float,
    f_aten: float,
) -> tuple[float | None, float, float, float, float, float]:
    """
    MODO AVANZADO: evalúa la respuesta en F_PASO (banda de paso, baja
    frecuencia) y F_ATEN (banda de atenuación, alta frecuencia),
    interpolando en escala logarítmica, y calcula la pendiente entre
    ambos puntos.

    Retorna: (amp_dc, amp_max, amp_paso, amp_aten, pendiente_db_dec, f_plano)
    """
    try:
        datos = np.loadtxt(archivo_datos)
        frecuencias = datos[:, 0]
        amplitudes = datos[:, 1]

        amp_dc = float(amplitudes[0])
        amp_max = float(np.max(amplitudes))
        log_f = np.log10(frecuencias)
        amp_paso = float(np.interp(np.log10(f_paso), log_f, amplitudes))
        amp_aten = float(np.interp(np.log10(f_aten), log_f, amplitudes))

        # abs() en ambos lados: así la fórmula da la magnitud de la
        # pendiente sin importar si F_PASO/F_ATEN quedan invertidas en el
        # JSON (en el pasa-bajas lo normal es F_PASO < F_ATEN).
        pendiente = abs(_db(np.array([amp_paso])) - _db(np.array([amp_aten]))) / abs(
            np.log10(f_aten / f_paso)
        )

        f_plano = calcular_f_plano(frecuencias, amplitudes)

        return amp_dc, amp_max, amp_paso, amp_aten, float(pendiente[0]), float(f_plano)
    except Exception:
        print("[AVISO] calcular_metricas_paso_aten (pasa_bajas) falló; se usará (None, 0.0, 0.0, 0.0, 0.0, 0.0):")
        traceback.print_exc()
        return None, 0.0, 0.0, 0.0, 0.0, 0.0