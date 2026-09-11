"""
Utilería: cálculo de métricas sobre la curva de respuesta en frecuencia
leída del archivo de datos producido por ngspice.

No depende de ninguna otra capa ni de estado global; recibe todo lo que
necesita como argumentos.
"""
import numpy as np


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _db(x: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(x, 1e-12))


def calcular_f_plano(frecuencias: np.ndarray, amplitudes: np.ndarray) -> float:
    """
    Mide qué tan ancha es la meseta de la banda de paso.

    Devuelve un valor entre 0 (pico angosto / resonancia) y 1 (meseta ideal).
    Evalúa dos riesgos:
        - post-pico:  cuántas décadas tarda la curva en caer al 95 % del pico.
        - pre-pico:   peor caída relativa al máximo acumulado durante la subida
                      (detecta rizados antes de llegar al pico global).
    El resultado final es el mínimo de ambas métricas.
    """
    idx_max = int(np.argmax(amplitudes))
    amp_max = amplitudes[idx_max]
    f_max = frecuencias[idx_max]

    # -- Métrica post-pico --
    umbral_95 = 0.95 * amp_max
    idx_caida = next(
        (i for i in range(idx_max, len(amplitudes)) if amplitudes[i] < umbral_95),
        None,
    )

    if idx_caida is None:
        f_plano_post = 1.0
    else:
        ancho_decadas = np.log10(frecuencias[idx_caida] / f_max)
        f_plano_post = float(ancho_decadas / (ancho_decadas + 1.0))

    # -- Métrica pre-pico (resonancias antes del pico global) --
    if amp_max > 0 and idx_max > 0:
        subida = amplitudes[: idx_max + 1]
        maximo_acumulado = np.maximum.accumulate(subida)
        peor_caida = float(np.max(maximo_acumulado - subida))
        f_plano_pre = 1.0 / (1.0 + (peor_caida / amp_max) * 10.0)
    else:
        f_plano_pre = 1.0

    return min(f_plano_post, f_plano_pre)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def calcular_metricas_fc(
    archivo_datos: str,
) -> tuple[float | None, float, float, float]:
    """
    MODO BASICO: interpola la Fc real (-3 dB), mide la pendiente una década
    por debajo de Fc y calcula f_plano.

    Retorna: (fc_real, amp_max, pendiente_db_dec, f_plano)
    """
    try:
        datos = np.loadtxt(archivo_datos)
        frecuencias = datos[:, 0]
        amplitudes = datos[:, 1]

        amp_max = float(np.max(amplitudes))
        nivel_fc = amp_max / np.sqrt(2)

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
        f_ref = fc_real / 10.0
        idx_ref = np.argmin(np.abs(frecuencias - f_ref))
        pendiente = abs(_db(amplitudes[idx_fc]) - _db(amplitudes[idx_ref]))

        f_plano = calcular_f_plano(frecuencias, amplitudes)

        return float(fc_real), float(amp_max), float(pendiente), float(f_plano)
    except Exception:
        return None, 0.0, 0.0, 0.0


def calcular_metricas_paso_aten(
    archivo_datos: str,
    f_paso: float,
    f_aten: float,
) -> tuple[float | None, float, float, float, float]:
    """
    MODO AVANZADO: evalúa la respuesta en F_PASO y F_ATEN interpolando en
    escala logarítmica y calcula la pendiente entre ambos puntos.

    Retorna: (amp_max, amp_paso, amp_aten, pendiente_db_dec, f_plano)
    """
    try:
        datos = np.loadtxt(archivo_datos)
        frecuencias = datos[:, 0]
        amplitudes = datos[:, 1]

        amp_max = float(np.max(amplitudes))
        log_f = np.log10(frecuencias)
        amp_paso = float(np.interp(np.log10(f_paso), log_f, amplitudes))
        amp_aten = float(np.interp(np.log10(f_aten), log_f, amplitudes))

        pendiente = abs(_db(np.array([amp_paso])) - _db(np.array([amp_aten]))) / abs(
            np.log10(f_aten / f_paso)
        )

        f_plano = calcular_f_plano(frecuencias, amplitudes)

        return amp_max, amp_paso, amp_aten, float(pendiente[0]), float(f_plano)
    except Exception:
        return None, 0.0, 0.0, 0.0, 0.0