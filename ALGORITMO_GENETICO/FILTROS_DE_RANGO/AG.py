import random
import subprocess
import numpy as np
import re
import json
from pathlib import Path

# ============================================================
# CONFIGURACION
# ============================================================
NGSPICE_EXE = r"C:\Users\luis_\Desktop\Spice64\bin\ngspice.exe"
ARCHIVO_CIR = "circuit_0.cir"
ARCHIVO_DATOS = "datos_filtro.txt"

# ============================================================
# OBJETIVO DE DISEÑO (PASABANDA CON RANGO)
# ============================================================
FL_OBJETIVO = 400.0         # Frecuencia de corte inferior deseada (Hz)
FH_OBJETIVO = 600.0         # Frecuencia de corte superior deseada (Hz)
AMPLITUD_OBJETIVO = 5.0     # Amplitud esperada en la banda de paso (V)
PENDIENTE_OBJETIVO = 40.0   # Pendiente buscada en las bandas de atenuación (dB/dec)

# ============================================================
# PARÁMETROS DEL ALGORITMO GENÉTICO
# ============================================================
TAM_POBLACION = 60          # Más individuos para la complejidad de rango
NUM_GENERACIONES = 40       # Más generaciones para estabilizar ambos cortes
PROB_CRUCE = 0.85
PROB_MUTACION = 0.35
ELITISMO = 3

# ============================================================
# SERIES COMERCIALES (E6 para Capacitores, E12 para Resistencias)
# ============================================================
def generar_serie(base, decadas):
    serie = []
    for d in decadas:
        for b in base:
            serie.append(b * (10 ** d))
    return sorted(serie)

SERIE_E6 = generar_serie([1.0, 1.5, 2.2, 3.3, 4.7, 6.8], range(-9, -4))
SERIE_E12 = generar_serie([1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2], range(1, 6))

# ============================================================
# PARSER DINÁMICO: DETECTA CUALQUIER R Y C, MENOS Rs Y Rl
# ============================================================
def extraer_componentes():
    texto = Path(ARCHIVO_CIR).read_text(encoding="utf-8")
    detectados = []
    
    fijos = ["RS", "RL", "R_S", "R_L"] 
    patron = r"^([CR][a-zA-Z0-9_]*)\s+"
    
    for linea in texto.splitlines():
        linea = linea.strip()
        m = re.match(patron, linea)
        if m:
            nombre = m.group(1)
            if nombre.upper() not in fijos:
                tipo = "R" if nombre.upper().startswith("R") else "C"
                detectados.append({"nombre": nombre, "tipo": tipo})
    return detectados

COMPONENTES_AG = extraer_componentes()
NUM_PARAMETROS = len(COMPONENTES_AG)
print(f"Componentes detectados para optimización: {NUM_PARAMETROS}")
for c in COMPONENTES_AG:
    print(f"  - {c['nombre']} ({c['tipo']})")

# ============================================================
# FORMATO SPICE Y REEMPLAZO SEGURO
# ============================================================
def valor_spice(v):
    return re.sub(r'e([+-])0', r'e\1', f"{v:.1e}")

def actualizar_circuito(individuo):
    texto = Path(ARCHIVO_CIR).read_text(encoding="utf-8")
    lineas = texto.splitlines()
    
    for i, comp in enumerate(COMPONENTES_AG):
        lista = SERIE_E12 if comp["tipo"] == "R" else SERIE_E6
        nuevo_valor = valor_spice(lista[individuo[i]])
        
        for idx, linea in enumerate(lineas):
            linea_limpia = linea.strip()
            if linea_limpia.startswith(comp["nombre"]) and re.match(rf"^{comp['nombre']}\s+", linea_limpia):
                partes = linea_limpia.split()
                partes[-1] = nuevo_valor
                lineas[idx] = " ".join(partes)
                break
                
    Path(ARCHIVO_CIR).write_text("\n".join(lineas), encoding="utf-8")

def ejecutar_spice():
    resultado = subprocess.run([NGSPICE_EXE, "-b", ARCHIVO_CIR], capture_output=True, text=True)
    return resultado.returncode == 0

