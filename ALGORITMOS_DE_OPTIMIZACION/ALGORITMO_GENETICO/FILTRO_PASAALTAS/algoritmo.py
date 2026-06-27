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
        cfg["fc_objetivo"] = float(_buscar_etiqueta(frecuencias, "fc_objetivo"))
    else:  # AVANZADO
        cfg["f_paso"] = float(_buscar_etiqueta(frecuencias, "f_paso"))
        cfg["f_aten"] = float(_buscar_etiqueta(frecuencias, "f_aten"))

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
# Pendiente teórica máxima de un pasaaltas Sallen-Key de 4to orden (dos
# etapas de 2do orden en cascada): 80 dB/dec. Se usa como objetivo en
# ambos modos y no depende de la configuración del usuario.
PENDIENTE_OBJETIVO_FC = 80.0
PENDIENTE_OBJETIVO_PASO_ATEN = 80.0

# Objetivos específicos de cada modo (frecuencias, sí vienen del JSON).
FC_OBJETIVO = CFG.get("fc_objetivo")
F_PASO = CFG.get("f_paso")
F_ATEN = CFG.get("f_aten")

# Amplitudes ideales en MODO AVANZADO: en banda de paso se busca que pase
# toda la señal de entrada (= v_fuente) y en banda de atenuación que la
# señal quede completamente eliminada (= 0V). Se derivan de v_fuente, por
# lo que no es necesario indicarlas en el JSON.
AMP_PASO_OBJETIVO = VS_VALOR
AMP_ATEN_OBJETIVO = 0.0

# ============================================================
# SERIES COMERCIALES (E6 Capacitores, E12 Resistencias)
# ============================================================
def generar_serie(base, decadas):
    serie = []
    for d in decadas:
        for b in base:
            # round() evita el ruido de floating point
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

def calcular_f_plano(frecuencias, amplitudes):
    """
    Mide qué tan ancha es la meseta de la banda de paso: cuántas décadas,
    a partir del pico máximo de la curva, tarda la amplitud en caer por
    debajo del 95% de ese pico. Un pico resonante angosto (atajo que el AG
    puede preferir si la fitness solo evalúa 1-2 puntos discretos de la
    curva) cae casi de inmediato y obtiene un f_plano cercano a 0; una
    banda de paso ancha y plana tarda varias décadas en caer y se acerca
    a 1. Si la curva nunca cae al 95% dentro del barrido (sin evidencia
    de que se angoste), se devuelve 1.0, el mejor caso posible.

    Nota: si el pico máximo es ~0V (filtro que no deja pasar nada), el
    bucle tampoco encuentra una caída por debajo de 0.95*0 y también
    devuelve 1.0. No es un problema práctico aquí porque ese caso ya
    queda fuertemente penalizado por f_paso/f_fc (pesos mayores), pero
    vale la pena tenerlo presente.

    Además, lo anterior solo mira hacia ADELANTE desde el pico máximo
    global, así que es ciego a una resonancia (sube-baja-sube) que
    ocurra ANTES de llegar a ese pico (ej. un rizado a media subida que
    luego sigue subiendo hasta un máximo más alto al final del barrido).
    Para cubrir ese caso se mide también la peor caída relativa al
    máximo acumulado hasta el pico (running max): cualquier "vuelta
    atrás" en la subida cuenta como resonancia. f_plano final es el
    peor (mínimo) de ambas métricas.
    """
    idx_max = int(np.argmax(amplitudes))
    amp_max = amplitudes[idx_max]
    f_max = frecuencias[idx_max]

    umbral_95 = 0.95 * amp_max
    idx_caida = None
    for i in range(idx_max, len(amplitudes)):
        if amplitudes[i] < umbral_95:
            idx_caida = i
            break

    if idx_caida is None:
        f_plano_post = 1.0
    else:
        ancho_decadas = np.log10(frecuencias[idx_caida] / f_max)
        f_plano_post = float(ancho_decadas / (ancho_decadas + 1.0))

    # Resonancia ANTES del pico global: cualquier caída respecto al
    # máximo ya alcanzado en la subida hacia idx_max.
    if amp_max > 0 and idx_max > 0:
        subida = amplitudes[:idx_max + 1]
        maximo_acumulado = np.maximum.accumulate(subida)
        peor_caida = float(np.max(maximo_acumulado - subida))
        f_plano_pre = 1.0 / (1.0 + (peor_caida / amp_max) * 10.0)
    else:
        f_plano_pre = 1.0

    return min(f_plano_post, f_plano_pre)

