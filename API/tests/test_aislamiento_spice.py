"""
Fase 0: ngspice trabaja dentro del directorio de la corrida. Se usa un ngspice
SIMULADO (tests/_ngspice_falso.py) que, como el real, resuelve las rutas
relativas de `wrdata` contra el cwd del proceso.
"""
import hashlib
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

import numpy as np

from app.constants_repository import ConstantsRepository
from app.preparation_service.pasa_altas_service import PasaAltasPreparationService
from app.utils.spice_runner import actualizar_circuito, ejecutar_spice

FALSO = [sys.executable, str(Path(__file__).with_name("_ngspice_falso.py"))]
ENTORNO = dict(vs_valor=5.0, vpp_valor=15.0, vnn_valor=-15.0, rs_valor=500.0, rl_valor=500.0,
               f_inicial=1.0, f_final=100000.0)


def _simular(servicio, individuo) -> np.ndarray:
    """Misma secuencia que el fitness: escribir el .cir, correr SPICE, leer datos."""
    repo = servicio.constants_repository
    comps = servicio.extract_components()
    actualizar_circuito(individuo, comps, repo.get_archivo_cir(), **ENTORNO)
    assert ejecutar_spice(FALSO, repo.get_archivo_cir())
    return np.loadtxt(repo.get_archivo_datos())


def _individuo(offset: int, n: int) -> list:
    return [(offset + 3 * k) % 25 for k in range(n)]


class TestAislamientoSpice(unittest.TestCase):

    def setUp(self):
        self.servicios = []

    def tearDown(self):
        for s in self.servicios:
            s.constants_repository.cleanup()

    def _servicio(self):
        s = PasaAltasPreparationService()
        self.servicios.append(s)
        return s

    def test_la_salida_de_ngspice_cae_en_el_directorio_de_trabajo_y_no_en_el_cwd(self):
        servicio = self._servicio()
        plantilla = ConstantsRepository.directorio_plantilla_de("pasa_altas")
        antes_plantilla = {p.name: p.stat().st_mtime_ns for p in plantilla.iterdir()}
        cwd_original = os.getcwd()
        with tempfile.TemporaryDirectory() as otro_cwd:
            os.chdir(otro_cwd)                            # p. ej. la carpeta desde la que se lanzó uvicorn
            try:
                _simular(servicio, _individuo(0, len(servicio.extract_components())))
                self.assertEqual(os.listdir(otro_cwd), [], "ngspice escribió en el cwd del proceso")
            finally:
                os.chdir(cwd_original)
        trabajo = Path(servicio.constants_repository.get_directorio_trabajo())
        self.assertTrue((trabajo / "datos_filtro.txt").is_file())
        self.assertTrue((trabajo / "simulacion.raw").is_file())
        self.assertEqual(antes_plantilla, {p.name: p.stat().st_mtime_ns for p in plantilla.iterdir()},
                         "la plantilla del repositorio fue modificada")

    def test_cada_circuito_simulado_produce_una_curva_distinta_y_se_lee_la_ultima(self):
        servicio = self._servicio()
        n = len(servicio.extract_components())
        curvas = [_simular(servicio, _individuo(k, n)) for k in range(5)]
        for a in range(len(curvas)):
            for b in range(a + 1, len(curvas)):
                self.assertFalse(np.allclose(curvas[a], curvas[b]),
                                 f"los individuos {a} y {b} dieron la misma curva (dato viejo)")

    def test_el_fitness_distingue_individuos(self):
        """Con datos viejos todos los individuos tendrían el MISMO fitness; con datos frescos, no."""
        servicio = self._servicio()
        comps = servicio.extract_components()
        cfg = servicio.validate_json_config({
            "modo": "AVANZADO", "entorno": {"v_fuente": 5, "r_fuente": 500, "r_carga": 500},
            "barrido_ac": {"f_inicial": 1, "f_final": 100000},
            "parametros_optimizador": [{"clave": "tam_poblacion", "valor": 4}, {"clave": "num_generaciones", "valor": 2},
                                       {"clave": "prob_cruce", "valor": 0.8}, {"clave": "prob_mutacion", "valor": 0.3},
                                       {"clave": "elitismo", "valor": 1}, {"clave": "torneo_k", "valor": 2}],
            "frecuencias": [{"clave": "f_aten", "valor": 1000}, {"clave": "f_paso", "valor": 10000}],
        })
        ctx = servicio._build_run_context(cfg)
        servicio.constants_repository.ngspice_exe = FALSO
        fitnesses = {round(servicio._evaluar(_individuo(k, len(comps)), ctx, comps)[0], 9) for k in range(8)}
        self.assertGreater(len(fitnesses), 1, f"todos los individuos dieron el mismo fitness: {fitnesses}")

    def test_peticiones_simultaneas_no_se_pisan(self):
        hilos_n = 6
        servicios = [self._servicio() for _ in range(hilos_n)]
        n = len(servicios[0].extract_components())
        esperado = [_simular(self._servicio(), _individuo(k, n)) for k in range(hilos_n)]   # referencia secuencial

        resultados, errores = [None] * hilos_n, []
        barrera = threading.Barrier(hilos_n)

        def corrida(k):
            try:
                barrera.wait()
                for _ in range(3):                         # varias evaluaciones seguidas, como un optimizador
                    resultados[k] = _simular(servicios[k], _individuo(k, n))
            except Exception as e:                         # pragma: no cover
                errores.append(e)

        hilos = [threading.Thread(target=corrida, args=(k,)) for k in range(hilos_n)]
        [h.start() for h in hilos]
        [h.join() for h in hilos]

        self.assertEqual(errores, [])
        for k in range(hilos_n):
            self.assertTrue(np.allclose(resultados[k], esperado[k]), f"la corrida {k} leyó datos de otra petición")

    def test_ejecutar_spice_devuelve_false_si_ngspice_falla(self):
        servicio = self._servicio()
        cir = Path(servicio.constants_repository.get_archivo_cir())
        cir.write_text("* netlist sin .AC ni wrdata")
        self.assertFalse(ejecutar_spice(FALSO, str(cir)))


if __name__ == "__main__":
    unittest.main()