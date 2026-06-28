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
        # --- parámetros del enjambre de partículas (PSO) ---
        "num_particulas": int(_buscar_etiqueta(parametros, "num_particulas")),
        "num_iteraciones": int(_buscar_etiqueta(parametros, "num_iteraciones")),
        "w": float(_buscar_etiqueta(parametros, "w")),
        "c1": float(_buscar_etiqueta(parametros, "c1")),
        "c2": float(_buscar_etiqueta(parametros, "c2")),
    }

    if modo == "BASICO":
        # Dos Fc objetivo: los bordes de la MUESCA (rechazo), el que
        # baja (inferior) y el que vuelve a subir (superior).
        cfg["fc_inferior"] = float(_buscar_etiqueta(frecuencias, "fc_inferior"))
        cfg["fc_superior"] = float(_buscar_etiqueta(frecuencias, "fc_superior"))
    else:  # AVANZADO
        # 4 frecuencias para RECHAZA BANDA, en ESTE orden (de menor a
        # mayor frecuencia): paso inicio, atenuación inferior (borde
        # inferior de la muesca), atenuación superior (borde superior
        # de la muesca), paso fin.
        #   F_PASO_1 < F_ATEN_1 < F_ATEN_2 < F_PASO_2
        # (es el orden invertido respecto a un pasabanda: aquí la
        # atenuación queda en el centro y el paso en los extremos).
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

NUM_PARTICULAS = CFG["num_particulas"]
NUM_ITERACIONES = CFG["num_iteraciones"]
W = CFG["w"]
C1 = CFG["c1"]
C2 = CFG["c2"]

# ============================================================
# CONSTANTES DE DISEÑO FIJAS EN EL CÓDIGO (no vienen del JSON)
# ============================================================
# Pendiente objetivo POR FLANCO de la muesca (rechaza banda).
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

