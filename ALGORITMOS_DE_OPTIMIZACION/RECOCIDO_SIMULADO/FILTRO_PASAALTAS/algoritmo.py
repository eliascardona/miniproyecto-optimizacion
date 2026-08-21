import random
import subprocess
import sys
import base64
import math
import numpy as np
import re
import json
from pathlib import Path

# ============================================================
# RUTAS DE EJECUCIÓN
# ============================================================
NGSPICE_EXE = r"C:\Users\garab\Downloads\Spice64\bin\ngspice.exe"
ARCHIVO_CIR = "filtro.cir"
ARCHIVO_DATOS = "datos_filtro.txt"
ARCHIVO_CONFIG_JSON = "config.json"
GRAFICA_ARCHIVO = "resultado_filtro.png"
ARCHIVO_RESULTADO_JSON = "resultado.json"

def _buscar_etiqueta(lista, etiqueta):
    for item in lista:
        if item.get("clave") == etiqueta:
            return item.get("valor")

def cargar_configuracion(ruta):
    try:
        cfg_raw = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"[ERROR] No se encontró el archivo de configuración: {ruta}")
    
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
        "v_fuente": v_fuente,
        "r_fuente": r_fuente,
        "r_carga": r_carga,
        "vpp": v_fuente + 10.0,
        "vnn": -(v_fuente + 10.0),
        "f_inicial": float(barrido["f_inicial"]),
        "f_final": float(barrido["f_final"]),
        "temp_inicial": float(_buscar_etiqueta(parametros, "temp_inicial")),
        "temp_final": float(_buscar_etiqueta(parametros, "temp_final")),
        "factor_enfriamiento": float(_buscar_etiqueta(parametros, "factor_enfriamiento")),
        "iteraciones_por_temp": int(_buscar_etiqueta(parametros, "iteraciones_por_temp")),
    }

    if modo == "BASICO":
        cfg["fc_objetivo"] = float(_buscar_etiqueta(frecuencias, "fc_objetivo"))
    else:  # AVANZADO
        cfg["f_paso"] = float(_buscar_etiqueta(frecuencias, "f_paso"))
        cfg["f_aten"] = float(_buscar_etiqueta(frecuencias, "f_aten"))
    return cfg

CFG = cargar_configuracion(ARCHIVO_CONFIG_JSON)

MODO = CFG["modo"]
VS_VALOR = CFG["v_fuente"]
VPP_VALOR = CFG["vpp"]
VNN_VALOR = CFG["vnn"]
RS_VALOR = CFG["r_fuente"]
RL_VALOR = CFG["r_carga"]
F_INICIAL = CFG["f_inicial"]
F_FINAL = CFG["f_final"]
TEMP_INICIAL = CFG["temp_inicial"]
TEMP_FINAL = CFG["temp_final"]
FACTOR_ENFRIAMIENTO = CFG["factor_enfriamiento"]
ITERACIONES_POR_TEMP = CFG["iteraciones_por_temp"]

PENDIENTE_OBJETIVO_FC = 80.0
PENDIENTE_OBJETIVO_PASO_ATEN = 80.0
FC_OBJETIVO = CFG.get("fc_objetivo")
F_PASO = CFG.get("f_paso")
F_ATEN = CFG.get("f_aten")
AMP_PASO_OBJETIVO = VS_VALOR
AMP_ATEN_OBJETIVO = 0.0

def generar_serie(base, decadas):
    serie = []
    for d in decadas:
        for b in base:
            serie.append(round(b * (10 ** d), 12))
    return sorted(serie)

SERIE_E6 = generar_serie([1.0, 1.5, 2.2, 3.3, 4.7, 6.8], range(-9, -5))
SERIE_E12 = generar_serie([1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2], range(1, 6))

def extraer_componentes():
    texto = Path(ARCHIVO_CIR).read_text()
    detectados = []
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
                nodos = partes[1:3]
                detectados.append({"nombre": nombre, "tipo": tipo, "nodos": nodos})
    return detectados

COMPONENTES_AG = extraer_componentes()
NUM_PARAMETROS = len(COMPONENTES_AG)

def valor_spice(v): return re.sub(r'e([+-])0', r'e\1', f"{v:.1e}")
def valor_frecuencia(v): return str(int(v)) if float(v).is_integer() else str(v)

