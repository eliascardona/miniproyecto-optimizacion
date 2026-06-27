import random
import subprocess
import sys
import base64
import numpy as np
import re
import json
from pathlib import Path

# ============================================================
# RUTAS DE EJECUCIÓN
# ============================================================
NGSPICE_EXE = r"C:\Users\luis_\Desktop\Spice64\bin\ngspice.exe"
ARCHIVO_CIR = "filtro.cir"
ARCHIVO_DATOS = "datos_filtro.txt"
ARCHIVO_CONFIG_JSON = "config.json"

# Gráfica de la respuesta final del filtro optimizado
GRAFICA_ARCHIVO = "resultado_filtro.png"   # ruta donde se guarda la imagen

# JSON con el resumen del resultado de la optimización
ARCHIVO_RESULTADO_JSON = "resultado.json"

# ============================================================
# CARGA DE CONFIGURACIÓN DESDE JSON
# ============================================================
def _buscar_etiqueta(lista, etiqueta):
    for item in lista:
        if item.get("clave") == etiqueta:
            return item.get("valor")

def cargar_configuracion(ruta):
    try:
        cfg_raw = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"[ERROR] No se encontró el archivo de configuración: {ruta}")
    except json.JSONDecodeError as e:
        sys.exit(f"[ERROR] El archivo de configuración '{ruta}' no es un JSON válido: {e}")

    modo = str(cfg_raw.get("modo", "")).strip().upper()

    entorno = cfg_raw["entorno"]
    v_fuente = float(entorno["v_fuente"])
    r_fuente = float(entorno["r_fuente"])
    r_carga = float(entorno["r_carga"])

    parametros = cfg_raw.get("parametros_optimizador", [])
    frecuencias = cfg_raw.get("frecuencias", [])
    barrido = cfg_raw.get("barrido_ac", {})

    cfg = {
        "modo": modo,

        # --- entorno (fijo durante la simulación, NO se optimiza) ---
        "v_fuente": v_fuente,
        "r_fuente": r_fuente,
        "r_carga": r_carga,
        # Vpp/Vnn de alimentación del Op-Amp: se derivan automáticamente
        # con 10V de margen sobre la señal de entrada.
        "vpp": v_fuente + 10.0,
        "vnn": -(v_fuente + 10.0),

        # --- rango del barrido .AC del .cir ---
        "f_inicial": float(barrido["f_inicial"]),
        "f_final": float(barrido["f_final"]),

        # --- parámetros del algoritmo genético ---
        "tam_poblacion": int(_buscar_etiqueta(parametros, "tam_poblacion")),
        "num_generaciones": int(_buscar_etiqueta(parametros, "num_generaciones")),
        "prob_cruce": float(_buscar_etiqueta(parametros, "prob_cruce")),
        "prob_mutacion": float(_buscar_etiqueta(parametros, "prob_mutacion")),
        "elitismo": int(_buscar_etiqueta(parametros, "elitismo")),
        "torneo_k": int(_buscar_etiqueta(parametros, "torneo_k")),
    }

    if modo == "BASICO":
        # Dos Fc objetivo: la del borde que sube (inferior) y la del
        # borde que baja (superior).
        cfg["fc_inferior"] = float(_buscar_etiqueta(frecuencias, "fc_inferior"))
        cfg["fc_superior"] = float(_buscar_etiqueta(frecuencias, "fc_superior"))
    else:  # AVANZADO
        # 4 frecuencias: atenuación inferior, paso inicio, paso fin,
        # atenuación superior (en ese orden, de menor a mayor frecuencia).
        cfg["f_aten_1"] = float(_buscar_etiqueta(frecuencias, "f_aten_1"))
        cfg["f_paso_1"] = float(_buscar_etiqueta(frecuencias, "f_paso_1"))
        cfg["f_paso_2"] = float(_buscar_etiqueta(frecuencias, "f_paso_2"))
        cfg["f_aten_2"] = float(_buscar_etiqueta(frecuencias, "f_aten_2"))

    return cfg

# Ruta del JSON de configuración
CFG = cargar_configuracion(ARCHIVO_CONFIG_JSON)

# --- Variables de configuración ---
MODO = CFG["modo"]                       # "BASICO" o "AVANZADO"

VS_VALOR = CFG["v_fuente"]
VPP_VALOR = CFG["vpp"]
VNN_VALOR = CFG["vnn"]
RS_VALOR = CFG["r_fuente"]
RL_VALOR = CFG["r_carga"]

F_INICIAL = CFG["f_inicial"]
F_FINAL = CFG["f_final"]

TAM_POBLACION = CFG["tam_poblacion"]
NUM_GENERACIONES = CFG["num_generaciones"]
PROB_CRUCE = CFG["prob_cruce"]
PROB_MUTACION = CFG["prob_mutacion"]
ELITISMO = CFG["elitismo"]
TORNEO_K = CFG["torneo_k"]