COMPONENTES = extraer_componentes()
NUM_PARAMETROS = len(COMPONENTES)

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
    for i, comp in enumerate(COMPONENTES):
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
    MODO BASICO (RECHAZA BANDA):
    - Se busca el valle (mínimo) para dividir el espectro.
    - Los cruces a -3dB se calculan respecto al amp_max (banda de paso).
    - Pendientes calculadas hacia el valle con protección ante divisiones por cero.
    """
    try:
        datos = np.loadtxt(ARCHIVO_DATOS)
        frecuencias = datos[:, 0]
        amplitudes = datos[:, 1]

        amp_max = np.max(amplitudes)
        idx_valle = int(np.argmin(amplitudes))
        nivel_fc = amp_max / np.sqrt(2)

        # Buscar cruces interpolados
        fc_inferior = _cruce_interpolado(frecuencias[:idx_valle+1], amplitudes[:idx_valle+1], nivel_fc)
        fc_superior = _cruce_interpolado(frecuencias[idx_valle:], amplitudes[idx_valle:], nivel_fc)

        f_valle = frecuencias[idx_valle]
        amp_valle = amplitudes[idx_valle]
        
        # --- CÁLCULO DE PENDIENTES CON PROTECCIÓN ---
        # Evitamos divisiones por cero si el valle coincide con fc
        def safe_div(valle, fc):
            den = abs(np.log10(valle / fc))
            return den if den > 1e-12 else 1e-12

        idx_inf = np.argmin(np.abs(frecuencias - fc_inferior))
        pend_subida = abs(_db(amplitudes[idx_inf]) - _db(amp_valle)) / safe_div(f_valle, fc_inferior)

        idx_sup = np.argmin(np.abs(frecuencias - fc_superior))
        pend_bajada = abs(_db(amplitudes[idx_sup]) - _db(amp_valle)) / safe_div(f_valle, fc_superior)

        return float(fc_inferior), float(fc_superior), float(amp_max), float(pend_subida), float(pend_bajada)
        
    except Exception as e:
        return None, None, 0, 0, 0

def obtener_metricas_paso_aten():
    """
    MODO AVANZADO (RECHAZA BANDA)
    Orden esperado (de menor a mayor frecuencia):
        F_PASO_1 < F_ATEN_1 < F_ATEN_2 < F_PASO_2
    Devuelve:
        amp_max        -> nivel de PASO de referencia (V); máximo
                          alcanzado lejos de la muesca, también usado
                          para detectar saturación
        amp_paso_1      -> amplitud real (V) en F_PASO_1 -> se busca
                          que sea = AMP_PASO_OBJETIVO
        amp_paso_2      -> amplitud real (V) en F_PASO_2 -> se busca
                          que sea = AMP_PASO_OBJETIVO
        amp_aten_1      -> amplitud real (V) en F_ATEN_1 -> se busca
                          que sea = AMP_ATEN_OBJETIVO
        amp_aten_2      -> amplitud real (V) en F_ATEN_2 -> idem
        pend_bajada     -> pendiente real (dB/dec, valor absoluto)
                          entre F_PASO_1 y F_ATEN_1
        pend_subida     -> pendiente real (dB/dec, valor absoluto)
                          entre F_ATEN_2 y F_PASO_2
    """
    try:
        datos = np.loadtxt(ARCHIVO_DATOS)
        frecuencias = datos[:, 0]
        amplitudes = datos[:, 1]

        amp_max = np.max(amplitudes)

        log_f = np.log10(frecuencias)
        
        amp_paso_1 = np.interp(np.log10(F_PASO_1), log_f, amplitudes)
        amp_paso_2 = np.interp(np.log10(F_PASO_2), log_f, amplitudes)

        amp_aten_1 = np.interp(np.log10(F_ATEN_1), log_f, amplitudes)
        amp_aten_2 = np.interp(np.log10(F_ATEN_2), log_f, amplitudes)

        # abs() en ambos lados: así no importa el orden relativo de las
        # frecuencias en el JSON.
        pend_bajada = abs(_db(amp_paso_1) - _db(amp_aten_1)) / abs(np.log10(F_ATEN_1 / F_PASO_1))
        pend_subida = abs(_db(amp_paso_2) - _db(amp_aten_2)) / abs(np.log10(F_ATEN_2 / F_PASO_2))

        return (float(amp_max), float(amp_paso_1), float(amp_paso_2), float(amp_aten_1), float(amp_aten_2),
                float(pend_subida), float(pend_bajada))
    except:
        return None, 0, 0, 0, 0, 0, 0

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
        fc_inf, fc_sup, amp_max, pend_sub, pend_baj = obtener_metricas_fc()
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
        ax.axvline(F_PASO_1, color="#16a34a", linestyle=":", linewidth=1.5,
                   label=f"F_PASO_1 ({F_PASO_1:.0f} Hz)")
        ax.axvline(F_ATEN_1, color="#dc2626", linestyle=":", linewidth=1.5,
                   label=f"F_ATEN_1 ({F_ATEN_1:.0f} Hz)")
        ax.axvline(F_ATEN_2, color="#dc2626", linestyle=":", linewidth=1.5,
                   label=f"F_ATEN_2 ({F_ATEN_2:.0f} Hz)")
        ax.axvline(F_PASO_2, color="#16a34a", linestyle=":", linewidth=1.5,
                   label=f"F_PASO_2 ({F_PASO_2:.0f} Hz)")

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
        for i, comp in enumerate(COMPONENTES)
    ]

    if MODO == "BASICO":
        fc_inf, fc_sup, amp_max, pend_sub, pend_baj = obtener_metricas_fc()
        frecuencias_obtenidas = [
            {"clave": "fc_inferior_obtenida", "valor": fc_inf},
            {"clave": "fc_superior_obtenida", "valor": fc_sup},
        ]
    else:  # AVANZADO
        (amp_max, amp_paso_1, amp_paso_2, amp_aten_1, amp_aten_2,
         pend_sub, pend_baj) = obtener_metricas_paso_aten()
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
    """MODO BASICO (RECHAZA BANDA): fitness por Fc inferior + Fc superior
    de la muesca + pendiente de bajada y de subida objetivo + ganancia
    general."""
    try:
        actualizar_circuito(individuo)
        if not ejecutar_spice(): return 1e-6, None, None, 0, 0, 0, 0, 0, 0
        fc_inf, fc_sup, amp_max, pend_sub, pend_baj = obtener_metricas_fc()

        if fc_inf is None or fc_sup is None: return 1e-6, None, None, 0, 0, 0, 0, 0, 0
        # Penalización si el Op-Amp satura (pico mayor al margen de seguridad)
        if amp_max > (VS_VALOR * 1.01):
            return 1e-6, fc_inf, fc_sup, pend_sub, pend_baj, 0, 0, 0, 0

        f_fc_inf = 1.0 / (1.0 + abs(fc_inf - FC_INFERIOR_OBJETIVO) / FC_INFERIOR_OBJETIVO)
        f_fc_sup = 1.0 / (1.0 + abs(fc_sup - FC_SUPERIOR_OBJETIVO) / FC_SUPERIOR_OBJETIVO)
        f_pend_sub = 1.0 / (1.0 + abs(pend_sub - PENDIENTE_OBJETIVO_FC) / PENDIENTE_OBJETIVO_FC)
        f_pend_baj = 1.0 / (1.0 + abs(pend_baj - PENDIENTE_OBJETIVO_FC) / PENDIENTE_OBJETIVO_FC)

        fit = (f_fc_inf * 0.4) + (f_fc_sup * 0.4) + (f_pend_sub * 0.1) + (f_pend_baj * 0.1)
        return (float(fit), fc_inf, fc_sup, pend_sub, pend_baj,
                f_fc_inf, f_fc_sup, f_pend_sub, f_pend_baj)
    except Exception:
        return 1e-6, None, None, 0, 0, 0, 0, 0, 0

def fitness_paso_aten(individuo):
    """MODO AVANZADO (RECHAZA BANDA)"""
    try:
        actualizar_circuito(individuo)
        if not ejecutar_spice():
            return 1e-6, None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        (amp_max, amp_paso_1, amp_paso_2, amp_aten_1, amp_aten_2,
        pend_subida, pend_bajada) = obtener_metricas_paso_aten()

        if amp_max is None:
            return 1e-6, None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        # Penalización si el Op-Amp satura (pico mayor al margen de seguridad)
        if amp_max > (VS_VALOR * 1.01):
            return (1e-6, amp_aten_1, amp_paso_1, amp_paso_2, amp_aten_2,
                    pend_subida, pend_bajada, 0, 0, 0, 0, 0, 0)

        # Qué tan baja (cerca de 0V) es la amplitud real en F_ATEN_1/F_ATEN_2.
        f_aten1 = 1.0 / (1.0 + abs(amp_aten_1 - AMP_ATEN_OBJETIVO) / VS_VALOR)
        f_aten2 = 1.0 / (1.0 + abs(amp_aten_2 - AMP_ATEN_OBJETIVO) / VS_VALOR)

        # Paso: mientras más cerca de AMP_PASO_OBJETIVO (Vs) esté el
        # peor caso (mínimo) de cada región externa a la muesca, mejor.
        f_paso1 = 1.0 / (1.0 + abs(amp_paso_1 - AMP_PASO_OBJETIVO) / VS_VALOR)
        f_paso2 = 1.0 / (1.0 + abs(amp_paso_2 - AMP_PASO_OBJETIVO) / VS_VALOR)

        # Pendientes de bajada (hacia la muesca, lado inferior) y subida
        # (saliendo de la muesca, lado superior).
        f_pend_subida = 1.0 / (1.0 + abs(pend_subida - PENDIENTE_OBJETIVO_PASO_ATEN) / PENDIENTE_OBJETIVO_PASO_ATEN)
        f_pend_bajada = 1.0 / (1.0 + abs(pend_bajada - PENDIENTE_OBJETIVO_PASO_ATEN) / PENDIENTE_OBJETIVO_PASO_ATEN)

        fit = (f_aten1 * 0.15) + (f_aten2 * 0.15) + (f_paso1 * 0.25) + (f_paso2 * 0.25) + \
              (f_pend_subida * 0.1) + (f_pend_bajada * 0.1)

        return (float(fit), amp_aten_1, amp_paso_1, amp_paso_2, amp_aten_2,
                pend_subida, pend_bajada,
                f_paso1, f_paso2, f_aten1, f_aten2, f_pend_subida, f_pend_bajada)
    except Exception:
        return 1e-6, None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0

def fitness(individuo):
    """Despacha al método de evaluación según MODO."""
    if MODO == "BASICO":
        return fitness_fc(individuo)
    else:
        return fitness_paso_aten(individuo)

# ============================================================
# ENJAMBRE DE PARTÍCULAS (PSO)
# ============================================================
def crear_individuo():
    return [random.randint(0, (len(SERIE_E12) if c["tipo"]=="R" else len(SERIE_E6))-1) for c in COMPONENTES]

# Límite superior (índice máximo válido) de cada dimensión, según si el
# componente es R (serie E12) o C (serie E6).
LIMITES = [(len(SERIE_E12) if c["tipo"] == "R" else len(SERIE_E6)) - 1 for c in COMPONENTES]

# Velocidad máxima por dimensión: acota qué tanto puede moverse una
# partícula en un solo paso (20% del rango de esa dimensión), evitando que
# "vuele" fuera del espacio de búsqueda de un salto.
VMAX = [0.2 * lim for lim in LIMITES]

def crear_velocidad():
    return [random.uniform(-VMAX[i], VMAX[i]) for i in range(NUM_PARAMETROS)]

def redondear_individuo(posicion):
    """Convierte una posición continua de PSO al índice entero (discreto)
    de la serie comercial correspondiente, recortando a los límites."""
    return [int(round(min(max(p, 0.0), LIMITES[i]))) for i, p in enumerate(posicion)]

def imprimir_encabezado():
    print(f"Configuración: '{ARCHIVO_CONFIG_JSON}' | "
          f"V_fuente={VS_VALOR} V | Rs={RS_VALOR} Ω | Rl={RL_VALOR} Ω")
    print(f"Barrido .AC: {valor_frecuencia(F_INICIAL)} Hz a {valor_frecuencia(F_FINAL)} Hz")
    print(f"PSO: partículas={NUM_PARTICULAS} | iteraciones={NUM_ITERACIONES} | "
          f"w={W} | c1={C1} | c2={C2}")
    if MODO == "BASICO":
        print(f"MODO BASICO (Fc inferior + Fc superior de la MUESCA + pendientes) | "
              f"Fc inferior objetivo={FC_INFERIOR_OBJETIVO} Hz | "
              f"Fc superior objetivo={FC_SUPERIOR_OBJETIVO} Hz | "
              f"Pendiente objetivo={PENDIENTE_OBJETIVO_FC:.1f} dB/dec (cada flanco)\n")
        print(f"{'Iter':<6} | {'Fit':<6} | {'FcInf (Hz)':<11} | {'FcSup (Hz)':<11} | "
              f"{'PendBaj':<8} | {'PendSub':<8} | {'f_fcInf':<8} | {'f_fcSup':<8} | "
              f"{'f_pBaj':<7} | {'f_pSub':<7}")
        print("-" * 110)
    else:
        print(f"MODO AVANZADO (RECHAZA BANDA) | "
              f"F_PASO_1={F_PASO_1} Hz | F_ATEN_1={F_ATEN_1} Hz | "
              f"F_ATEN_2={F_ATEN_2} Hz | F_PASO_2={F_PASO_2} Hz | "
              f"Pendiente objetivo ~ {PENDIENTE_OBJETIVO_PASO_ATEN:.1f} dB/dec (cada flanco)\n")
        print(f"{'Iter':<6} | {'Fit':<6} | {'AmpPaso1 (V)':<12} | {'AmpAten1 (V)':<12} | "
              f"{'AmpAten2 (V)':<12} | {'AmpPaso2 (V)':<12} | {'PendBaj':<8} | {'PendSub':<8} | "
              f"{'f_paso1':<7} | {'f_paso2':<7} | {'f_aten1':<7} | {'f_aten2':<7} | "
              f"{'f_pBaj':<7} | {'f_pSub':<7}")
        print("-" * 165)

def imprimir_generacion(gen, fit, res_best):
    if MODO == "BASICO":
        (fc_inf, fc_sup, pend_sub, pend_baj,
         f_fc_inf, f_fc_sup, f_pend_sub, f_pend_baj) = res_best[1:9]
        print(f"{gen+1:<6} | {fit:.4f} | {fc_inf:11.1f} | {fc_sup:11.1f} | "
              f"{pend_baj:8.2f} | {pend_sub:8.2f} | {f_fc_inf:<8.3f} | {f_fc_sup:<8.3f} | "
              f"{f_pend_baj:<7.3f} | {f_pend_sub:<7.3f}")
    else:
        (amp_aten_1, amp_paso_1, amp_paso_2, amp_aten_2,
         pend_sub, pend_baj, f_paso1, f_paso2, f_aten1, f_aten2,
         f_pend_sub, f_pend_baj) = res_best[1:13]
        print(f"{gen+1:<6} | {fit:.4f} | {amp_paso_1:12.4f} | {amp_aten_1:12.4f} | "
              f"{amp_aten_2:12.4f} | {amp_paso_2:12.4f} | {pend_baj:8.2f} | {pend_sub:8.2f} | "
              f"{f_paso1:<7.3f} | {f_paso2:<7.3f} | {f_aten1:<7.3f} | {f_aten2:<7.3f} | "
              f"{f_pend_baj:<7.3f} | {f_pend_sub:<7.3f}")

def ejecutar_PSO():
    # Posiciones iniciales: mismos índices discretos que el AG, pero
    # representados como flotantes porque PSO necesita moverse en un
    # espacio continuo (se redondean solo al evaluar el circuito).
    posiciones = [[float(g) for g in crear_individuo()] for _ in range(NUM_PARTICULAS)]
    velocidades = [crear_velocidad() for _ in range(NUM_PARTICULAS)]

    # Caché de fitness: evita volver a correr SPICE para un individuo ya
    # evaluado antes (misma idea que en el AG, aquí la clave es el
    # individuo discreto resultante de redondear la posición).
    cache_fitness = {}

    def evaluar(individuo):
        clave = tuple(individuo)
        if clave not in cache_fitness:
            cache_fitness[clave] = fitness(individuo)
        return cache_fitness[clave]

    # Mejor posición histórica de cada partícula (pbest) y su fitness.
    pbest_pos = [pos[:] for pos in posiciones]
    pbest_individuo = [redondear_individuo(pos) for pos in posiciones]
    pbest_res = [evaluar(ind) for ind in pbest_individuo]
    pbest_fit = [r[0] for r in pbest_res]

    # Mejor posición global del enjambre (gbest).
    idx_gbest = int(np.argmax(pbest_fit))
    gbest_pos = pbest_pos[idx_gbest][:]
    gbest_individuo = pbest_individuo[idx_gbest][:]
    gbest_fit = pbest_fit[idx_gbest]
    gbest_res = pbest_res[idx_gbest]

    imprimir_encabezado()

    for it in range(NUM_ITERACIONES):
        for p in range(NUM_PARTICULAS):
            for d in range(NUM_PARAMETROS):
                r1, r2 = random.random(), random.random()
                # Ecuación clásica de PSO: inercia + atracción al mejor
                # personal (cognitivo) + atracción al mejor global (social).
                velocidades[p][d] = (
                    W * velocidades[p][d]
                    + C1 * r1 * (pbest_pos[p][d] - posiciones[p][d])
                    + C2 * r2 * (gbest_pos[d] - posiciones[p][d])
                )
                velocidades[p][d] = max(-VMAX[d], min(VMAX[d], velocidades[p][d]))

                posiciones[p][d] += velocidades[p][d]
                posiciones[p][d] = max(0.0, min(float(LIMITES[d]), posiciones[p][d]))

            individuo = redondear_individuo(posiciones[p])
            res = evaluar(individuo)
            fit = res[0]

            if fit > pbest_fit[p]:
                pbest_fit[p] = fit
                pbest_pos[p] = posiciones[p][:]
                pbest_individuo[p] = individuo[:]
                pbest_res[p] = res

        idx_mejor_pbest = int(np.argmax(pbest_fit))
        if pbest_fit[idx_mejor_pbest] > gbest_fit:
            gbest_fit = pbest_fit[idx_mejor_pbest]
            gbest_pos = pbest_pos[idx_mejor_pbest][:]
            gbest_individuo = pbest_individuo[idx_mejor_pbest][:]
            gbest_res = pbest_res[idx_mejor_pbest]

        imprimir_generacion(it, gbest_fit, gbest_res)

    actualizar_circuito(gbest_individuo)
    ejecutar_spice()

    print("\n" + "="*50)
    print("OPTIMIZACIÓN FINALIZADA")
    print("Componentes Optimizados:")
    for i, comp in enumerate(COMPONENTES):
        lista = SERIE_E12 if comp["tipo"] == "R" else SERIE_E6
        val = lista[gbest_individuo[i]]
        print(f"  {comp['nombre']}: {valor_spice(val)}")
    print("="*50)

    graficar_resultado()
    guardar_resultado_json(gbest_individuo, gbest_fit)

if __name__ == "__main__":
    ejecutar_PSO()