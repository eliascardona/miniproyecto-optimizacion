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
# OBJETIVO DE DISEÑO
# ============================================================
FC_OBJETIVO = 1000        # 1000 Hz
AMPLITUD_OBJETIVO = 5     # Amplitud esperada
PENDIENTE_OBJETIVO = 40   # Pendiente buscada

# ============================================================
# PARÁMETROS DEL ALGORITMO GENÉTICO
# ============================================================
TAM_POBLACION = 20
NUM_GENERACIONES = 30
PROB_CRUCE = 0.8
PROB_MUTACION = 0.2
ELITISMO = 2

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
    texto = Path(ARCHIVO_CIR).read_text()
    detectados = []
    
    # Filtro estricto para ignorar resistencias fijas de fuente y carga
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
    texto = Path(ARCHIVO_CIR).read_text()
    lineas = texto.splitlines()
    
    for i, comp in enumerate(COMPONENTES_AG):
        lista = SERIE_E12 if comp["tipo"] == "R" else SERIE_E6
        nuevo_valor = valor_spice(lista[individuo[i]])
        
        for idx, linea in enumerate(lineas):
            linea_limpia = linea.strip()
            if linea_limpia.startswith(comp["nombre"]) and re.match(rf"^{comp['nombre']}\s+", linea_limpia):
                partes = linea_limpia.split()
                partes[-1] = nuevo_valor  # Cambia con precisión la última columna de la netlist
                lineas[idx] = " ".join(partes)
                break
                
    Path(ARCHIVO_CIR).write_text("\n".join(lineas))

def ejecutar_spice():
    resultado = subprocess.run([NGSPICE_EXE, "-b", ARCHIVO_CIR], capture_output=True, text=True)
    if resultado.returncode != 0:
        return False
    return True

# ============================================================
# OBTENER METRICAS CON TU INTERPOLACIÓN REAL
# ============================================================
def obtener_metricas():
    try:
        datos = np.loadtxt(ARCHIVO_DATOS)
        frecuencias = datos[:, 0]
        amplitudes = datos[:, 1]  # vm(1002) entrega directamente magnitud lineal

        amp_max = np.max(amplitudes)
        if amp_max <= 0: return None, None, 0
        nivel_fc = amp_max / np.sqrt(2)

        # Tu algoritmo original de interpolación lineal exacta
        fc_real = None
        for i in range(len(amplitudes) - 1):
            if (amplitudes[i] <= nivel_fc <= amplitudes[i+1]) or (amplitudes[i] >= nivel_fc >= amplitudes[i+1]):
                f1, f2 = frecuencias[i], frecuencias[i+1]
                a1, a2 = amplitudes[i], amplitudes[i+1]
                fc_real = f1 + (nivel_fc - a1) * (f2 - f1) / (a2 - a1)
                break

        if fc_real is None:
            idx = np.argmin(np.abs(amplitudes - nivel_fc))
            fc_real = frecuencias[idx]

        # Medición de pendiente adaptada para evitar valores asintóticos erróneos
        f_baja = fc_real / 10.0
        idx_fc = np.argmin(np.abs(frecuencias - fc_real))
        idx_baja = np.argmin(np.abs(frecuencias - f_baja))
        
        v_fc = amplitudes[idx_fc] + 1e-12
        v_baja = amplitudes[idx_baja] + 1e-12
        
        pend = abs(20 * np.log10(v_fc) - 20 * np.log10(v_baja))
        
        return float(fc_real), float(amp_max), float(pend)
    except: 
        return None, None, 0

# ============================================================
# FITNESS MULTIOBJETIVO REFACTORIZADO
# ============================================================
def fitness(individuo):
    try:
        actualizar_circuito(individuo)
        if not ejecutar_spice():
            return 1e-6, None, None, 0

        fc, amp, pend = obtener_metricas()
        if fc is None or amp is None:
            return 1e-6, None, None, 0

        # Filtro de seguridad para evitar soluciones con banda de paso colapsada
        if amp < 0.5:
            return 1e-6, fc, amp, pend

        f_fc = 1.0 / (1.0 + abs(fc - FC_OBJETIVO)/FC_OBJETIVO)
        f_amp = 1.0 / (1.0 + abs(amp - AMPLITUD_OBJETIVO)/AMPLITUD_OBJETIVO)
        f_pend = 1.0 / (1.0 + abs(pend - PENDIENTE_OBJETIVO)/PENDIENTE_OBJETIVO)
        
        fit_ponderado = float(f_fc * 0.3 + f_amp * 0.4 + f_pend * 0.3)
        return fit_ponderado, fc, amp, pend
    except:
        return 1e-6, None, None, 0