# ============================================================
# CONSTANTES DE DISEÑO FIJAS EN EL CÓDIGO (no vienen del JSON)
# ============================================================
# Pendiente teórica máxima POR BORDE en un pasabanda hecho de una etapa
# pasaaltas + una etapa pasabajas (cada una de 2do orden): 40 dB/dec.
# A diferencia del pasabajas/pasaaltas puros (donde las dos etapas
# cascadean sobre el MISMO borde y daban 80 dB/dec), aquí cada etapa
# gobierna un borde distinto. Se usa como objetivo en ambos modos y no
# depende de la configuración del usuario.
PENDIENTE_OBJETIVO_FC = 40.0
PENDIENTE_OBJETIVO_PASO_ATEN = 40.0

# Objetivos específicos de cada modo (frecuencias, sí vienen del JSON).
FC_INFERIOR_OBJETIVO = CFG.get("fc_inferior")
FC_SUPERIOR_OBJETIVO = CFG.get("fc_superior")
F_ATEN_1 = CFG.get("f_aten_1")
F_PASO_1 = CFG.get("f_paso_1")
F_PASO_2 = CFG.get("f_paso_2")
F_ATEN_2 = CFG.get("f_aten_2")

# Amplitudes ideales: en banda de paso se busca que pase toda la señal
# de entrada (= v_fuente) y en banda de atenuación que la señal quede
# completamente eliminada (= 0V). Se derivan de v_fuente, por lo que no
# es necesario indicarlas en el JSON.
AMP_PASO_OBJETIVO = VS_VALOR
AMP_ATEN_OBJETIVO = 0.0

# Compuerta dura para el borde SUPERIOR de la banda (lo gobierna la
# etapa pasabajas, en ambos modos): castiga el fitness COMPLETO si la
# curva sube de nuevo más de este margen DESPUÉS de haber tocado un
# mínimo, ya pasado F_ATEN_2 (MODO AVANZADO) o fc_superior (MODO BASICO).
# No se aplica al borde inferior en ningún modo: lo gobierna la etapa
# pasaaltas, que no tiene mecanismo físico de rebote (ver
# obtener_metricas_paso_aten / obtener_metricas_fc).
REBOTE_TOLERADO_REL = 0.03     # margen tolerado, como fracción de VS (3%)
PENALIZACION_ATEN_FALLO = 0.1  # multiplicador aplicado al fitness si rebota

# ============================================================
# SERIES COMERCIALES (E6 Capacitores, E12 Resistencias)
# ============================================================
def generar_serie(base, decadas):
    serie = []
    for d in decadas:
        for b in base:
            # round() evita el ruido de floating point (ej. 1.5000000000000002e-09
            # en vez de 1.5e-09) cuando estos valores se serializan en el JSON.
            serie.append(round(b * (10 ** d), 12))
    return sorted(serie)

SERIE_E6 = generar_serie([1.0, 1.5, 2.2, 3.3, 4.7, 6.8], range(-9, -5))
SERIE_E12 = generar_serie([1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2], range(1, 6))

# ============================================================
# PARSER DINÁMICO
# ============================================================
def extraer_componentes():
    texto = Path(ARCHIVO_CIR).read_text()
    detectados = []
    # Lista de componentes excluidos de la optimización
    fijos = ["RS", "RL", "VS", "VPP", "VNN"]
    patron = r"^([CR][a-zA-Z0-9_]*)\s+"

    for linea in texto.splitlines():
        linea = linea.strip()
        m = re.match(patron, linea)
        if m:
            nombre = m.group(1)
            if nombre.upper() not in fijos:
                partes = linea.split()
                tipo = "R" if nombre.upper().startswith("R") else "C"
                nodos = partes[1:3]  # terminal positivo y negativo (R/C son de 2 terminales)
                detectados.append({"nombre": nombre, "tipo": tipo, "nodos": nodos})
    return detectados

COMPONENTES_AG = extraer_componentes()
NUM_PARAMETROS = len(COMPONENTES_AG)

# ============================================================
# FORMATO SPICE Y ACTUALIZACIÓN (CON VPP/VNN AUTOMÁTICOS)
# ============================================================
def valor_spice(v):
    return re.sub(r'e([+-])0', r'e\1', f"{v:.1e}")

def valor_frecuencia(v):
    """Formatea una frecuencia del barrido .AC para SPICE: entero limpio
    si no tiene parte decimal (1 -> '1', 1e7 -> '10000000')."""
    return str(int(v)) if float(v).is_integer() else str(v)

def actualizar_circuito(individuo):
    texto = Path(ARCHIVO_CIR).read_text()
    lineas = texto.splitlines()

    # 1. Actualizar componentes R y C
    for i, comp in enumerate(COMPONENTES_AG):
        lista = SERIE_E12 if comp["tipo"] == "R" else SERIE_E6
        nuevo_valor = valor_spice(lista[individuo[i]])

        for idx, linea in enumerate(lineas):
            if linea.strip().startswith(comp["nombre"] + " "):
                partes = linea.split()
                partes[-1] = nuevo_valor
                lineas[idx] = " ".join(partes)
                break

    # 2. Inyección dinámica de parámetros fijos y fuentes (vienen del JSON)
    for i, linea in enumerate(lineas):
        partes = linea.split()
        if not partes: continue
        nombre = partes[0].upper()

        if nombre == "VS":
            partes[-1] = str(VS_VALOR)
            lineas[i] = " ".join(partes)
        elif nombre == "VPP":
            partes[-1] = str(VPP_VALOR)
            lineas[i] = " ".join(partes)
        elif nombre == "VNN":
            partes[-1] = str(VNN_VALOR)
            lineas[i] = " ".join(partes)
        elif nombre == "RS":
            partes[-1] = str(RS_VALOR)
            lineas[i] = " ".join(partes)
        elif nombre == "RL":
            partes[-1] = str(RL_VALOR)
            lineas[i] = " ".join(partes)
        elif nombre == ".AC":
            partes[-2] = valor_frecuencia(F_INICIAL)
            partes[-1] = valor_frecuencia(F_FINAL)
            lineas[i] = " ".join(partes)

    Path(ARCHIVO_CIR).write_text("\n".join(lineas))