def actualizar_circuito(individuo):
    texto = Path(ARCHIVO_CIR).read_text()
    lineas = texto.splitlines()
    for i, comp in enumerate(COMPONENTES_AG):
        lista = SERIE_E12 if comp["tipo"] == "R" else SERIE_E6
        nuevo_valor = valor_spice(lista[individuo[i]])
        for idx, linea in enumerate(lineas):
            if linea.strip().startswith(comp["nombre"] + " "):
                partes = linea.split()
                partes[-1] = nuevo_valor
                lineas[idx] = " ".join(partes)
                break
    for i, linea in enumerate(lineas):
        partes = linea.split()
        if not partes: continue
        nombre = partes[0].upper()
        if nombre == "VS": lineas[i] = linea.replace(partes[-1], str(VS_VALOR))
        elif nombre == "VPP": lineas[i] = linea.replace(partes[-1], str(VPP_VALOR))
        elif nombre == "VNN": lineas[i] = linea.replace(partes[-1], str(VNN_VALOR))
        elif nombre == "RS": lineas[i] = linea.replace(partes[-1], str(RS_VALOR))
        elif nombre == "RL": lineas[i] = linea.replace(partes[-1], str(RL_VALOR))
        elif nombre == ".AC":
            partes[-2] = valor_frecuencia(F_INICIAL)
            partes[-1] = valor_frecuencia(F_FINAL)
            lineas[i] = " ".join(partes)
    Path(ARCHIVO_CIR).write_text("\n".join(lineas))

def ejecutar_spice():
    resultado = subprocess.run([NGSPICE_EXE, "-b", ARCHIVO_CIR], capture_output=True, text=True)
    return resultado.returncode == 0

def _db(x): return 20.0 * np.log10(np.maximum(x, 1e-12))

def calcular_f_plano(frecuencias, amplitudes):
    idx_max = int(np.argmax(amplitudes))
    amp_max = amplitudes[idx_max]
    f_max = frecuencias[idx_max]
    umbral_95 = 0.95 * amp_max
    idx_caida = None
    for i in range(idx_max, len(amplitudes)):
        if amplitudes[i] < umbral_95:
            idx_caida = i
            break
    if idx_caida is None: f_plano_post = 1.0
    else:
        ancho_decadas = np.log10(frecuencias[idx_caida] / f_max)
        f_plano_post = float(ancho_decadas / (ancho_decadas + 1.0))
    if amp_max > 0 and idx_max > 0:
        subida = amplitudes[:idx_max + 1]
        maximo_acumulado = np.maximum.accumulate(subida)
        peor_caida = float(np.max(maximo_acumulado - subida))
        f_plano_pre = 1.0 / (1.0 + (peor_caida / amp_max) * 10.0)
    else: f_plano_pre = 1.0
    return min(f_plano_post, f_plano_pre)

def obtener_metricas_fc():
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
        f_ref = fc_real / 10.0
        idx_ref = np.argmin(np.abs(frecuencias - f_ref))
        pend = abs(_db(amplitudes[idx_fc]) - _db(amplitudes[idx_ref]))
        f_plano = calcular_f_plano(frecuencias, amplitudes)
        return float(fc_real), float(amp_max), float(pend), float(f_plano)
    except: return None, 0, 0, 0

def obtener_metricas_paso_aten():
    try:
        datos = np.loadtxt(ARCHIVO_DATOS)
        frecuencias = datos[:, 0]
        amplitudes = datos[:, 1]
        amp_max = np.max(amplitudes)
        log_f = np.log10(frecuencias)
        amp_paso = np.interp(np.log10(F_PASO), log_f, amplitudes)
        amp_aten = np.interp(np.log10(F_ATEN), log_f, amplitudes)
        pendiente = abs(_db(amp_paso) - _db(amp_aten)) / abs(np.log10(F_ATEN / F_PASO))
        f_plano = calcular_f_plano(frecuencias, amplitudes)
        return float(amp_max), float(amp_paso), float(amp_aten), float(pendiente), float(f_plano)
    except: return None, 0, 0, 0, 0
    
    


def fitness_fc(individuo):
    try:
        actualizar_circuito(individuo)
        if not ejecutar_spice(): return 1e-6, None, 0, 0, 0, 0, 0, 0
        fc, amp_max, pend, f_plano = obtener_metricas_fc()
        if fc is None: return 1e-6, None, 0, 0, 0, 0, 0, 0
        if amp_max > (VS_VALOR * 1.01): return 1e-6, fc, amp_max, pend, 0, 0, f_plano, 0
        f_fc = 1.0 / (1.0 + abs(fc - FC_OBJETIVO) / FC_OBJETIVO)
        f_pend = 1.0 / (1.0 + abs(pend - PENDIENTE_OBJETIVO_FC) / PENDIENTE_OBJETIVO_FC)
        f_amp = 1.0 / (1.0 + abs(VS_VALOR - amp_max) / VS_VALOR)
        fit = (f_plano * 0.2) + (f_fc * 0.4) + (f_pend * 0.2) + (f_amp * 0.2)
        return float(fit), fc, amp_max, pend, f_fc, f_pend, f_plano, f_amp
    except Exception: return 1e-6, None, 0, 0, 0, 0, 0, 0