def obtener_metricas_fc():
    """
    MODO BASICO: busca la frecuencia de corte real (cruce por amp_max/sqrt(2))
    y mide la pendiente una década por DEBAJO de esa Fc (en el pasaaltas la
    atenuación cae hacia baja frecuencia, al revés que en el pasabajas).
    Devuelve: fc_real, amp_max, pendiente, f_plano
    """
    try:
        datos = np.loadtxt(ARCHIVO_DATOS)
        frecuencias = datos[:, 0]
        amplitudes = datos[:, 1]

        amp_max = np.max(amplitudes)

        nivel_fc = amp_max / np.sqrt(2)
        fc_real = None
        for i in range(len(amplitudes) - 1):
            if (amplitudes[i] <= nivel_fc <= amplitudes[i+1]) or (amplitudes[i] >= nivel_fc >= amplitudes[i+1]):
                f1, f2 = frecuencias[i], frecuencias[i+1]
                a1, a2 = amplitudes[i], amplitudes[i+1]
                fc_real = f1 + (nivel_fc - a1) * (f2 - f1) / (a2 - a1)
                break

        if fc_real is None: fc_real = frecuencias[np.argmin(np.abs(amplitudes - nivel_fc))]

        idx_fc = np.argmin(np.abs(frecuencias - fc_real))
        f_ref = fc_real / 10.0  # una década POR DEBAJO de Fc (lado de atenuación)
        idx_ref = np.argmin(np.abs(frecuencias - f_ref))

        pend = abs(_db(amplitudes[idx_fc]) - _db(amplitudes[idx_ref]))

        # Anti-resonancia: qué tan ancha es la meseta de la banda de paso
        # arriba de Fc (un pico angosto centrado en Fc puede dar un cruce
        # de -3dB y una pendiente "buenos" sin ser un pasaaltas real).
        f_plano = calcular_f_plano(frecuencias, amplitudes)

        return float(fc_real), float(amp_max), float(pend), float(f_plano)
    except:
        return None, 0, 0, 0