def ejecutar_spice():
    resultado = subprocess.run([NGSPICE_EXE, "-b", ARCHIVO_CIR], capture_output=True, text=True)
    return resultado.returncode == 0

# ============================================================
# MÉTRICAS
# ============================================================
def _db(x):
    return 20.0 * np.log10(np.maximum(x, 1e-12))

def _cruce_interpolado(frecuencias, amplitudes, nivel):
    """Busca el cruce (interpolado linealmente) de 'amplitudes' por
    'nivel', recorriendo los arreglos en el orden en que se pasen (por
    eso a quien llama le toca pasar el tramo de la curva que le
    interesa: antes o después del pico). Si no hay cruce exacto, cae al
    punto más cercano a 'nivel' dentro del tramo dado."""
    for i in range(len(amplitudes) - 1):
        if (amplitudes[i] <= nivel <= amplitudes[i+1]) or (amplitudes[i] >= nivel >= amplitudes[i+1]):
            f1, f2 = frecuencias[i], frecuencias[i+1]
            a1, a2 = amplitudes[i], amplitudes[i+1]
            if a2 != a1:
                return float(f1 + (nivel - a1) * (f2 - f1) / (a2 - a1))
            return float(f1)
    return float(frecuencias[np.argmin(np.abs(amplitudes - nivel))])

def obtener_metricas_fc():
    """
    MODO BASICO (PASABANDA): cada borde se define por el cruce a -3dB
    respecto del PICO de amplitud (no respecto a DC ni al extremo del
    barrido, porque aquí ambos extremos están atenuados). El borde
    inferior (sube) se busca ANTES del pico; el superior (baja),
    DESPUÉS. Las pendientes se miden una década por fuera de cada Fc:
    por DEBAJO para el inferior (estilo pasaaltas) y por ENCIMA para el
    superior (estilo pasabajas).
    Devuelve: fc_inferior, fc_superior, amp_max, pend_subida, pend_bajada,
    rebote (ver _peor_rebote; solo lado superior, misma razón que en
    obtener_metricas_paso_aten: el borde inferior lo gobierna la etapa
    pasaaltas y no tiene mecanismo físico de rebote).
    """
    try:
        datos = np.loadtxt(ARCHIVO_DATOS)
        frecuencias = datos[:, 0]
        amplitudes = datos[:, 1]

        amp_max = np.max(amplitudes)
        idx_pico = int(np.argmax(amplitudes))
        nivel_fc = amp_max / np.sqrt(2)

        fc_inferior = _cruce_interpolado(frecuencias[:idx_pico+1], amplitudes[:idx_pico+1], nivel_fc)
        fc_superior = _cruce_interpolado(frecuencias[idx_pico:], amplitudes[idx_pico:], nivel_fc)

        idx_inf = np.argmin(np.abs(frecuencias - fc_inferior))
        f_ref_inf = fc_inferior / 10.0  # una década POR DEBAJO (lado de atenuación inferior)
        idx_ref_inf = np.argmin(np.abs(frecuencias - f_ref_inf))
        pend_subida = abs(_db(amplitudes[idx_inf]) - _db(amplitudes[idx_ref_inf]))

        idx_sup = np.argmin(np.abs(frecuencias - fc_superior))
        f_ref_sup = fc_superior * 10.0  # una década POR ENCIMA (lado de atenuación superior)
        idx_ref_sup = np.argmin(np.abs(frecuencias - f_ref_sup))
        pend_bajada = abs(_db(amplitudes[idx_sup]) - _db(amplitudes[idx_ref_sup]))

        # Rebote: ver _peor_rebote(). Solo lado superior, alejándose desde
        # fc_superior hacia el final del barrido.
        rebote = _peor_rebote(amplitudes[idx_sup:])

        return (float(fc_inferior), float(fc_superior), float(amp_max),
                float(pend_subida), float(pend_bajada), float(rebote))
    except:
        return None, None, 0, 0, 0, 0

def _peor_rebote(amplitudes_desde_borde):
    """Recorre 'amplitudes_desde_borde' (ordenadas empezando justo en el
    borde de atenuación F_ATEN_2- y alejándose hacia la banda
    de rechazo) y mide cuánto sube la curva DESPUÉS de su mínimo más
    profundo hasta ese punto.
    - Si la curva solo baja o se mantiene plana: rebote = 0. Esto es
      válido aunque nunca llegue a 0V -p.ej. porque F_ATEN está
      físicamente cerca de F_PASO y no hay décadas suficientes para que
      la pendiente termine de caer-, así que NO se castiga por eso.
    - Si después de bajar la curva vuelve a subir (resonancia que no
      decae, el problema real): el rebote crece con esa subida.
    """
    minimo = amplitudes_desde_borde[0]
    peor = 0.0
    for a in amplitudes_desde_borde[1:]:
        if a < minimo:
            minimo = a
        else:
            peor = max(peor, a - minimo)
    return peor

