"""
Worker con interfaz estilo Keras que envuelve el Algoritmo Genetico real.

Equivalencias:
  Keras:                              AG (algoritmo.py):
    model.compile(optimizer,loss,...)   compile() -> carga configuracion
    model.fit(X, y, epochs)             fit() -> ciclo evolutivo
    model.evaluate(X_test, y_test)      evaluate() -> fitness final
    model.predict(X_test)               predict() -> simulacion + resultado

Uso como clase (import):
  worker = GeneticWorker()
  worker.compile(config=dict)     # o config_path="config.json"
  history = worker.fit()          # retorna historial de fitness
  metrics = worker.evaluate()     # retorna metricas detalladas
  result = worker.predict()       # retorna resultado completo

Uso como script (subprocess):
  python ejemplo_worker.py        # lee config.json, escribe resultado.json
"""

import random
import subprocess
import sys
import base64
import numpy as np
import re
import json
import os
from pathlib import Path

# Se reemplaza por script_runner.py antes de ejecutar como subprocess
NGSPICE_EXE = r"C:\Users\luis_\Desktop\Spice64\bin\ngspice.exe"


class GeneticWorker:
    """
    Worker que envuelve el AG real de algoritmo.py con interfaz Keras.
    Todas las constantes de diseno y funciones del script original se
    mantienen intactas, solo se convierten de modulos globales a atributos
    y metodos de instancia.
    """

    # Series comerciales (constantes de clase: iguales para todas las instancias)
    SERIE_E6 = sorted([
        round(b * (10 ** d), 12)
        for d in range(-9, -5)
        for b in [1.0, 1.5, 2.2, 3.3, 4.7, 6.8]
    ])
    SERIE_E12 = sorted([
        round(b * (10 ** d), 12)
        for d in range(1, 6)
        for b in [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]
    ])

    PENDIENTE_OBJETIVO_FC = 80.0
    PENDIENTE_OBJETIVO_PASO_ATEN = 80.0

    def __init__(self, workspace_dir="."):
        self.workspace_dir = Path(workspace_dir)

        # Configuracion (se setea en compile())
        self.config = None
        self.MODO = None
        self.VS_VALOR = None
        self.VPP_VALOR = None
        self.VNN_VALOR = None
        self.RS_VALOR = None
        self.RL_VALOR = None
        self.F_INICIAL = None
        self.F_FINAL = None
        self.TAM_POBLACION = None
        self.NUM_GENERACIONES = None
        self.PROB_CRUCE = None
        self.PROB_MUTACION = None
        self.ELITISMO = None
        self.TORNEO_K = None
        self.FC_OBJETIVO = None
        self.F_PASO = None
        self.F_ATEN = None
        self.AMP_PASO_OBJETIVO = None
        self.AMP_ATEN_OBJETIVO = None
        self.ngspice_path = NGSPICE_EXE

        self.COMPONENTES_AG = []
        self.NUM_PARAMETROS = 0

        self.mejor_global = None
        self.mejor_fit = -1.0
        self.history = {"fitness": []}

    # ------------------------------------------------------------------
    # Metodos auxiliares (del script original)
    # ------------------------------------------------------------------

    @staticmethod
    def _buscar_etiqueta(lista, etiqueta):
        for item in lista:
            if item.get("clave") == etiqueta:
                return item.get("valor")
        return None

    def _extraer_componentes(self):
        """
        Lee filtro.cir y extrae resistencias y capacitores optimizables.
        Excluye componentes fijos: RS, RL, VS, VPP, VNN.
        """
        texto = Path(self.workspace_dir / "filtro.cir").read_text()
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

    @staticmethod
    def _valor_spice(v):
        return re.sub(r'e([+-])0', r'e\1', f"{v:.1e}")

    @staticmethod
    def _valor_frecuencia(v):
        return str(int(v)) if float(v).is_integer() else str(v)

    def _actualizar_circuito(self, individuo):
        """Escribe el .cir con los valores del individuo + parametros fijos."""
        path_cir = self.workspace_dir / "filtro.cir"
        texto = path_cir.read_text()
        lineas = texto.splitlines()

        for i, comp in enumerate(self.COMPONENTES_AG):
            lista = self.SERIE_E12 if comp["tipo"] == "R" else self.SERIE_E6
            nuevo_valor = self._valor_spice(lista[individuo[i]])
            for idx, linea in enumerate(lineas):
                if linea.strip().startswith(comp["nombre"] + " "):
                    partes = linea.split()
                    partes[-1] = nuevo_valor
                    lineas[idx] = " ".join(partes)
                    break

        for i, linea in enumerate(lineas):
            partes = linea.split()
            if not partes:
                continue
            nombre = partes[0].upper()
            if nombre == "VS":
                partes[-1] = str(self.VS_VALOR)
                lineas[i] = " ".join(partes)
            elif nombre == "VPP":
                partes[-1] = str(self.VPP_VALOR)
                lineas[i] = " ".join(partes)
            elif nombre == "VNN":
                partes[-1] = str(self.VNN_VALOR)
                lineas[i] = " ".join(partes)
            elif nombre == "RS":
                partes[-1] = str(self.RS_VALOR)
                lineas[i] = " ".join(partes)
            elif nombre == "RL":
                partes[-1] = str(self.RL_VALOR)
                lineas[i] = " ".join(partes)
            elif nombre == ".AC":
                partes[-2] = self._valor_frecuencia(self.F_INICIAL)
                partes[-1] = self._valor_frecuencia(self.F_FINAL)
                lineas[i] = " ".join(partes)

        path_cir.write_text("\n".join(lineas))

    def _ejecutar_spice(self):
        """Ejecuta ngspice en el .cir del workspace."""
        kwargs = {}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        resultado = subprocess.run(
            [self.ngspice_path, "-b", str(self.workspace_dir / "filtro.cir")],
            capture_output=True, text=True,
            cwd=str(self.workspace_dir), **kwargs
        )
        return resultado.returncode == 0

    @staticmethod
    def _db(x):
        return 20.0 * np.log10(np.maximum(x, 1e-12))

    @staticmethod
    def _calcular_f_plano(frecuencias, amplitudes):
        """
        Mide que tan ancha es la meseta de la banda de paso.
        Retorna un valor entre 0 (pico resonante angosto) y 1 (banda ancha y plana).
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

        if amp_max > 0 and idx_max > 0:
            subida = amplitudes[:idx_max + 1]
            maximo_acumulado = np.maximum.accumulate(subida)
            peor_caida = float(np.max(maximo_acumulado - subida))
            f_plano_pre = 1.0 / (1.0 + (peor_caida / amp_max) * 10.0)
        else:
            f_plano_pre = 1.0

        return min(f_plano_post, f_plano_pre)

    def _obtener_metricas_fc(self):
        """
        MODO BASICO: busca frecuencia de corte real y pendiente.
        Retorna (fc_real, amp_max, pendiente, f_plano).
        """
        path_datos = self.workspace_dir / "datos_filtro.txt"
        try:
            datos = np.loadtxt(str(path_datos))
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
            if fc_real is None:
                fc_real = frecuencias[np.argmin(np.abs(amplitudes - nivel_fc))]
            idx_fc = np.argmin(np.abs(frecuencias - fc_real))
            f_ref = fc_real / 10.0
            idx_ref = np.argmin(np.abs(frecuencias - f_ref))
            pend = abs(self._db(amplitudes[idx_fc]) - self._db(amplitudes[idx_ref]))
            f_plano = self._calcular_f_plano(frecuencias, amplitudes)
            return float(fc_real), float(amp_max), float(pend), float(f_plano)
        except Exception:
            return None, 0, 0, 0

    def _obtener_metricas_paso_aten(self):
        """
        MODO AVANZADO: evalua respuesta en F_PASO y F_ATEN.
        Retorna (amp_max, amp_paso, amp_aten, pendiente, f_plano).
        """
        path_datos = self.workspace_dir / "datos_filtro.txt"
        try:
            datos = np.loadtxt(str(path_datos))
            frecuencias = datos[:, 0]
            amplitudes = datos[:, 1]
            amp_max = np.max(amplitudes)
            log_f = np.log10(frecuencias)
            amp_paso = np.interp(np.log10(self.F_PASO), log_f, amplitudes)
            amp_aten = np.interp(np.log10(self.F_ATEN), log_f, amplitudes)
            pendiente = abs(self._db(amp_paso) - self._db(amp_aten)) / abs(np.log10(self.F_ATEN / self.F_PASO))
            f_plano = self._calcular_f_plano(frecuencias, amplitudes)
            return float(amp_max), float(amp_paso), float(amp_aten), float(pendiente), float(f_plano)
        except Exception:
            return None, 0, 0, 0, 0

    def _graficar_resultado(self, archivo_salida=None):
        """Grafica la respuesta en frecuencia del filtro optimizado."""
        if archivo_salida is None:
            archivo_salida = self.workspace_dir / "resultado_filtro.png"
        else:
            archivo_salida = Path(archivo_salida)
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("[AVISO] No se pudo graficar: falta matplotlib")
            return
        path_datos = self.workspace_dir / "datos_filtro.txt"
        try:
            datos = np.loadtxt(str(path_datos))
        except Exception as e:
            print(f"[AVISO] No se pudo leer '{path_datos}': {e}")
            return
        frecuencias = datos[:, 0]
        amplitudes = datos[:, 1]
        fig, ax = plt.subplots(figsize=(8, 5))

        if self.MODO == "BASICO":
            fc_real, amp_max, pend, _ = self._obtener_metricas_fc()
            nivel_fc = (amp_max / np.sqrt(2)) if amp_max else None
            ax.semilogx(frecuencias, amplitudes, color="#2563eb", linewidth=2, label="Respuesta simulada")
            if nivel_fc is not None:
                ax.axhline(nivel_fc, color="gray", linestyle="--", linewidth=1,
                           label=f"Nivel de corte (-3 dB) ({nivel_fc:.2f} V)")
            ax.axvline(self.FC_OBJETIVO, color="#16a34a", linestyle="--", linewidth=1,
                       label=f"Fc objetivo ({self.FC_OBJETIVO:.0f} Hz)")
            if fc_real:
                ax.axvline(fc_real, color="#dc2626", linestyle=":", linewidth=1.5,
                           label=f"Fc obtenida ({fc_real:.0f} Hz)")
            ax.set_ylabel("Amplitud (V)")
            ax.set_title("Respuesta en frecuencia del filtro optimizado (MODO BASICO)")
        else:
            ax.semilogx(frecuencias, amplitudes, color="#2563eb", linewidth=2, label="Respuesta simulada")
            ax.axhline(self.AMP_PASO_OBJETIVO, color="#16a34a", linestyle="--", linewidth=1,
                       label=f"Objetivo banda de paso ({self.AMP_PASO_OBJETIVO:.2f} V)")
            ax.axhline(self.AMP_ATEN_OBJETIVO, color="#dc2626", linestyle="--", linewidth=1,
                       label=f"Objetivo banda de atenuacion ({self.AMP_ATEN_OBJETIVO:.2f} V)")
            ax.axvline(self.F_ATEN, color="#dc2626", linestyle=":", linewidth=1.5,
                       label=f"F_ATEN ({self.F_ATEN:.0f} Hz)")
            ax.axvline(self.F_PASO, color="#16a34a", linestyle=":", linewidth=1.5,
                       label=f"F_PASO ({self.F_PASO:.0f} Hz)")
            ax.set_ylabel("Amplitud (V)")
            ax.set_title("Respuesta en frecuencia del filtro optimizado (MODO AVANZADO)")

        ax.set_xlabel("Frecuencia (Hz)")
        ax.grid(True, which="both", linestyle=":", alpha=0.5)
        ax.legend(loc="best", fontsize=8)
        fig.tight_layout()
        fig.savefig(str(archivo_salida), dpi=150)
        print(f"Grafica guardada en: {archivo_salida}")
        plt.close(fig)

    @staticmethod
    def _codificar_imagen_base64(ruta_imagen):
        """Lee un PNG y lo devuelve como string base64 (sin prefijo data:image/...)."""
        try:
            return base64.b64encode(Path(ruta_imagen).read_bytes()).decode("ascii")
        except Exception as e:
            print(f"[AVISO] No se pudo codificar la imagen: {e}")
            return None

    def _guardar_resultado_json(self, mejor_global, mejor_fit, archivo_salida=None,
                                 archivo_grafica=None):
        """
        Genera el dict resultado (analogo a resultado.json del script original).
        Si archivo_salida se especifica, escribe el JSON a disco.
        """
        if archivo_salida is None:
            archivo_salida = self.workspace_dir / "resultado.json"
        if archivo_grafica is None:
            archivo_grafica = self.workspace_dir / "resultado_filtro.png"

        componentes_optimizados = [
            {
                "nombre": comp["nombre"],
                "valor": (self.SERIE_E12 if comp["tipo"] == "R" else self.SERIE_E6)[mejor_global[i]],
            }
            for i, comp in enumerate(self.COMPONENTES_AG)
        ]

        if self.MODO == "BASICO":
            fc_real, amp_max, pend, _ = self._obtener_metricas_fc()
            frecuencias_obtenidas = [
                {"clave": "fc_obtenida", "valor": fc_real},
            ]
        else:
            amp_max, amp_paso, amp_aten, pendiente, _ = self._obtener_metricas_paso_aten()
            frecuencias_obtenidas = [
                {"clave": "amp_paso_obtenida", "valor": amp_paso},
                {"clave": "amp_aten_obtenida", "valor": amp_aten},
            ]

        resultado = {
            "fitness": mejor_fit,
            "frecuencias_obtenidas": frecuencias_obtenidas,
            "componentes_optimizados": componentes_optimizados,
            "grafica_png_base64": self._codificar_imagen_base64(str(archivo_grafica)),
        }

        Path(archivo_salida).write_text(
            json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Resultado guardado en: {archivo_salida}")
        return resultado

    # ------------------------------------------------------------------
    # Fitness (del script original)
    # ------------------------------------------------------------------

    def _fitness_fc(self, individuo):
        """MODO BASICO: fitness por Fc objetivo + pendiente + amplitud + anti-resonancia."""
        try:
            self._actualizar_circuito(individuo)
            if not self._ejecutar_spice():
                return 1e-6, None, 0, 0, 0, 0, 0, 0
            fc, amp_max, pend, f_plano = self._obtener_metricas_fc()
            if fc is None:
                return 1e-6, None, 0, 0, 0, 0, 0, 0
            if amp_max > (self.VS_VALOR * 1.01):
                return 1e-6, fc, amp_max, pend, 0, 0, f_plano, 0
            f_fc = 1.0 / (1.0 + abs(fc - self.FC_OBJETIVO) / self.FC_OBJETIVO)
            f_pend = 1.0 / (1.0 + abs(pend - self.PENDIENTE_OBJETIVO_FC) / self.PENDIENTE_OBJETIVO_FC)
            f_amp = 1.0 / (1.0 + abs(self.VS_VALOR - amp_max) / self.VS_VALOR)
            fit = (f_plano * 0.2) + (f_fc * 0.4) + (f_pend * 0.2) + (f_amp * 0.2)
            return float(fit), fc, amp_max, pend, f_fc, f_pend, f_plano, f_amp
        except Exception:
            return 1e-6, None, 0, 0, 0, 0, 0, 0

    def _fitness_paso_aten(self, individuo):
        """MODO AVANZADO: fitness por voltaje en F_PASO, F_ATEN y anti-resonancia."""
        try:
            self._actualizar_circuito(individuo)
            if not self._ejecutar_spice():
                return 1e-6, 0, 0, 0, 0, 0, 0, 0
            amp_max, amp_paso, amp_aten, pendiente, f_plano = self._obtener_metricas_paso_aten()
            if amp_max is None:
                return 1e-6, 0, 0, 0, 0, 0, 0, 0
            if amp_max > (self.VS_VALOR * 1.01):
                return 1e-6, amp_paso, amp_aten, pendiente, 0, 0, 0, 0
            error_rel_paso = abs(self.AMP_PASO_OBJETIVO - amp_paso) / self.AMP_PASO_OBJETIVO
            f_paso = 1.0 / (1.0 + (error_rel_paso ** 4) * 100.0)
            f_aten = 1.0 / (1.0 + abs(amp_aten - self.AMP_ATEN_OBJETIVO) / self.VS_VALOR)
            f_pend = 1.0 / (1.0 + abs(pendiente - self.PENDIENTE_OBJETIVO_PASO_ATEN) / self.PENDIENTE_OBJETIVO_PASO_ATEN)
            fit = (f_paso * 0.4) + (f_aten * 0.3) + (f_pend * 0.1) + (f_plano * 0.2)
            return float(fit), amp_paso, amp_aten, pendiente, f_paso, f_aten, f_pend, f_plano
        except Exception:
            return 1e-6, 0, 0, 0, 0, 0, 0, 0

    def _fitness(self, individuo):
        """Despacha a fitness_fc o fitness_paso_aten segun MODO."""
        if self.MODO == "BASICO":
            return self._fitness_fc(individuo)
        else:
            return self._fitness_paso_aten(individuo)

    # ------------------------------------------------------------------
    # Operadores geneticos (del script original)
    # ------------------------------------------------------------------

    def _crear_individuo(self):
        return [
            random.randint(0, (len(self.SERIE_E12) if c["tipo"] == "R" else len(self.SERIE_E6)) - 1)
            for c in self.COMPONENTES_AG
        ]

    def _seleccion_torneo(self, poblacion, fitnesses):
        k = min(self.TORNEO_K, len(poblacion))
        candidatos = random.sample(range(len(poblacion)), k)
        idx_mejor = max(candidatos, key=lambda i: fitnesses[i])
        return poblacion[idx_mejor]

    def _cruzar(self, p1, p2):
        if self.NUM_PARAMETROS > 1 and random.random() < self.PROB_CRUCE:
            punto = random.randint(1, self.NUM_PARAMETROS - 1)
            h1 = p1[:punto] + p2[punto:]
            h2 = p2[:punto] + p1[punto:]
        else:
            h1, h2 = p1[:], p2[:]
        return h1, h2

    def _mutar(self, individuo):
        for i in range(self.NUM_PARAMETROS):
            if random.random() < self.PROB_MUTACION:
                lim = len(self.SERIE_E12) if self.COMPONENTES_AG[i]["tipo"] == "R" else len(self.SERIE_E6)
                individuo[i] = random.randint(0, lim - 1)
        return individuo

    # ------------------------------------------------------------------
    # Impresion (del script original)
    # ------------------------------------------------------------------

    def _imprimir_encabezado(self):
        print(f"Configuracion: V_fuente={self.VS_VALOR} V | Rs={self.RS_VALOR} ohm | Rl={self.RL_VALOR} ohm")
        print(f"Barrido .AC: {self._valor_frecuencia(self.F_INICIAL)} Hz a {self._valor_frecuencia(self.F_FINAL)} Hz")
        print(f"AG: poblacion={self.TAM_POBLACION} | generaciones={self.NUM_GENERACIONES} | "
              f"elitismo={self.ELITISMO} | torneo_k={self.TORNEO_K} | "
              f"prob_cruce={self.PROB_CRUCE} | prob_mutacion={self.PROB_MUTACION}")
        if self.MODO == "BASICO":
            print(f"MODO BASICO (Fc + pendiente) | Fc objetivo={self.FC_OBJETIVO} Hz | "
                  f"Pendiente objetivo={self.PENDIENTE_OBJETIVO_FC:.1f} dB/dec")
            print(f"{'Gen':<6} | {'Fit':<6} | {'Fc (Hz)':<10} | {'Amp (V)':<8} | {'Pend (dB/dec)':<15} | "
                  f"{'f_fc':<6} | {'f_amp':<6} | {'f_pend':<6} | {'f_plano':<7}")
            print("-" * 104)
        else:
            print(f"MODO AVANZADO (paso/atenuacion) | F_ATEN={self.F_ATEN} Hz (objetivo {self.AMP_ATEN_OBJETIVO} V) | "
                  f"F_PASO={self.F_PASO} Hz (objetivo {self.AMP_PASO_OBJETIVO} V) | "
                  f"Pendiente objetivo ~ {self.PENDIENTE_OBJETIVO_PASO_ATEN:.1f} dB/dec")
            print(f"{'Gen':<6} | {'Fit':<6} | {'Amp Aten (V)':<13} | {'Amp Paso (V)':<13} | {'Pend (dB/dec)':<13} | "
                  f"{'f_aten':<6} | {'f_paso':<6} | {'f_pend':<6} | {'f_plano':<7}")
            print("-" * 110)

    def _imprimir_generacion(self, gen, fit, res_best):
        if self.MODO == "BASICO":
            fc, amp, pend, f_fc, f_pend, f_plano, f_amp = (
                res_best[1], res_best[2], res_best[3],
                res_best[4], res_best[5], res_best[6], res_best[7]
            )
            print(f"{gen+1:<6} | {fit:.4f} | {fc:10.1f} | {amp:8.2f} | {pend:15.2f} | "
                  f"{f_fc:<6.3f} | {f_amp:<6.3f} | {f_pend:<6.3f} | {f_plano:<7.3f}")
        else:
            amp_paso, amp_aten, pend = res_best[1], res_best[2], res_best[3]
            f_paso, f_aten, f_pend, f_plano = res_best[4], res_best[5], res_best[6], res_best[7]
            print(f"{gen+1:<6} | {fit:.4f} | {amp_aten:13.4f} | {amp_paso:13.3f} | {pend:13.2f} | "
                  f"{f_aten:<6.3f} | {f_paso:<6.3f} | {f_pend:<6.3f} | {f_plano:<7.3f}")

    # ------------------------------------------------------------------
    # Interfaz publica estilo Keras
    # ------------------------------------------------------------------

    def compile(self, config=None, config_path="config.json", ngspice_path=None):
        """
        Compila/Configura el modelo genetico.

        Args:
            config: dict con la configuracion (equivalente a config.json).
            config_path: ruta al JSON si config es None.
            ngspice_path: ruta al ejecutable de ngspice (opcional).
        """
        if ngspice_path is not None:
            self.ngspice_path = ngspice_path

        if config is None:
            ruta = self.workspace_dir / config_path
            try:
                cfg_raw = json.loads(ruta.read_text(encoding="utf-8"))
            except FileNotFoundError:
                sys.exit(f"[ERROR] No se encontro: {ruta}")
            except json.JSONDecodeError as e:
                sys.exit(f"[ERROR] JSON invalido: {e}")
        else:
            cfg_raw = config

        modo = str(cfg_raw.get("modo", "")).strip().upper()
        entorno = cfg_raw["entorno"]
        v_fuente = float(entorno["v_fuente"])
        r_fuente = float(entorno["r_fuente"])
        r_carga = float(entorno["r_carga"])
        parametros = cfg_raw.get("parametros_optimizador", [])
        frecuencias = cfg_raw.get("frecuencias", [])
        barrido = cfg_raw.get("barrido_ac", {})

        self.config = {
            "modo": modo,
            "v_fuente": v_fuente,
            "r_fuente": r_fuente,
            "r_carga": r_carga,
            "vpp": v_fuente + 10.0,
            "vnn": -(v_fuente + 10.0),
            "f_inicial": float(barrido["f_inicial"]),
            "f_final": float(barrido["f_final"]),
            "tam_poblacion": int(self._buscar_etiqueta(parametros, "tam_poblacion")),
            "num_generaciones": int(self._buscar_etiqueta(parametros, "num_generaciones")),
            "prob_cruce": float(self._buscar_etiqueta(parametros, "prob_cruce")),
            "prob_mutacion": float(self._buscar_etiqueta(parametros, "prob_mutacion")),
            "elitismo": int(self._buscar_etiqueta(parametros, "elitismo")),
            "torneo_k": int(self._buscar_etiqueta(parametros, "torneo_k")),
        }
        if modo == "BASICO":
            self.config["fc_objetivo"] = float(self._buscar_etiqueta(frecuencias, "fc_objetivo"))
        else:
            self.config["f_paso"] = float(self._buscar_etiqueta(frecuencias, "f_paso"))
            self.config["f_aten"] = float(self._buscar_etiqueta(frecuencias, "f_aten"))

        # Despliegue de variables de instancia
        self.MODO = modo
        self.VS_VALOR = v_fuente
        self.VPP_VALOR = v_fuente + 10.0
        self.VNN_VALOR = -(v_fuente + 10.0)
        self.RS_VALOR = r_fuente
        self.RL_VALOR = r_carga
        self.F_INICIAL = float(barrido["f_inicial"])
        self.F_FINAL = float(barrido["f_final"])
        self.TAM_POBLACION = int(self._buscar_etiqueta(parametros, "tam_poblacion"))
        self.NUM_GENERACIONES = int(self._buscar_etiqueta(parametros, "num_generaciones"))
        self.PROB_CRUCE = float(self._buscar_etiqueta(parametros, "prob_cruce"))
        self.PROB_MUTACION = float(self._buscar_etiqueta(parametros, "prob_mutacion"))
        self.ELITISMO = int(self._buscar_etiqueta(parametros, "elitismo"))
        self.TORNEO_K = int(self._buscar_etiqueta(parametros, "torneo_k"))

        if modo == "BASICO":
            self.FC_OBJETIVO = float(self._buscar_etiqueta(frecuencias, "fc_objetivo"))
            self.F_PASO = None
            self.F_ATEN = None
        else:
            self.FC_OBJETIVO = None
            self.F_PASO = float(self._buscar_etiqueta(frecuencias, "f_paso"))
            self.F_ATEN = float(self._buscar_etiqueta(frecuencias, "f_aten"))

        self.AMP_PASO_OBJETIVO = self.VS_VALOR
        self.AMP_ATEN_OBJETIVO = 0.0

        # Extraer componentes del .cir en el workspace
        self.COMPONENTES_AG = self._extraer_componentes()
        self.NUM_PARAMETROS = len(self.COMPONENTES_AG)

        self.mejor_global = None
        self.mejor_fit = -1.0
        self.history = {"fitness": []}

        print(f"[COMPILE] Worker configurado: modo={self.MODO}, "
              f"poblacion={self.TAM_POBLACION}, generaciones={self.NUM_GENERACIONES}, "
              f"componentes={self.NUM_PARAMETROS}")
        return self

    def fit(self):
        """
        Ejecuta el ciclo evolutivo del AG (equivalente a ejecutar_AG).
        Retorna un dict con el historial de fitness por generacion.
        """
        poblacion = [self._crear_individuo() for _ in range(self.TAM_POBLACION)]
        self.mejor_global = None
        self.mejor_fit = -1.0
        self.history = {"fitness": []}
        cache_fitness = {}

        def evaluar(individuo):
            clave = tuple(individuo)
            if clave not in cache_fitness:
                cache_fitness[clave] = self._fitness(individuo)
            return cache_fitness[clave]

        self._imprimir_encabezado()

        for gen in range(self.NUM_GENERACIONES):
            res = [evaluar(ind) for ind in poblacion]
            fitnesses = [r[0] for r in res]

            idx_best = int(np.argmax(fitnesses))
            if fitnesses[idx_best] > self.mejor_fit:
                self.mejor_fit = fitnesses[idx_best]
                self.mejor_global = poblacion[idx_best][:]

            self.history["fitness"].append(self.mejor_fit)
            self._imprimir_generacion(gen, fitnesses[idx_best], res[idx_best])

            indices = np.argsort(fitnesses)[::-1]
            nueva_pob = [poblacion[i][:] for i in indices[:self.ELITISMO]]

            while len(nueva_pob) < self.TAM_POBLACION:
                p1 = self._seleccion_torneo(poblacion, fitnesses)
                p2 = self._seleccion_torneo(poblacion, fitnesses)
                h1, h2 = self._cruzar(p1, p2)
                self._mutar(h1)
                nueva_pob.append(h1)
                if len(nueva_pob) < self.TAM_POBLACION:
                    self._mutar(h2)
                    nueva_pob.append(h2)

            poblacion = nueva_pob

        print(f"\n[FIT] Evolucion completada. Mejor fitness: {self.mejor_fit:.4f}")
        return self.history

    def evaluate(self):
        """
        Evalua la mejor solucion encontrada con metricas desglosadas.
        Retorna dict con fitness, componentes y metricas por sub-objetivo.
        """
        if self.mejor_global is None:
            raise RuntimeError("Debe llamar a fit() antes de evaluate()")

        res = self._fitness(self.mejor_global)
        fit = res[0]

        metricas = {
            "fitness": float(fit),
            "mejor_fit": float(self.mejor_fit),
            "modo": self.MODO,
            "componentes_optimizados": [
                {
                    "nombre": comp["nombre"],
                    "valor": (self.SERIE_E12 if comp["tipo"] == "R" else self.SERIE_E6)[self.mejor_global[i]],
                }
                for i, comp in enumerate(self.COMPONENTES_AG)
            ],
        }

        if self.MODO == "BASICO":
            _, fc, amp, pend, f_fc, f_pend, f_plano, f_amp = res
            metricas["fc_obtenida"] = fc
            metricas["amp_max"] = amp
            metricas["pendiente"] = pend
            metricas["f_fc"] = f_fc
            metricas["f_amp"] = f_amp
            metricas["f_pend"] = f_pend
            metricas["f_plano"] = f_plano
        else:
            _, amp_paso, amp_aten, pend, f_paso_sub, f_aten_sub, f_pend_sub, f_plano_sub = res
            metricas["amp_paso"] = amp_paso
            metricas["amp_aten"] = amp_aten
            metricas["pendiente"] = pend
            metricas["f_paso"] = f_paso_sub
            metricas["f_aten"] = f_aten_sub
            metricas["f_pend"] = f_pend_sub
            metricas["f_plano"] = f_plano_sub

        print(f"[EVALUATE] Fitness: {fit:.4f}")
        return metricas

    def predict(self):
        """
        Simula el mejor individuo en SPICE y genera el resultado completo.
        Retorna dict con fitness, frecuencias_obtenidas, componentes_optimizados,
        grafica_png_base64 (equivalente a resultado.json).
        """
        if self.mejor_global is None:
            raise RuntimeError("Debe llamar a fit() antes de predict()")

        self._actualizar_circuito(self.mejor_global)
        self._ejecutar_spice()

        print("[PREDICT] Simulacion final completada")
        self._graficar_resultado()
        resultado = self._guardar_resultado_json(self.mejor_global, self.mejor_fit)
        return resultado

    def run(self, config=None, config_path="config.json", ngspice_path=None):
        """
        Flujo completo: compile + fit + predict en un solo paso.
        Retorna el dict resultado (equivalente a resultado.json).
        """
        self.compile(config=config, config_path=config_path, ngspice_path=ngspice_path)
        self.fit()
        return self.predict()


if __name__ == "__main__":
    worker = GeneticWorker()
    worker.compile(config_path="config.json")
    history = worker.fit()
    result = worker.predict()
    # resultado.json ya fue escrito por _guardar_resultado_json dentro de predict()
    print("\nOptimizacion finalizada. Resultado en resultado.json")