# ============================================================
# OBTENER METRICAS (DOS FRECUENCIAS DE CORTE + PENDIENTE + AMP)
# ============================================================
def obtener_metricas():
    try:
        datos = np.loadtxt(ARCHIVO_DATOS)
        frecuencias_crudas = datos[:, 0]
        amplitudes_crudas = np.abs(datos[:, 1])

        # Ventana activa para limpiar ruido de desfasamiento
        mascara = frecuencias_crudas >= 10
        frecuencias = frecuencias_crudas[mascara]
        amplitudes = amplitudes_crudas[mascara]

        if len(amplitudes) == 0: return None, None, None, 0

        amp_max = np.max(amplitudes)
        idx_max = np.argmax(amplitudes)
        if amp_max <= 0: return None, None, None, 0
        
        nivel_fc = amp_max / np.sqrt(2)

        fl_real, fh_real = None, None

        # 1. Buscar fL (Frecuencia inferior): desde el inicio hasta el pico máximo
        for i in range(idx_max):
            if amplitudes[i] <= nivel_fc <= amplitudes[i+1]:
                f1, f2 = frecuencias[i], frecuencias[i+1]
                a1, a2 = amplitudes[i], amplitudes[i+1]
                fl_real = f1 + (nivel_fc - a1) * (f2 - f1) / (a2 - a1)
                break

        # 2. Buscar fH (Frecuencia superior): desde el pico máximo hasta el final
        for i in range(idx_max, len(amplitudes) - 1):
            if amplitudes[i] >= nivel_fc >= amplitudes[i+1]:
                f1, f2 = frecuencias[i], frecuencias[i+1]
                a1, a2 = amplitudes[i], amplitudes[i+1]
                fh_real = f1 + (nivel_fc - a1) * (f2 - f1) / (a2 - a1)
                break

        # Respaldos de seguridad
        if fl_real is None and idx_max > 0:
            idx_l = np.argmin(np.abs(amplitudes[:idx_max] - nivel_fc))
            fl_real = frecuencias[idx_l]
        if fh_real is None:
            idx_h = np.argmin(np.abs(amplitudes[idx_max:] - nivel_fc)) + idx_max
            fh_real = frecuencias[idx_h]

        # Medición de pendientes (promedio de atenuación en banda baja y alta)
        idx_fl = np.argmin(np.abs(frecuencias - fl_real))
        idx_fh = np.argmin(np.abs(frecuencias - fh_real))
        
        f_ref_baja = fl_real / 10.0
        f_ref_alta = fh_real * 10.0
        
        idx_ref_baja = np.argmin(np.abs(frecuencias - f_ref_baja))
        idx_ref_alta = np.argmin(np.abs(frecuencias - f_ref_alta))

        v_fl = amplitudes[idx_fl] + 1e-12
        v_fh = amplitudes[idx_fh] + 1e-12
        v_ref_baja = amplitudes[idx_ref_baja] + 1e-12
        v_ref_alta = amplitudes[idx_ref_alta] + 1e-12

        pend_baja = abs(20 * np.log10(v_fl) - 20 * np.log10(v_ref_baja))
        pend_alta = abs(20 * np.log10(v_fh) - 20 * np.log10(v_ref_alta))
        pend_promedio = (pend_baja + pend_alta) / 2.0

        return float(fl_real), float(fh_real), float(amp_max), float(pend_promedio)
    except:
        return None, None, None, 0

# ============================================================
# FITNESS MULTIOBJETIVO REFACTORIZADO PARA PASABANDA
# ============================================================
def fitness(individuo):
    try:
        actualizar_circuito(individuo)
        if not ejecutar_spice():
            return 1e-6, None, None, None, 0

        fl, fh, amp, pend = obtener_metricas()
        if fl is None or fh is None or amp is None:
            return 1e-6, None, None, None, 0

        # Filtro de seguridad para evitar soluciones vacías
        if amp < 0.5:
            return 1e-6, fl, fh, amp, pend

        # Penalización severa si las frecuencias se cruzan
        penalizacion = 0.0
        if fl >= fh:
            penalizacion = 5.0

        f_fl = 1.0 / (1.0 + abs(fl - FL_OBJETIVO)/FL_OBJETIVO)
        f_fh = 1.0 / (1.0 + abs(fh - FH_OBJETIVO)/FH_OBJETIVO)
        f_amp = 1.0 / (1.0 + abs(amp - AMPLITUD_OBJETIVO)/AMPLITUD_OBJETIVO)
        f_pend = 1.0 / (1.0 + abs(pend - PENDIENTE_OBJETIVO)/PENDIENTE_OBJETIVO)
        
        # Ponderación balanceada considerando ambos puntos del rango
        fit_ponderado = float((f_fl * 0.2 + f_fh * 0.2) + f_amp * 0.3 + f_pend * 0.3) - penalizacion
        return max(1e-6, fit_ponderado), fl, fh, amp, pend
    except:
        return 1e-6, None, None, None, 0

# ============================================================
# MÉTODOS DEL ALGORITMO GENÉTICO
# ============================================================
def crear_individuo():
    return [random.randint(0, (len(SERIE_E12) if c["tipo"]=="R" else len(SERIE_E6))-1) for c in COMPONENTES_AG]

def seleccion_torneo(poblacion, fitnesses, k=3):
    participantes = random.sample(list(zip(poblacion, fitnesses)), k)
    participantes.sort(key=lambda x: x[1], reverse=True)
    return participantes[0][0][:]