def obtener_metricas_paso_aten():
    """
    MODO AVANZADO (PASABANDA): se evalúan dos frecuencias de atenuación
    fijas (una antes y otra después de la banda) y la amplitud real en
    las dos frecuencias de paso objetivo (F_PASO_1, F_PASO_2).
    Devuelve:
        amp_max        -> pico máximo de amplitud (V); para detectar
                          saturación
        amp_paso_1      -> amplitud real (V) en F_PASO_1 -> se busca que
                          sea = AMP_PASO_OBJETIVO
        amp_paso_2      -> amplitud real (V) en F_PASO_2 -> idem
        amp_aten_1      -> PEOR CASO (máximo) de amplitud (V) en toda la
                          región del barrido por DEBAJO de F_ATEN_1 -> se
                          busca que sea ~ 0 (no solo el punto exacto, para
                          que ninguna resonancia se "esconda" antes de
                          F_ATEN_1)
        amp_aten_2      -> PEOR CASO (máximo) de amplitud (V) en toda la
                          región del barrido por ENCIMA de F_ATEN_2 ->
                          idem, ninguna resonancia puede escapar después
                          de F_ATEN_2
        pend_subida     -> pendiente real (dB/dec, valor absoluto) entre
                          F_PASO_1 y F_ATEN_1
        pend_bajada     -> pendiente real (dB/dec, valor absoluto) entre
                          F_PASO_2 y F_ATEN_2
        rebote          -> cuánto sube la curva por ENCIMA de F_ATEN_2
                          después de tocar su mínimo (0 si solo decae).
                          No se calcula el equivalente para el lado
                          inferior: por la naturaleza del netlist (etapa
                          pasaaltas), por DEBAJO de F_ATEN_1 los
                          capacitores en serie solo aumentan su
                          impedancia al bajar la frecuencia, así que la
                          curva tiende a 0 monótonamente y no hay
                          mecanismo físico de rebote en ese lado.
    """
    try:
        datos = np.loadtxt(ARCHIVO_DATOS)
        frecuencias = datos[:, 0]
        amplitudes = datos[:, 1]

        amp_max = np.max(amplitudes)

        log_f = np.log10(frecuencias)
        amp_paso_1 = np.interp(np.log10(F_PASO_1), log_f, amplitudes)
        amp_paso_2 = np.interp(np.log10(F_PASO_2), log_f, amplitudes)

        # Atenuación = PEOR CASO en toda la región fuera de la banda (no
        # solo el punto exacto F_ATEN_X). Así un repunte de resonancia en
        # cualquier otra frecuencia de esa región queda penalizado, en vez
        # de poder "esconderse" entre dos muestras sin ser detectado.
        idx_aten1 = int(np.argmin(np.abs(frecuencias - F_ATEN_1)))
        idx_aten2 = int(np.argmin(np.abs(frecuencias - F_ATEN_2)))
        amp_aten_1 = np.max(amplitudes[:idx_aten1 + 1])
        amp_aten_2 = np.max(amplitudes[idx_aten2:])

        # abs() en ambos lados: así no importa el orden relativo de las
        # frecuencias en el JSON.
        pend_subida = abs(_db(amp_paso_1) - _db(amp_aten_1)) / abs(np.log10(F_ATEN_1 / F_PASO_1))
        pend_bajada = abs(_db(amp_paso_2) - _db(amp_aten_2)) / abs(np.log10(F_ATEN_2 / F_PASO_2))

        # Rebote
        rebote = _peor_rebote(amplitudes[idx_aten2:])

        return (float(amp_max), float(amp_paso_1), float(amp_paso_2), float(amp_aten_1), float(amp_aten_2),
                float(pend_subida), float(pend_bajada), float(rebote))
    except:
        return None, 0, 0, 0, 0, 0, 0, 0