def fitness_paso_aten(individuo):
    try:
        actualizar_circuito(individuo)
        if not ejecutar_spice(): return 1e-6, 0, 0, 0, 0, 0, 0, 0
        amp_max, amp_paso, amp_aten, pendiente, f_plano = obtener_metricas_paso_aten()
        if amp_max is None: return 1e-6, 0, 0, 0, 0, 0, 0, 0
        if amp_max > (VS_VALOR * 1.01): return 1e-6, amp_paso, amp_aten, pendiente, 0, 0, 0, 0
        error_rel_paso = abs(AMP_PASO_OBJETIVO - amp_paso) / AMP_PASO_OBJETIVO
        f_paso = 1.0 / (1.0 + (error_rel_paso ** 4) * 100.0)
        f_aten = 1.0 / (1.0 + abs(amp_aten - AMP_ATEN_OBJETIVO) / VS_VALOR)
        f_pend = 1.0 / (1.0 + abs(pendiente - PENDIENTE_OBJETIVO_PASO_ATEN) / PENDIENTE_OBJETIVO_PASO_ATEN)
        fit = (f_paso * 0.4) + (f_aten * 0.3) + (f_pend * 0.1) + (f_plano * 0.2)
        return float(fit), amp_paso, amp_aten, pendiente, f_paso, f_aten, f_pend, f_plano
    except Exception: return 1e-6, 0, 0, 0, 0, 0, 0, 0

def fitness(individuo):
    if MODO == "BASICO": return fitness_fc(individuo)
    else: return fitness_paso_aten(individuo)

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


def guardar_resultado_json(mejor_global, mejor_fit):
    componentes_optimizados = [{"nombre": c["nombre"], "valor": (SERIE_E12 if c["tipo"] == "R" else SERIE_E6)[mejor_global[i]]} for i, c in enumerate(COMPONENTES_AG)]
    if MODO == "BASICO":
        frecuencias_obtenidas = [{"clave": "fc_obtenida", "valor": obtener_metricas_fc()[0]}]
    else:
        met = obtener_metricas_paso_aten()
        frecuencias_obtenidas = [{"clave": "amp_paso_obtenida", "valor": met[1]}, {"clave": "amp_aten_obtenida", "valor": met[2]}]
    resultado = {"fitness": mejor_fit, "frecuencias_obtenidas": frecuencias_obtenidas, "componentes_optimizados": componentes_optimizados}
    Path(ARCHIVO_RESULTADO_JSON).write_text(json.dumps(resultado, indent=2), encoding="utf-8")

def crear_solucion_inicial():
    return [random.randint(0, (len(SERIE_E12) if c["tipo"]=="R" else len(SERIE_E6))-1) for c in COMPONENTES_AG]

def generar_vecino(estado_actual):
    vecino = estado_actual[:]
    num_mutaciones = random.randint(1, max(1, NUM_PARAMETROS // 3))
    indices_a_mutar = random.sample(range(NUM_PARAMETROS), num_mutaciones)
    for i in indices_a_mutar:
        lim = len(SERIE_E12) if COMPONENTES_AG[i]["tipo"] == "R" else len(SERIE_E6)
        salto = random.choice([-2, -1, 1, 2])
        vecino[i] = max(0, min(lim - 1, vecino[i] + salto))
    return vecino

def ejecutar_RS():
    print(f"RS PASAALTAS | Temp: {TEMP_INICIAL} -> {TEMP_FINAL} | Factor: {FACTOR_ENFRIAMIENTO}")
    estado_actual = crear_solucion_inicial()
    fit_actual = fitness(estado_actual)[0]
    mejor_estado, mejor_fit = estado_actual[:], fit_actual
    temperatura, ciclo = TEMP_INICIAL, 1
    
    while temperatura > TEMP_FINAL:
        for _ in range(ITERACIONES_POR_TEMP):
            vecino = generar_vecino(estado_actual)
            fit_vecino = fitness(vecino)[0]
            delta_fit = fit_vecino - fit_actual
            if delta_fit > 0:
                estado_actual, fit_actual = vecino[:], fit_vecino
                if fit_actual > mejor_fit: mejor_estado, mejor_fit = estado_actual[:], fit_actual
            else:
                if random.random() < math.exp(delta_fit / temperatura):
                    estado_actual, fit_actual = vecino[:], fit_vecino
        print(f"Ciclo {ciclo:<3} | Temp: {temperatura:.4f} | Mejor Fit: {mejor_fit:.4f}")
        temperatura *= FACTOR_ENFRIAMIENTO
        ciclo += 1

    actualizar_circuito(mejor_estado)
    ejecutar_spice()
    guardar_resultado_json(mejor_estado, mejor_fit)
    graficar_resultado()

if __name__ == "__main__":
    ejecutar_RS()