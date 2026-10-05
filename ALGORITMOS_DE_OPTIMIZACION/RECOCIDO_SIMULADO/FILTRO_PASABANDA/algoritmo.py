import random
import subprocess
import sys
import base64
import math
import numpy as np
import re
import json
from pathlib import Path

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
    cfg_raw = json.loads(Path(ruta).read_text(encoding="utf-8"))
    modo = str(cfg_raw.get("modo", "")).strip().upper()
    entorno = cfg_raw["entorno"]
    v_fuente = float(entorno["v_fuente"])
    parametros = cfg_raw.get("parametros_optimizador", [])
    frecuencias = cfg_raw.get("frecuencias", [])
    barrido = cfg_raw.get("barrido_ac", {})

    cfg = {
        "modo": modo,
        "v_fuente": v_fuente,
        "r_fuente": float(entorno["r_fuente"]),
        "r_carga": float(entorno["r_carga"]),
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
        cfg["fc_inferior"] = float(_buscar_etiqueta(frecuencias, "fc_inferior"))
        cfg["fc_superior"] = float(_buscar_etiqueta(frecuencias, "fc_superior"))
    else:
        cfg["f_aten_1"] = float(_buscar_etiqueta(frecuencias, "f_aten_1"))
        cfg["f_paso_1"] = float(_buscar_etiqueta(frecuencias, "f_paso_1"))
        cfg["f_paso_2"] = float(_buscar_etiqueta(frecuencias, "f_paso_2"))
        cfg["f_aten_2"] = float(_buscar_etiqueta(frecuencias, "f_aten_2"))
    return cfg

CFG = cargar_configuracion(ARCHIVO_CONFIG_JSON)
MODO, VS_VALOR = CFG["modo"], CFG["v_fuente"]
VPP_VALOR, VNN_VALOR = CFG["vpp"], CFG["vnn"]
RS_VALOR, RL_VALOR = CFG["r_fuente"], CFG["r_carga"]
F_INICIAL, F_FINAL = CFG["f_inicial"], CFG["f_final"]

TEMP_INICIAL = CFG["temp_inicial"]
TEMP_FINAL = CFG["temp_final"]
FACTOR_ENFRIAMIENTO = CFG["factor_enfriamiento"]
ITERACIONES_POR_TEMP = CFG["iteraciones_por_temp"]

PENDIENTE_OBJETIVO_FC = 40.0
PENDIENTE_OBJETIVO_PASO_ATEN = 40.0
FC_INFERIOR_OBJETIVO = CFG.get("fc_inferior")
FC_SUPERIOR_OBJETIVO = CFG.get("fc_superior")
F_ATEN_1, F_PASO_1 = CFG.get("f_aten_1"), CFG.get("f_paso_1")
F_PASO_2, F_ATEN_2 = CFG.get("f_paso_2"), CFG.get("f_aten_2")
AMP_PASO_OBJETIVO, AMP_ATEN_OBJETIVO = VS_VALOR, 0.0
REBOTE_TOLERADO_REL = 0.03
PENALIZACION_ATEN_FALLO = 0.1

def generar_serie(base, decadas):
    serie = []
    for d in decadas:
        for b in base: serie.append(round(b * (10 ** d), 12))
    return sorted(serie)

SERIE_E6 = generar_serie([1.0, 1.5, 2.2, 3.3, 4.7, 6.8], range(-9, -5))
SERIE_E12 = generar_serie([1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2], range(1, 6))

def extraer_componentes():
    texto = Path(ARCHIVO_CIR).read_text()
    detectados = []
    patron = r"^([CR][a-zA-Z0-9_]*)\s+"
    for linea in texto.splitlines():
        m = re.match(patron, linea.strip())
        if m and m.group(1).upper() not in ["RS", "RL", "VS", "VPP", "VNN"]:
            detectados.append({"nombre": m.group(1), "tipo": "R" if m.group(1).upper().startswith("R") else "C"})
    return detectados

COMPONENTES_AG = extraer_componentes()
NUM_PARAMETROS = len(COMPONENTES_AG)

def valor_spice(v): return re.sub(r'e([+-])0', r'e\1', f"{v:.1e}")
def valor_frecuencia(v): return str(int(v)) if float(v).is_integer() else str(v)

def actualizar_circuito(individuo):
    lineas = Path(ARCHIVO_CIR).read_text().splitlines()
    for i, comp in enumerate(COMPONENTES_AG):
        nuevo_valor = valor_spice((SERIE_E12 if comp["tipo"] == "R" else SERIE_E6)[individuo[i]])
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
        elif nombre == ".AC":
            partes[-2], partes[-1] = valor_frecuencia(F_INICIAL), valor_frecuencia(F_FINAL)
            lineas[i] = " ".join(partes)
    Path(ARCHIVO_CIR).write_text("\n".join(lineas))

def ejecutar_spice():
    return subprocess.run([NGSPICE_EXE, "-b", ARCHIVO_CIR], capture_output=True, text=True).returncode == 0

def _db(x): return 20.0 * np.log10(np.maximum(x, 1e-12))

def _cruce_interpolado(frecuencias, amplitudes, nivel):
    for i in range(len(amplitudes) - 1):
        if (amplitudes[i] <= nivel <= amplitudes[i+1]) or (amplitudes[i] >= nivel >= amplitudes[i+1]):
            if amplitudes[i+1] != amplitudes[i]:
                return float(frecuencias[i] + (nivel - amplitudes[i]) * (frecuencias[i+1] - frecuencias[i]) / (amplitudes[i+1] - amplitudes[i]))
            return float(frecuencias[i])
    return float(frecuencias[np.argmin(np.abs(amplitudes - nivel))])

def _peor_rebote(amplitudes_desde_borde):
    minimo, peor = amplitudes_desde_borde[0], 0.0
    for a in amplitudes_desde_borde[1:]:
        if a < minimo: minimo = a
        else: peor = max(peor, a - minimo)
    return peor

def obtener_metricas_fc():
    try:
        datos = np.loadtxt(ARCHIVO_DATOS)
        frecuencias, amplitudes = datos[:, 0], datos[:, 1]
        amp_max, idx_pico = np.max(amplitudes), int(np.argmax(amplitudes))
        nivel_fc = amp_max / np.sqrt(2)
        fc_inf = _cruce_interpolado(frecuencias[:idx_pico+1], amplitudes[:idx_pico+1], nivel_fc)
        fc_sup = _cruce_interpolado(frecuencias[idx_pico:], amplitudes[idx_pico:], nivel_fc)
        
        idx_inf = np.argmin(np.abs(frecuencias - fc_inf))
        idx_ref_inf = np.argmin(np.abs(frecuencias - (fc_inf / 10.0)))
        pend_subida = abs(_db(amplitudes[idx_inf]) - _db(amplitudes[idx_ref_inf]))
        
        idx_sup = np.argmin(np.abs(frecuencias - fc_sup))
        idx_ref_sup = np.argmin(np.abs(frecuencias - (fc_sup * 10.0)))
        pend_bajada = abs(_db(amplitudes[idx_sup]) - _db(amplitudes[idx_ref_sup]))
        
        rebote = _peor_rebote(amplitudes[idx_sup:])
        return float(fc_inf), float(fc_sup), float(amp_max), float(pend_subida), float(pend_bajada), float(rebote)
    except: return None, None, 0, 0, 0, 0

def obtener_metricas_paso_aten():
    try:
        datos = np.loadtxt(ARCHIVO_DATOS)
        frecuencias, amplitudes = datos[:, 0], datos[:, 1]
        amp_max, log_f = np.max(amplitudes), np.log10(frecuencias)
        amp_paso_1 = np.interp(np.log10(F_PASO_1), log_f, amplitudes)
        amp_paso_2 = np.interp(np.log10(F_PASO_2), log_f, amplitudes)
        
        idx_aten1 = int(np.argmin(np.abs(frecuencias - F_ATEN_1)))
        idx_aten2 = int(np.argmin(np.abs(frecuencias - F_ATEN_2)))
        amp_aten_1 = np.max(amplitudes[:idx_aten1 + 1])
        amp_aten_2 = np.max(amplitudes[idx_aten2:])
        
        pend_subida = abs(_db(amp_paso_1) - _db(amp_aten_1)) / abs(np.log10(F_ATEN_1 / F_PASO_1))
        pend_bajada = abs(_db(amp_paso_2) - _db(amp_aten_2)) / abs(np.log10(F_ATEN_2 / F_PASO_2))
        rebote = _peor_rebote(amplitudes[idx_aten2:])
        return float(amp_max), float(amp_paso_1), float(amp_paso_2), float(amp_aten_1), float(amp_aten_2), float(pend_subida), float(pend_bajada), float(rebote)
    except: return None, 0, 0, 0, 0, 0, 0, 0

def fitness_fc(individuo):
    try:
        actualizar_circuito(individuo)
        if not ejecutar_spice(): return 1e-6, 0, None, None, 0, 0, 0, 0, 0, 0, 0, 1.0
        fc_inf, fc_sup, amp_max, pend_sub, pend_baj, rebote = obtener_metricas_fc()
        if fc_inf is None or fc_sup is None: return 1e-6, 0, None, None, 0, 0, 0, 0, 0, 0, 0, 1.0
        if amp_max > (VS_VALOR * 1.01): return 1e-6, amp_max, fc_inf, fc_sup, pend_sub, pend_baj, 0, 0, 0, 0, 0, 1.0
        
        f_fc_inf = 1.0 / (1.0 + abs(fc_inf - FC_INFERIOR_OBJETIVO) / FC_INFERIOR_OBJETIVO)
        f_fc_sup = 1.0 / (1.0 + abs(fc_sup - FC_SUPERIOR_OBJETIVO) / FC_SUPERIOR_OBJETIVO)
        f_pend_sub = 1.0 / (1.0 + abs(pend_sub - PENDIENTE_OBJETIVO_FC) / PENDIENTE_OBJETIVO_FC)
        f_pend_baj = 1.0 / (1.0 + abs(pend_baj - PENDIENTE_OBJETIVO_FC) / PENDIENTE_OBJETIVO_FC)
        f_amp = 1.0 / (1.0 + abs(amp_max - VS_VALOR) / VS_VALOR)
        
        fit = (f_fc_inf * 0.25) + (f_fc_sup * 0.25) + (f_pend_sub * 0.125) + (f_pend_baj * 0.125) + (f_amp * 0.25)
        pen_rebote = PENALIZACION_ATEN_FALLO if rebote > VS_VALOR * REBOTE_TOLERADO_REL else 1.0
        fit *= pen_rebote
        return float(fit), amp_max, fc_inf, fc_sup, pend_sub, pend_baj, f_fc_inf, f_fc_sup, f_pend_sub, f_pend_baj, f_amp, pen_rebote
    except: return 1e-6, 0, None, None, 0, 0, 0, 0, 0, 0, 0, 1.0

def fitness_paso_aten(individuo):
    try:
        actualizar_circuito(individuo)
        if not ejecutar_spice(): return 1e-6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.0
        amp_max, amp_paso_1, amp_paso_2, amp_aten_1, amp_aten_2, pend_subida, pend_bajada, rebote = obtener_metricas_paso_aten()
        if amp_max is None: return 1e-6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.0
        if amp_max > (VS_VALOR * 1.01): return 1e-6, amp_max, amp_aten_1, amp_paso_1, amp_paso_2, amp_aten_2, pend_subida, pend_bajada, 0, 0, 0, 0, 0, 0, 1.0
        
        f_paso1 = 1.0 / (1.0 + abs(amp_paso_1 - AMP_PASO_OBJETIVO) / VS_VALOR)
        f_paso2 = 1.0 / (1.0 + abs(amp_paso_2 - AMP_PASO_OBJETIVO) / VS_VALOR)
        f_aten1 = 1.0 / (1.0 + abs(amp_aten_1 - AMP_ATEN_OBJETIVO) / VS_VALOR)
        f_aten2 = 1.0 / (1.0 + abs(amp_aten_2 - AMP_ATEN_OBJETIVO) / VS_VALOR)
        f_pSub = 1.0 / (1.0 + abs(pend_subida - PENDIENTE_OBJETIVO_PASO_ATEN) / PENDIENTE_OBJETIVO_PASO_ATEN)
        f_pBaj = 1.0 / (1.0 + abs(pend_bajada - PENDIENTE_OBJETIVO_PASO_ATEN) / PENDIENTE_OBJETIVO_PASO_ATEN)
        
        fit = (f_paso1 * 0.25) + (f_paso2 * 0.25) + (f_aten1 * 0.15) + (f_aten2 * 0.15) + (f_pSub * 0.1) + (f_pBaj * 0.1)
        pen_aten = PENALIZACION_ATEN_FALLO if rebote > VS_VALOR * REBOTE_TOLERADO_REL else 1.0
        fit *= pen_aten
        return float(fit), amp_max, amp_aten_1, amp_paso_1, amp_paso_2, amp_aten_2, pend_subida, pend_bajada, f_paso1, f_paso2, f_aten1, f_aten2, f_pSub, f_pBaj, pen_aten
    except: return 1e-6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.0

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

def guardar_resultado_json(mejor_global, mejor_fit):
    componentes_optimizados = [{"nombre": c["nombre"], "valor": (SERIE_E12 if c["tipo"] == "R" else SERIE_E6)[mejor_global[i]]} for i, c in enumerate(COMPONENTES_AG)]
    if MODO == "BASICO":
        met = obtener_metricas_fc()
        frecuencias_obtenidas = [{"clave": "fc_inferior_obtenida", "valor": met[0]}, {"clave": "fc_superior_obtenida", "valor": met[1]}]
    else:
        met = obtener_metricas_paso_aten()
        frecuencias_obtenidas = [{"clave": "amp_paso_1_obtenida", "valor": met[1]}, {"clave": "amp_paso_2_obtenida", "valor": met[2]}, {"clave": "amp_aten_1_obtenida", "valor": met[3]}, {"clave": "amp_aten_2_obtenida", "valor": met[4]}]
    resultado = {"fitness": mejor_fit, "frecuencias_obtenidas": frecuencias_obtenidas, "componentes_optimizados": componentes_optimizados}
    Path(ARCHIVO_RESULTADO_JSON).write_text(json.dumps(resultado, indent=2), encoding="utf-8")

def crear_solucion_inicial(): return [random.randint(0, (len(SERIE_E12) if c["tipo"]=="R" else len(SERIE_E6))-1) for c in COMPONENTES_AG]

def generar_vecino(estado_actual):
    vecino = estado_actual[:]
    num_mutaciones = random.randint(1, max(1, NUM_PARAMETROS // 3))
    indices_a_mutar = random.sample(range(NUM_PARAMETROS), num_mutaciones)
    for i in indices_a_mutar:
        lim = len(SERIE_E12) if COMPONENTES_AG[i]["tipo"] == "R" else len(SERIE_E6)
        vecino[i] = max(0, min(lim - 1, vecino[i] + random.choice([-2, -1, 1, 2])))
    return vecino

def ejecutar_RS():
    print(f"RS PASABANDA | Temp: {TEMP_INICIAL} -> {TEMP_FINAL} | Factor: {FACTOR_ENFRIAMIENTO}")
    estado_actual = crear_solucion_inicial()
    fit_actual = fitness(estado_actual)[0]
    mejor_estado, mejor_fit = estado_actual[:], fit_actual
    temperatura, ciclo = TEMP_INICIAL, 1
    
    while temperatura > TEMP_FINAL:
        for _ in range(ITERACIONES_POR_TEMP):
            vecino = generar_vecino(estado_actual)
            fit_vecino = fitness(vecino)[0]
            delta_fit = fit_vecino - fit_actual
            if delta_fit > 0 or random.random() < math.exp(delta_fit / temperatura):
                estado_actual, fit_actual = vecino[:], fit_vecino
                if fit_actual > mejor_fit: mejor_estado, mejor_fit = estado_actual[:], fit_actual
        print(f"Ciclo {ciclo:<3} | Temp: {temperatura:.4f} | Mejor Fit: {mejor_fit:.4f}")
        temperatura *= FACTOR_ENFRIAMIENTO
        ciclo += 1

    actualizar_circuito(mejor_estado)
    ejecutar_spice()
    graficar_resultado()
    guardar_resultado_json(mejor_estado, mejor_fit)

if __name__ == "__main__":
    ejecutar_RS()