# ============================================================
# GRÁFICA DE LA RESPUESTA FINAL
# ============================================================
def graficar_resultado(archivo_salida=GRAFICA_ARCHIVO):
    """
    Grafica la respuesta en frecuencia del circuito ya optimizado, usando
    los datos de la última simulación (la del mejor individuo encontrado
    por el AG) y guarda la imagen en disco.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("[AVISO] No se pudo graficar: falta instalar matplotlib (pip install matplotlib).")
        return

    try:
        datos = np.loadtxt(ARCHIVO_DATOS)
    except Exception as e:
        print(f"[AVISO] No se pudo leer '{ARCHIVO_DATOS}' para graficar: {e}")
        return

    frecuencias = datos[:, 0]
    amplitudes = datos[:, 1]

    fig, ax = plt.subplots(figsize=(8, 5))

    if MODO == "BASICO":
        fc_inf, fc_sup, amp_max, pend_sub, pend_baj, rebote = obtener_metricas_fc()
        nivel_fc = (amp_max / np.sqrt(2)) if amp_max else None

        ax.semilogx(frecuencias, amplitudes, color="#2563eb", linewidth=2, label="Respuesta simulada")
        if nivel_fc is not None:
            ax.axhline(nivel_fc, color="gray", linestyle="--", linewidth=1,
                       label=f"Nivel de corte (-3 dB) ({nivel_fc:.2f} V)")
        ax.axvline(FC_INFERIOR_OBJETIVO, color="#16a34a", linestyle="--", linewidth=1,
                   label=f"Fc inferior objetivo ({FC_INFERIOR_OBJETIVO:.0f} Hz)")
        ax.axvline(FC_SUPERIOR_OBJETIVO, color="#16a34a", linestyle="--", linewidth=1,
                   label=f"Fc superior objetivo ({FC_SUPERIOR_OBJETIVO:.0f} Hz)")
        if fc_inf:
            ax.axvline(fc_inf, color="#dc2626", linestyle=":", linewidth=1.5,
                       label=f"Fc inferior obtenida ({fc_inf:.0f} Hz)")
        if fc_sup:
            ax.axvline(fc_sup, color="#dc2626", linestyle=":", linewidth=1.5,
                       label=f"Fc superior obtenida ({fc_sup:.0f} Hz)")

        ax.set_ylabel("Amplitud (V)")
        ax.set_title("Respuesta en frecuencia del filtro optimizado (MODO BASICO)")

    else:  # AVANZADO
        ax.semilogx(frecuencias, amplitudes, color="#2563eb", linewidth=2, label="Respuesta simulada")
        ax.axhline(AMP_PASO_OBJETIVO, color="#16a34a", linestyle="--", linewidth=1,
                   label=f"Objetivo banda de paso ({AMP_PASO_OBJETIVO:.2f} V)")
        ax.axhline(AMP_ATEN_OBJETIVO, color="#dc2626", linestyle="--", linewidth=1,
                   label=f"Objetivo banda de atenuación ({AMP_ATEN_OBJETIVO:.2f} V)")
        ax.axvline(F_ATEN_1, color="#dc2626", linestyle=":", linewidth=1.5,
                   label=f"F_ATEN_1 ({F_ATEN_1:.0f} Hz)")
        ax.axvline(F_PASO_1, color="#16a34a", linestyle=":", linewidth=1.5,
                   label=f"F_PASO_1 ({F_PASO_1:.0f} Hz)")
        ax.axvline(F_PASO_2, color="#16a34a", linestyle=":", linewidth=1.5,
                   label=f"F_PASO_2 ({F_PASO_2:.0f} Hz)")
        ax.axvline(F_ATEN_2, color="#dc2626", linestyle=":", linewidth=1.5,
                   label=f"F_ATEN_2 ({F_ATEN_2:.0f} Hz)")

        ax.set_ylabel("Amplitud (V)")
        ax.set_title("Respuesta en frecuencia del filtro optimizado (MODO AVANZADO)")

    ax.set_xlabel("Frecuencia (Hz)")
    ax.grid(True, which="both", linestyle=":", alpha=0.5)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()

    fig.savefig(archivo_salida, dpi=150)
    print(f"\nGráfica guardada en: {archivo_salida}")

# ============================================================
# JSON DE RESULTADO
# ============================================================
def _codificar_imagen_base64(ruta_imagen):
    """Lee un archivo PNG y lo devuelve codificado en base64 (string plano,
    sin el prefijo 'data:image/png;base64,' — eso lo agrega quien consuma
    el JSON si lo va a mostrar directo en un <img src=...>)."""
    try:
        return base64.b64encode(Path(ruta_imagen).read_bytes()).decode("ascii")
    except Exception as e:
        print(f"[AVISO] No se pudo codificar la imagen '{ruta_imagen}' en base64: {e}")
        return None

def guardar_resultado_json(mejor_global, mejor_fit, archivo_salida=ARCHIVO_RESULTADO_JSON,
                            archivo_grafica=GRAFICA_ARCHIVO):
    """
    Genera un JSON con el resumen del resultado de la optimización: el
    fitness alcanzado, las frecuencias obtenidas en la simulación final,
    los componentes optimizados con su valor, y la gráfica de la respuesta
    final codificada en base64 (para que el resultado quede 100% autocontenido
    en un solo JSON, útil de cara a una API que recibe y devuelve solo JSON).
    """
    componentes_optimizados = [
        {
            "nombre": comp["nombre"],
            "valor": (SERIE_E12 if comp["tipo"] == "R" else SERIE_E6)[mejor_global[i]],
        }
        for i, comp in enumerate(COMPONENTES_AG)
    ]

    if MODO == "BASICO":
        fc_inf, fc_sup, amp_max, pend_sub, pend_baj, rebote = obtener_metricas_fc()
        frecuencias_obtenidas = [
            {"clave": "fc_inferior_obtenida", "valor": fc_inf},
            {"clave": "fc_superior_obtenida", "valor": fc_sup},
        ]
    else:  # AVANZADO
        (amp_max, amp_paso_1, amp_paso_2, amp_aten_1, amp_aten_2,
         pend_sub, pend_baj, rebote_2) = obtener_metricas_paso_aten()
        frecuencias_obtenidas = [
            {"clave": "amp_paso_1_obtenida", "valor": amp_paso_1},
            {"clave": "amp_paso_2_obtenida", "valor": amp_paso_2},
            {"clave": "amp_aten_1_obtenida", "valor": amp_aten_1},
            {"clave": "amp_aten_2_obtenida", "valor": amp_aten_2},
        ]

    resultado = {
        "fitness": mejor_fit,
        "frecuencias_obtenidas": frecuencias_obtenidas,
        "componentes_optimizados": componentes_optimizados,
        "grafica_png_base64": _codificar_imagen_base64(archivo_grafica),
    }

    Path(archivo_salida).write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Resultado guardado en: {archivo_salida}")
    return resultado

# ============================================================
# FITNESS
# ============================================================
def fitness_fc(individuo):
    """MODO BASICO (PASABANDA): fitness por Fc inferior + Fc superior +
    pendiente de subida y de bajada objetivo + amplitud máxima respecto
    a VS (mientras más cerca esté el pico de VS, mejor: idealmente toda
    la señal de entrada pasa sin pérdida en la banda de paso)."""
    try:
        actualizar_circuito(individuo)
        if not ejecutar_spice(): return 1e-6, 0, None, None, 0, 0, 0, 0, 0, 0, 0, 1.0
        fc_inf, fc_sup, amp_max, pend_sub, pend_baj, rebote = obtener_metricas_fc()

        if fc_inf is None or fc_sup is None: return 1e-6, 0, None, None, 0, 0, 0, 0, 0, 0, 0, 1.0
        # Penalización si el Op-Amp satura (pico mayor al margen de seguridad)
        if amp_max > (VS_VALOR * 1.01):
            return 1e-6, amp_max, fc_inf, fc_sup, pend_sub, pend_baj, 0, 0, 0, 0, 0, 1.0

        f_fc_inf = 1.0 / (1.0 + abs(fc_inf - FC_INFERIOR_OBJETIVO) / FC_INFERIOR_OBJETIVO)
        f_fc_sup = 1.0 / (1.0 + abs(fc_sup - FC_SUPERIOR_OBJETIVO) / FC_SUPERIOR_OBJETIVO)
        f_pend_sub = 1.0 / (1.0 + abs(pend_sub - PENDIENTE_OBJETIVO_FC) / PENDIENTE_OBJETIVO_FC)
        f_pend_baj = 1.0 / (1.0 + abs(pend_baj - PENDIENTE_OBJETIVO_FC) / PENDIENTE_OBJETIVO_FC)
        # Amplitud máxima vs VS: 1.0 cuando amp_max == VS_VALOR exacto,
        # y decae mientras más se aleje (por arriba o por abajo).
        f_amp = 1.0 / (1.0 + abs(amp_max - VS_VALOR) / VS_VALOR)

        fit = (f_fc_inf * 0.25) + (f_fc_sup * 0.25) + (f_pend_sub * 0.125) + \
              (f_pend_baj * 0.125) + (f_amp * 0.25)

        # Compuerta dura: igual que en fitness_paso_aten, castiga el
        # fitness COMPLETO si DESPUÉS de fc_superior la curva REBOTA
        # (sube después de tocar un mínimo) más del margen tolerado. Solo
        # lado superior, por la misma razón física que en MODO AVANZADO.
        pen_rebote = PENALIZACION_ATEN_FALLO if rebote > VS_VALOR * REBOTE_TOLERADO_REL else 1.0
        fit *= pen_rebote

        return (float(fit), amp_max, fc_inf, fc_sup, pend_sub, pend_baj,
                f_fc_inf, f_fc_sup, f_pend_sub, f_pend_baj, f_amp, pen_rebote)
    except Exception:
        return 1e-6, 0, None, None, 0, 0, 0, 0, 0, 0, 0, 1.0

def fitness_paso_aten(individuo):
    """MODO AVANZADO (PASABANDA): fitness por cercanía de la amplitud real
    en F_PASO_1/F_PASO_2 a la amplitud de paso deseada, atenuación en los
    dos extremos y pendientes de subida y bajada objetivo."""
    try:
        actualizar_circuito(individuo)
        if not ejecutar_spice(): return 1e-6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.0
        (amp_max, amp_paso_1, amp_paso_2, amp_aten_1, amp_aten_2,
         pend_subida, pend_bajada, rebote) = obtener_metricas_paso_aten()

        if amp_max is None: return 1e-6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.0
        # Penalización si el Op-Amp satura (pico mayor al margen de seguridad)
        if amp_max > (VS_VALOR * 1.01):
            return (1e-6, amp_max, amp_aten_1, amp_paso_1, amp_paso_2, amp_aten_2,
                    pend_subida, pend_bajada, 0, 0, 0, 0, 0, 0, 1.0)

        # Banda de paso: mientras más cerca de AMP_PASO_OBJETIVO (Vs), mejor.
        f_paso1 = 1.0 / (1.0 + abs(amp_paso_1 - AMP_PASO_OBJETIVO) / VS_VALOR)
        f_paso2 = 1.0 / (1.0 + abs(amp_paso_2 - AMP_PASO_OBJETIVO) / VS_VALOR)

        # Atenuación: mientras más cerca de AMP_ATEN_OBJETIVO (0V), mejor.
        f_aten1 = 1.0 / (1.0 + abs(amp_aten_1 - AMP_ATEN_OBJETIVO) / VS_VALOR)
        f_aten2 = 1.0 / (1.0 + abs(amp_aten_2 - AMP_ATEN_OBJETIVO) / VS_VALOR)

        # Pendientes de subida (borde inferior) y bajada (borde superior).
        f_pSub = 1.0 / (1.0 + abs(pend_subida - PENDIENTE_OBJETIVO_PASO_ATEN) / PENDIENTE_OBJETIVO_PASO_ATEN)
        f_pBaj = 1.0 / (1.0 + abs(pend_bajada - PENDIENTE_OBJETIVO_PASO_ATEN) / PENDIENTE_OBJETIVO_PASO_ATEN)

        fit = (f_paso1 * 0.25) + (f_paso2 * 0.25) + (f_aten1 * 0.15) + (f_aten2 * 0.15) + \
              (f_pSub * 0.1) + (f_pBaj * 0.1)

        # Compuerta dura: castiga el fitness COMPLETO si DESPUÉS de
        # F_ATEN_2 la curva REBOTA (sube después de tocar un mínimo) más
        # del margen tolerado -señal de resonancia que no decae, típica
        # de la caída de ganancia en lazo abierto del Op-Amp en alta
        # frecuencia.
        pen_aten = PENALIZACION_ATEN_FALLO if rebote > VS_VALOR * REBOTE_TOLERADO_REL else 1.0
        fit *= pen_aten

        return (float(fit), amp_max, amp_aten_1, amp_paso_1, amp_paso_2, amp_aten_2,
                pend_subida, pend_bajada, f_paso1, f_paso2, f_aten1, f_aten2, f_pSub, f_pBaj, pen_aten)
    except Exception:
        return 1e-6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.0

def fitness(individuo):
    """Despacha al método de evaluación según MODO."""
    if MODO == "BASICO":
        return fitness_fc(individuo)
    else:
        return fitness_paso_aten(individuo)

# ============================================================
# ALGORITMO GENÉTICO
# ============================================================
def crear_individuo():
    return [random.randint(0, (len(SERIE_E12) if c["tipo"]=="R" else len(SERIE_E6))-1) for c in COMPONENTES_AG]

# ============================================================
# SELECCIÓN, CRUCE Y MUTACIÓN
# ============================================================
def seleccion_torneo(poblacion, fitnesses, k=TORNEO_K):
    """Elige un padre tomando k individuos al azar y devolviendo el de
    mejor fitness entre ellos (k pequeño = más exploración,
    k grande = más presión selectiva)."""
    candidatos = random.sample(range(len(poblacion)), min(k, len(poblacion)))
    idx_mejor = max(candidatos, key=lambda i: fitnesses[i])
    return poblacion[idx_mejor]

def cruzar(p1, p2):
    """Cruce de un punto, con punto de corte aleatorio (no fijo en la
    mitad) y respetando PROB_CRUCE: con esa probabilidad se cruzan los
    padres, y si no, los hijos son copias directas de cada padre (la
    mutación posterior sigue aportando variación)."""
    if NUM_PARAMETROS > 1 and random.random() < PROB_CRUCE:
        punto = random.randint(1, NUM_PARAMETROS - 1)
        h1 = p1[:punto] + p2[punto:]
        h2 = p2[:punto] + p1[punto:]
    else:
        h1, h2 = p1[:], p2[:]
    return h1, h2

def mutar(individuo):
    """Mutación gen a gen: cada componente tiene probabilidad
    PROB_MUTACION de saltar a un valor aleatorio de su serie comercial."""
    for i in range(NUM_PARAMETROS):
        if random.random() < PROB_MUTACION:
            lim = len(SERIE_E12) if COMPONENTES_AG[i]["tipo"] == "R" else len(SERIE_E6)
            individuo[i] = random.randint(0, lim - 1)
    return individuo

def imprimir_encabezado():
    print(f"Configuración: '{ARCHIVO_CONFIG_JSON}' | "
          f"V_fuente={VS_VALOR} V | Rs={RS_VALOR} Ω | Rl={RL_VALOR} Ω")
    print(f"Barrido .AC: {valor_frecuencia(F_INICIAL)} Hz a {valor_frecuencia(F_FINAL)} Hz")
    print(f"AG: población={TAM_POBLACION} | generaciones={NUM_GENERACIONES} | "
          f"elitismo={ELITISMO} | torneo_k={TORNEO_K} | "
          f"prob_cruce={PROB_CRUCE} | prob_mutacion={PROB_MUTACION}")
    if MODO == "BASICO":
        print(f"MODO BASICO (Fc inferior + Fc superior + pendientes) | "
              f"Fc inferior objetivo={FC_INFERIOR_OBJETIVO} Hz | "
              f"Fc superior objetivo={FC_SUPERIOR_OBJETIVO} Hz | "
              f"Pendiente objetivo={PENDIENTE_OBJETIVO_FC:.1f} dB/dec (cada borde) | "
              f"Tolerancia a rebote tras Fc superior={REBOTE_TOLERADO_REL*100:.0f}% de VS (si se excede, fit x{PENALIZACION_ATEN_FALLO})\n")
        print(f"{'Gen':<6} | {'Fit':<6} | {'AmpMax (V)':<10} | {'FcInf (Hz)':<11} | {'FcSup (Hz)':<11} | "
              f"{'PendSub':<8} | {'PendBaj':<8} | {'f_amp':<7} | {'f_fcInf':<8} | {'f_fcSup':<8} | {'f_pSub':<7} | {'f_pBaj':<7} | {'pen_reb':<7}")
        print("-" * 140)
    else:
        print(f"MODO AVANZADO | "
              f"F_ATEN_1={F_ATEN_1} Hz | F_PASO_1={F_PASO_1} Hz | "
              f"F_PASO_2={F_PASO_2} Hz | F_ATEN_2={F_ATEN_2} Hz | "
              f"Pendiente objetivo ~ {PENDIENTE_OBJETIVO_PASO_ATEN:.1f} dB/dec (cada borde) | "
              f"Tolerancia a rebote en F_ATEN_2={REBOTE_TOLERADO_REL*100:.0f}% de VS (si se excede, fit x{PENALIZACION_ATEN_FALLO})\n")
        print(f"{'Gen':<6} | {'Fit':<6} | {'AmpAten1 (V)':<12} | {'AmpPaso1 (V)':<12} | "
              f"{'AmpPaso2 (V)':<12} | {'AmpAten2 (V)':<12} | {'PendSub':<8} | {'PendBaj':<8} | "
              f"{'f_paso1':<7} | {'f_paso2':<7} | {'f_aten1':<7} | {'f_aten2':<7} | {'f_pSub':<7} | {'f_pBaj':<7} | {'pen_aten':<8}")
        print("-" * 175)

def imprimir_generacion(gen, fit, res_best):
    if MODO == "BASICO":
        (amp_max, fc_inf, fc_sup, pend_sub, pend_baj,
         f_fc_inf, f_fc_sup, f_pSub, f_pBaj, f_amp, pen_rebote) = res_best[1:12]
        print(f"{gen+1:<6} | {fit:.4f} | {amp_max:10.3f} | {fc_inf:11.1f} | {fc_sup:11.1f} | "
              f"{pend_sub:8.2f} | {pend_baj:8.2f} | {f_amp:<7.3f} | {f_fc_inf:<8.3f} | {f_fc_sup:<8.3f} | "
              f"{f_pSub:<7.3f} | {f_pBaj:<7.3f} | {pen_rebote:<7.2f}")
    else:
        (amp_max, amp_aten_1, amp_paso_1, amp_paso_2, amp_aten_2, pend_sub, pend_baj,
         f_paso1, f_paso2, f_aten1, f_aten2, f_pSub, f_pBaj, pen_aten) = res_best[1:15]
        print(f"{gen+1:<6} | {fit:.4f} | {amp_aten_1:12.4f} | {amp_paso_1:12.3f} | "
              f"{amp_paso_2:12.3f} | {amp_aten_2:12.4f} | {pend_sub:8.2f} | {pend_baj:8.2f} | "
              f"{f_paso1:<7.3f} | {f_paso2:<7.3f} | {f_aten1:<7.3f} | {f_aten2:<7.3f} | "
              f"{f_pSub:<7.3f} | {f_pBaj:<7.3f} | {pen_aten:<8.2f}")

def ejecutar_AG():
    poblacion = [crear_individuo() for _ in range(TAM_POBLACION)]
    mejor_global = None
    mejor_fit = -1.0

    # Caché de fitness: evita volver a correr SPICE para un individuo ya
    # evaluado antes.
    cache_fitness = {}

    def evaluar(individuo):
        clave = tuple(individuo)
        if clave not in cache_fitness:
            cache_fitness[clave] = fitness(individuo)
        return cache_fitness[clave]

    imprimir_encabezado()

    for gen in range(NUM_GENERACIONES):
        res = [evaluar(ind) for ind in poblacion]
        fitnesses = [r[0] for r in res]

        idx_best = int(np.argmax(fitnesses))
        if fitnesses[idx_best] > mejor_fit:
            mejor_fit = fitnesses[idx_best]
            mejor_global = poblacion[idx_best][:]

        imprimir_generacion(gen, fitnesses[idx_best], res[idx_best])

        indices = np.argsort(fitnesses)[::-1]
        nueva_pob = [poblacion[i][:] for i in indices[:ELITISMO]]

        while len(nueva_pob) < TAM_POBLACION:
            p1 = seleccion_torneo(poblacion, fitnesses)
            p2 = seleccion_torneo(poblacion, fitnesses)
            h1, h2 = cruzar(p1, p2)
            mutar(h1)
            nueva_pob.append(h1)
            if len(nueva_pob) < TAM_POBLACION:
                mutar(h2)
                nueva_pob.append(h2)

        poblacion = nueva_pob

    actualizar_circuito(mejor_global)
    ejecutar_spice()

    print("\n" + "="*50)
    print("OPTIMIZACIÓN FINALIZADA")
    print("Componentes Optimizados:")
    for i, comp in enumerate(COMPONENTES_AG):
        lista = SERIE_E12 if comp["tipo"] == "R" else SERIE_E6
        val = lista[mejor_global[i]]
        print(f"  {comp['nombre']}: {valor_spice(val)}")
    print("="*50)

    graficar_resultado()
    guardar_resultado_json(mejor_global, mejor_fit)

if __name__ == "__main__":
    ejecutar_AG()