# ============================================================
# MÉTODOS DEL ALGORITMO GENÉTICO REESCRITOS PARA N-COMPONENTES
# ============================================================
def crear_individuo():
    # Genera los índices correctos mapeando dinámicamente si es R o C
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
    metricas_optimas = (None, None, 0)

    print(f"\nIniciando evolución para {NUM_GENERACIONES} generaciones...")

    for gen in range(NUM_GENERACIONES):
        res = [fitness(ind) for ind in poblacion]
        fitnesses = [r[0] for r in res]
        
        idx_best = int(np.argmax(fitnesses))
        if fitnesses[idx_best] > mejor_fit:
            mejor_fit = fitnesses[idx_best]
            mejor_global = poblacion[idx_best][:]
            metricas_optimas = (res[idx_best][1], res[idx_best][2], res[idx_best][3])

        fc_gen = res[idx_best][1]
        amp_gen = res[idx_best][2]
        pend_gen = res[idx_best][3]
        
        txt_fc = f"{fc_gen:.1f}Hz" if fc_gen is not None else "Error"
        txt_amp = f"{amp_gen:.2f}V" if amp_gen is not None else "Error"

        print(f"Gen {gen+1}: Fit {fitnesses[idx_best]:.4f} | fc {txt_fc} | Amp {txt_amp} | Pend {pend_gen:.1f}dB/dec")

        # Elitismo
        indices = np.argsort(fitnesses)[::-1]
        nueva_pob = [poblacion[i][:] for i in indices[:ELITISMO]]

        # Reproducción (Cruce y Mutación seguros para N-parámetros)
        while len(nueva_pob) < TAM_POBLACION:
            p1 = seleccion_torneo(poblacion, fitnesses)
            p2 = seleccion_torneo(poblacion, fitnesses)
            
            # Cruzamiento por punto de corte dinámico
            if random.random() < PROB_CRUCE and NUM_PARAMETROS > 1:
                pto = random.randint(1, NUM_PARAMETROS - 1)
                h1, h2 = p1[:pto] + p2[pto:], p2[:pto] + p1[pto:]
            else:
                h1, h2 = p1[:], p2[:]
            
            # Mutación indexada individualmente según límites de su propia serie comercial
            for h in [h1, h2]:
                for i in range(NUM_PARAMETROS):
                    if random.random() < PROB_MUTACION:
                        lim = len(SERIE_E12) if COMPONENTES_AG[i]["tipo"]=="R" else len(SERIE_E6)
                        cambio = random.choice([-1, 1])
                        h[i] = max(0, min(lim - 1, h[i] + cambio))
                nueva_pob.append(h)

        poblacion = nueva_pob[:TAM_POBLACION]

    # Re-escribir la netlist con los valores óptimos definitivos hallados
    actualizar_circuito(mejor_global)
    ejecutar_spice()

    print("\n================ MEJOR SOLUCION FINAL ================")
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

    print(f"fc FINAL = {f'{metricas_optimas[0]:.2f} Hz' if metricas_optimas[0] else 'Error'}")

    # Exportación a JSON limpia para guardar el registro real
    ruta_json = "mejor_solucion.json"
    datos_intercambio = {
        "configuracion": {
            "archivo_netlist": ARCHIVO_CIR,
            "frecuencia_objetivo_hz": FC_OBJETIVO,
            "tamano_poblacion": TAM_POBLACION,
            "total_generaciones": NUM_GENERACIONES
        },
        "resultado_optimo": {
            "frecuencia_corte_final_hz": round(metricas_optimas[0], 2) if metricas_optimas[0] else None,
            "amplitud_maxima_v": round(metricas_optimas[1], 2) if metricas_optimas[1] else None,
            "pendiente_db_dec": round(metricas_optimas[2], 2),
            "fitness_final": round(mejor_fit, 4),
            "componentes": componentes_json
        }
    }
    
    Path(ruta_json).write_text(json.dumps(datos_intercambio, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"\nArchivo de intercambio '{ruta_json}' guardado con éxito.")

if __name__ == "__main__":
    ejecutar_AG()