def ejecutar_AG():
    if NUM_PARAMETROS == 0:
        print("Error: No se detectaron componentes variables en el archivo .cir")
        return

    poblacion = [crear_individuo() for _ in range(TAM_POBLACION)]
    
    mejor_global = None
    mejor_fit = -1.0
    metricas_optimas = (None, None, None, 0)

    print(f"\nIniciando evolución para {NUM_GENERACIONES} generaciones...")

    for gen in range(NUM_GENERACIONES):
        res = [fitness(ind) for ind in poblacion]
        fitnesses = [r[0] for r in res]
        
        idx_best = int(np.argmax(fitnesses))
        if fitnesses[idx_best] > mejor_fit:
            mejor_fit = fitnesses[idx_best]
            mejor_global = poblacion[idx_best][:]
            metricas_optimas = (res[idx_best][1], res[idx_best][2], res[idx_best][3], res[idx_best][4])

        fl_gen = res[idx_best][1]
        fh_gen = res[idx_best][2]
        amp_gen = res[idx_best][3]
        pend_gen = res[idx_best][4]
        
        txt_fl = f"{fl_gen:.1f}Hz" if fl_gen is not None else "Error"
        txt_fh = f"{fh_gen:.1f}Hz" if fh_gen is not None else "Error"
        txt_amp = f"{amp_gen:.2f}V" if amp_gen is not None else "Error"

        print(f"Gen {gen+1:02d}: Fit {fitnesses[idx_best]:.4f} | Rango: [{txt_fl} a {txt_fh}] | Amp {txt_amp} | Pend {pend_gen:.1f}dB/dec")

        # Elitismo
        indices = np.argsort(fitnesses)[::-1]
        nueva_pob = [poblacion[i][:] for i in indices[:ELIMITISMO if 'ELIMITISMO' in locals() else ELITISMO]]

        # Reproducción segura para N-parámetros
        while len(nueva_pob) < TAM_POBLACION:
            p1 = seleccion_torneo(poblacion, fitnesses)
            p2 = seleccion_torneo(poblacion, fitnesses)
            
            if random.random() < PROB_CRUCE and NUM_PARAMETROS > 1:
                pto = random.randint(1, NUM_PARAMETROS - 1)
                h1, h2 = p1[:pto] + p2[pto:], p2[:pto] + p1[pto:]
            else:
                h1, h2 = p1[:], p2[:]
            
            for h in [h1, h2]:
                for i in range(NUM_PARAMETROS):
                    if random.random() < PROB_MUTACION:
                        lim = len(SERIE_E12) if COMPONENTES_AG[i]["tipo"]=="R" else len(SERIE_E6)
                        cambio = random.choice([-1, 1])
                        h[i] = max(0, min(lim - 1, h[i] + cambio))
                nueva_pob.append(h)

        poblacion = nueva_pob[:TAM_POBLACION]

    # Re-escribir la netlist con la mejor solución
    actualizar_circuito(mejor_global)
    ejecutar_spice()

    print("\n================ MEJOR SOLUCION FINAL DE PASABANDA ================")
    componentes_json = {}
    for i, comp in enumerate(COMPONENTES_AG):
        lista = SERIE_E12 if comp["tipo"] == "R" else SERIE_E6
        val_encontrado = lista[mejor_global[i]]
        print(f"{comp['nombre']} = {valor_spice(val_encontrado)}")
        componentes_json[comp["nombre"]] = {
            "valor_flotante": val_encontrado,
            "texto_spice": valor_spice(val_encontrado),
            "serie_comercial": "E12" if comp["tipo"] == "R" else "E6"
        }

    fl_final, fh_final = metricas_optimas[0], metricas_optimas[1]
    txt_fl_f = f"{fl_final:.2f} Hz" if fl_final else "Error"
    txt_fh_f = f"{fh_final:.2f} Hz" if fh_final else "Error"
    print(f"Rango FINAL = [{txt_fl_f} a {txt_fh_f}]")
    if fl_final and fh_final:
        print(f"Ancho de Banda Real = {fh_final - fl_final:.2f} Hz")

    # Exportación JSON avanzada estructurada para intercambio
    ruta_json = "mejor_solucion.json"
    datos_intercambio = {
        "configuracion": {
            "archivo_netlist": ARCHIVO_CIR,
            "frecuencia_inferior_objetivo_hz": FL_OBJETIVO,
            "frecuencia_superior_objetivo_hz": FH_OBJETIVO,
            "tamano_poblacion": TAM_POBLACION,
            "total_generaciones": NUM_GENERACIONES
        },
        "resultado_optimo": {
            "fl_final_hz": round(fl_final, 2) if fl_final else None,
            "fh_final_hz": round(fh_final, 2) if fh_final else None,
            "ancho_banda_hz": round(fh_final - fl_final, 2) if (fh_final and fl_final) else None,
            "amplitud_maxima_v": round(metricas_optimas[2], 2) if metricas_optimas[2] else None,
            "pendiente_db_dec": round(metricas_optimas[3], 2),
            "fitness_final": round(mejor_fit, 4),
            "componentes": componentes_json
        }
    }
    
    Path(ruta_json).write_text(json.dumps(datos_intercambio, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"\nArchivo de intercambio '{ruta_json}' guardado con éxito por rangos.")

if __name__ == "__main__":
    ejecutar_AG()