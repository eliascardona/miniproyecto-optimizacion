"""
Fase 0, de punta a punta: IndividualOptimizationController.optimize() con el ngspice
SIMULADO. Verifica que, con cualquier algoritmo/filtro, (1) la respuesta es válida,
(2) la plantilla del constants_repository queda intacta y (3) no sobran directorios temporales.
"""
import base64
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import app.constants_repository as repositorio
from app.constants_repository import ConstantsRepository
from app.controller.individual_optimization_controller import IndividualOptimizationController

FALSO = [sys.executable, str(Path(__file__).with_name("_ngspice_falso.py"))]
ENTORNO = {"v_fuente": 5, "r_fuente": 500, "r_carga": 500}
BARRIDO = {"f_inicial": 1, "f_final": 100000}

PARAMS = {
    "algoritmo_genetico": [("tam_poblacion", 4), ("num_generaciones", 2), ("prob_cruce", 0.8),
                           ("prob_mutacion", 0.3), ("elitismo", 1), ("torneo_k", 2)],
    "enjambre_particulas": [("num_particulas", 4), ("num_iteraciones", 2), ("w", 0.7), ("c1", 1.5), ("c2", 1.5)],
    "optimizacion_bayesiana": [("n_iniciales", 3), ("n_iteraciones", 2), ("xi", 0.01),
                               ("n_candidatos", 20), ("n_restarts", 2), ("semilla", 42)],
    "recocido_simulado": [("temp_inicial", 2.0), ("temp_final", 1.0), ("factor_enfriamiento", 0.6),
                          ("iteraciones_por_temp", 2)],
}
FRECUENCIAS_AVANZADO = {
    "pasa_altas": [("f_aten", 1000), ("f_paso", 10000)],
    "pasa_bajas": [("f_paso", 100), ("f_aten", 1000)],
    "pasa_banda": [("f_aten_1", 10), ("f_paso_1", 100), ("f_paso_2", 1000), ("f_aten_2", 10000)],
    "rechaza_banda": [("f_paso_1", 10), ("f_aten_1", 100), ("f_aten_2", 500), ("f_paso_2", 10000)],
}


def _kv(pares):
    return [{"clave": k, "valor": v} for k, v in pares]


def _peticion(filtro, algoritmo):
    return SimpleNamespace(filtro=filtro, algoritmo=algoritmo, entorno={
        "modo": "AVANZADO", "entorno": ENTORNO, "barrido_ac": BARRIDO,
        "parametros_optimizador": _kv(PARAMS[algoritmo]), "frecuencias": _kv(FRECUENCIAS_AVANZADO[filtro])})


def _huella(filtro):
    carpeta = ConstantsRepository.directorio_plantilla_de(filtro)
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in carpeta.iterdir() if p.is_file()}


def _temporales():
    return {p.name for p in Path(tempfile.gettempdir()).glob("opt_*")}


CASOS = [("pasa_altas", "algoritmo_genetico"), ("pasa_bajas", "algoritmo_genetico"),
         ("pasa_banda", "algoritmo_genetico"), ("rechaza_banda", "algoritmo_genetico"),
         ("pasa_altas", "enjambre_particulas"), ("pasa_bajas", "optimizacion_bayesiana"),
         ("pasa_banda", "recocido_simulado"), ("rechaza_banda", "recocido_simulado")]


class TestControladorDePuntaAPunta(unittest.TestCase):

    def setUp(self):
        self._ngspice_original = repositorio.NGSPICE_EXE
        repositorio.NGSPICE_EXE = FALSO
        self.controlador = IndividualOptimizationController()

    def tearDown(self):
        repositorio.NGSPICE_EXE = self._ngspice_original

    def test_respuesta_valida_plantilla_intacta_y_sin_temporales_huerfanos(self):
        for filtro, algoritmo in CASOS:
            with self.subTest(filtro=filtro, algoritmo=algoritmo):
                huella, temporales = _huella(filtro), _temporales()
                respuesta = self.controlador.optimize(_peticion(filtro, algoritmo))

                self.assertGreater(respuesta.fitness, 0.0)
                self.assertTrue(respuesta.componentes_optimizados)
                self.assertTrue(base64.b64decode(respuesta.grafica_png_base64).startswith(b"\x89PNG"))
                self.assertEqual(hasattr(respuesta, "tiempo_ejecucion_s"), algoritmo == "optimizacion_bayesiana")
                self.assertEqual(huella, _huella(filtro), "la plantilla del repositorio fue modificada")
                self.assertEqual(temporales, _temporales(), "quedó un directorio temporal sin borrar")

    def test_todos_los_servicios_del_mapa_se_instancian_y_limpian(self):
        temporales = _temporales()
        for clave, clase in IndividualOptimizationController.SERVICE_MAP.items():
            with self.subTest(clave=clave):
                servicio = clase()
                self.assertTrue(Path(servicio.constants_repository.get_directorio_trabajo()).is_dir())
                servicio.constants_repository.cleanup()
        self.assertEqual(len(IndividualOptimizationController.SERVICE_MAP), 16)
        self.assertEqual(temporales, _temporales())

    def test_el_directorio_temporal_se_borra_aunque_la_peticion_falle(self):
        temporales = _temporales()
        peticion = _peticion("pasa_altas", "algoritmo_genetico")
        peticion.entorno["parametros_optimizador"] = _kv(PARAMS["enjambre_particulas"])   # claves de otro algoritmo
        with self.assertRaises(Exception):
            self.controlador.optimize(peticion)
        self.assertEqual(temporales, _temporales())


if __name__ == "__main__":
    unittest.main()