def obtener_metricas_paso_aten():
    """
    MODO AVANZADO: evalúa la respuesta en dos puntos, F_PASO (banda de paso) y
    F_ATEN (banda de atenuación), interpolando en escala logarítmica de
    frecuencia (el barrido es .AC DEC). Devuelve:
        amp_max   -> pico máximo (para detectar saturación / picos resonantes)
        amp_paso  -> voltaje real (V) en F_PASO -> se busca que sea = AMP_PASO_OBJETIVO
        amp_aten  -> voltaje real (V) en F_ATEN -> se busca que sea = AMP_ATEN_OBJETIVO
        pendiente -> pendiente real (dB/dec, valor absoluto) entre F_PASO y F_ATEN
        f_plano   -> qué tan ancha es la meseta de la banda de paso (anti-resonancia)
    """
    try:
        datos = np.loadtxt(ARCHIVO_DATOS)
        frecuencias = datos[:, 0]
        amplitudes = datos[:, 1]

        amp_max = np.max(amplitudes)

        log_f = np.log10(frecuencias)
        amp_paso = np.interp(np.log10(F_PASO), log_f, amplitudes)
        amp_aten = np.interp(np.log10(F_ATEN), log_f, amplitudes)

        # abs() en ambos lados: en el pasaaltas F_PASO > F_ATEN (al revés que
        # en el pasabajas), así la fórmula da la magnitud de la pendiente sin
        # importar el orden de las frecuencias en el JSON.
        pendiente = abs(_db(amp_paso) - _db(amp_aten)) / abs(np.log10(F_ATEN / F_PASO))

        # Anti-resonancia: un pico angosto centrado justo en F_PASO puede
        # acertarle a amp_paso sin ser una banda de paso real.
        f_plano = calcular_f_plano(frecuencias, amplitudes)

        return float(amp_max), float(amp_paso), float(amp_aten), float(pendiente), float(f_plano)
    except:
        return None, 0, 0, 0, 0

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
        # Respuesta en amplitud (V)
        fc_real, amp_max, pend, _ = obtener_metricas_fc()
        nivel_fc = (amp_max / np.sqrt(2)) if amp_max else None

        ax.semilogx(frecuencias, amplitudes, color="#2563eb", linewidth=2, label="Respuesta simulada")
        if nivel_fc is not None:
            ax.axhline(nivel_fc, color="gray", linestyle="--", linewidth=1,
                       label=f"Nivel de corte (-3 dB) ({nivel_fc:.2f} V)")
        ax.axvline(FC_OBJETIVO, color="#16a34a", linestyle="--", linewidth=1,
                   label=f"Fc objetivo ({FC_OBJETIVO:.0f} Hz)")
        if fc_real:
            ax.axvline(fc_real, color="#dc2626", linestyle=":", linewidth=1.5,
                       label=f"Fc obtenida ({fc_real:.0f} Hz)")

        ax.set_ylabel("Amplitud (V)")
        ax.set_title("Respuesta en frecuencia del filtro optimizado (MODO BASICO)")

    else:  # AVANZADO
        ax.semilogx(frecuencias, amplitudes, color="#2563eb", linewidth=2, label="Respuesta simulada")
        ax.axhline(AMP_PASO_OBJETIVO, color="#16a34a", linestyle="--", linewidth=1,
                   label=f"Objetivo banda de paso ({AMP_PASO_OBJETIVO:.2f} V)")
        ax.axhline(AMP_ATEN_OBJETIVO, color="#dc2626", linestyle="--", linewidth=1,
                   label=f"Objetivo banda de atenuación ({AMP_ATEN_OBJETIVO:.2f} V)")
        ax.axvline(F_ATEN, color="#dc2626", linestyle=":", linewidth=1.5,
                   label=f"F_ATEN ({F_ATEN:.0f} Hz)")
        ax.axvline(F_PASO, color="#16a34a", linestyle=":", linewidth=1.5,
                   label=f"F_PASO ({F_PASO:.0f} Hz)")

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
        fc_real, amp_max, pend, _ = obtener_metricas_fc()
        frecuencias_obtenidas = [
            {"clave": "fc_obtenida", "valor": fc_real},
        ]
    else:  # AVANZADO
        amp_max, amp_paso, amp_aten, pendiente, _ = obtener_metricas_paso_aten()
        frecuencias_obtenidas = [
            {"clave": "amp_paso_obtenida", "valor": amp_paso},
            {"clave": "amp_aten_obtenida", "valor": amp_aten},
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
    """MODO BASICO: fitness por Fc objetivo + pendiente objetivo + amplitud máxima (busca llegar a V_fuente) + anti-resonancia."""
    try:
        actualizar_circuito(individuo)
        if not ejecutar_spice(): return 1e-6, None, 0, 0, 0, 0, 0, 0
        fc, amp_max, pend, f_plano = obtener_metricas_fc()

        if fc is None: return 1e-6, None, 0, 0, 0, 0, 0, 0
        # Penalización si el Op-Amp satura (pico mayor al margen de seguridad)
        if amp_max > (VS_VALOR * 1.01): return 1e-6, fc, amp_max, pend, 0, 0, f_plano, 0

        f_fc = 1.0 / (1.0 + abs(fc - FC_OBJETIVO) / FC_OBJETIVO)
        f_pend = 1.0 / (1.0 + abs(pend - PENDIENTE_OBJETIVO_FC) / PENDIENTE_OBJETIVO_FC)
        f_amp = 1.0 / (1.0 + abs(VS_VALOR - amp_max) / VS_VALOR)

        fit = (f_plano * 0.2) + (f_fc * 0.4) + (f_pend * 0.2) + (f_amp * 0.2)
        return float(fit), fc, amp_max, pend, f_fc, f_pend, f_plano, f_amp
    except Exception:
        return 1e-6, None, 0, 0, 0, 0, 0, 0

def fitness_paso_aten(individuo):
    """MODO AVANZADO: fitness por acercamiento a voltaje máximo en F_PASO, mínimo en F_ATEN y anti-resonancia."""
    try:
        actualizar_circuito(individuo)
        if not ejecutar_spice(): return 1e-6, 0, 0, 0, 0, 0, 0, 0
        amp_max, amp_paso, amp_aten, pendiente, f_plano = obtener_metricas_paso_aten()

        if amp_max is None: return 1e-6, 0, 0, 0, 0, 0, 0, 0
        # Penalización si el Op-Amp satura (pico mayor al margen de seguridad)
        if amp_max > (VS_VALOR * 1.01): return 1e-6, amp_paso, amp_aten, pendiente, 0, 0, 0, 0

        # 1. Calculamos el error relativo (de 0.0 a 1.0)
        error_rel_paso = abs(AMP_PASO_OBJETIVO - amp_paso) / AMP_PASO_OBJETIVO
        # 2. Aplicamos un castigo severo. Si el error es grande, el denominador explota.
        # El factor 100.0 y la potencia 4 aseguran que filtros "tramposos" reprueben al instante.
        f_paso = 1.0 / (1.0 + (error_rel_paso ** 4) * 100.0)
        # En F_ATEN: mientras más cerca de AMP_ATEN_OBJETIVO, mejor.
        f_aten = 1.0 / (1.0 + abs(amp_aten - AMP_ATEN_OBJETIVO) / VS_VALOR)
        # Pendiente real entre ambos puntos, comparada con la teórica del filtro.
        f_pend = 1.0 / (1.0 + abs(pendiente - PENDIENTE_OBJETIVO_PASO_ATEN) / PENDIENTE_OBJETIVO_PASO_ATEN)

        fit = (f_paso * 0.4) + (f_aten * 0.3) + (f_pend * 0.1) + (f_plano * 0.2)
        return float(fit), amp_paso, amp_aten, pendiente, f_paso, f_aten, f_pend, f_plano
    except Exception:
        return 1e-6, 0, 0, 0, 0, 0, 0, 0

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
        print(f"MODO BASICO (Fc + pendiente) | Fc objetivo={FC_OBJETIVO} Hz | "
              f"Pendiente objetivo={PENDIENTE_OBJETIVO_FC:.1f} dB/dec\n")
        print(f"{'Gen':<6} | {'Fit':<6} | {'Fc (Hz)':<10} | {'Amp (V)':<8} | {'Pend (dB/dec)':<15} | "
              f"{'f_fc':<6} | {'f_amp':<6} | {'f_pend':<6} | {'f_plano':<7}")
        print("-" * 104)
    else:
        print(f"MODO AVANZADO (paso/atenuación) | F_ATEN={F_ATEN} Hz (objetivo {AMP_ATEN_OBJETIVO} V) | "
              f"F_PASO={F_PASO} Hz (objetivo {AMP_PASO_OBJETIVO} V) | "
              f"Pendiente objetivo ~ {PENDIENTE_OBJETIVO_PASO_ATEN:.1f} dB/dec\n")
        print(f"{'Gen':<6} | {'Fit':<6} | {'Amp Aten (V)':<13} | {'Amp Paso (V)':<13} | {'Pend (dB/dec)':<13} | "
              f"{'f_aten':<6} | {'f_paso':<6} | {'f_pend':<6} | {'f_plano':<7}")
        print("-" * 110)

def imprimir_generacion(gen, fit, res_best):
    if MODO == "BASICO":
        fc, amp, pend, f_fc, f_pend, f_plano, f_amp = res_best[1], res_best[2], res_best[3], res_best[4], res_best[5], res_best[6], res_best[7]
        print(f"{gen+1:<6} | {fit:.4f} | {fc:10.1f} | {amp:8.2f} | {pend:15.2f} | "
              f"{f_fc:<6.3f} | {f_amp:<6.3f} | {f_pend:<6.3f} | {f_plano:<7.3f}")
    else:
        amp_paso, amp_aten, pend = res_best[1], res_best[2], res_best[3]
        f_paso, f_aten, f_pend, f_plano = res_best[4], res_best[5], res_best[6], res_best[7]
        print(f"{gen+1:<6} | {fit:.4f} | {amp_aten:13.4f} | {amp_paso:13.3f} | {pend:13.2f} | "
              f"{f_aten:<6.3f} | {f_paso:<6.3f} | {f_pend:<6.3f} | {f_plano:<7.3f}")

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