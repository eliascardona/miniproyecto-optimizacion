"""
Fase 2: la respuesta de /api/optimizar y el GET /api/circuitos/{filtro} entregan el esquema.
Se usa el ngspice SIMULADO (tests/_ngspice_falso.py), igual que en test_e2e_controlador.py.
"""
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np
from fastapi import HTTPException
from pydantic import ValidationError

import app.constants_repository as repositorio
from app.constants_repository import ConstantsRepository
from app.controller.circuit_schema_controller import CircuitSchemaController
from app.controller.individual_optimization_controller import IndividualOptimizationController
from app.pydantic_schema.api_response_schema.circuit_response import (
    CircuitoOptimizadoConTiempoResponse, CircuitoOptimizadoResponse)
from app.pydantic_schema.api_response_schema.esquema_schema import EsquemaCircuito, RespuestaFrecuencia
from app.routes.circuit_schema_router import circuit_schema_router
from app.utils.esquema import TopologiaNoSoportada, limpiar_cache, obtener_esquema
from app.utils.esquema import respuesta as modulo_respuesta
from app.utils.esquema.respuesta import extras_de_respuesta, leer_respuesta_frecuencia
from app.utils.genetico.commercial_series import SERIE_E6, SERIE_E12
from app.utils.spice_runner import actualizar_circuito, ejecutar_spice

FALSO = [sys.executable, str(Path(__file__).with_name("_ngspice_falso.py"))]
FILTROS = ["pasa_altas", "pasa_bajas", "pasa_banda", "rechaza_banda"]
ENTORNO_PETICION = {"v_fuente": 5, "r_fuente": 500, "r_carga": 470}
BARRIDO = {"f_inicial": 1, "f_final": 100000}
PARAMS_AG = [("tam_poblacion", 4), ("num_generaciones", 2), ("prob_cruce", 0.8),
             ("prob_mutacion", 0.3), ("elitismo", 1), ("torneo_k", 2)]
FRECUENCIAS = {
    "pasa_altas": [("f_aten", 1000), ("f_paso", 10000)],
    "pasa_bajas": [("f_paso", 100), ("f_aten", 1000)],
    "pasa_banda": [("f_aten_1", 10), ("f_paso_1", 100), ("f_paso_2", 1000), ("f_aten_2", 10000)],
    "rechaza_banda": [("f_paso_1", 10), ("f_aten_1", 100), ("f_aten_2", 500), ("f_paso_2", 10000)],
}
CAMPOS_VIEJOS = {"fitness", "frecuencias_obtenidas", "componentes_optimizados", "grafica_png_base64"}


def _kv(pares):
    return [{"clave": k, "valor": v} for k, v in pares]


def _peticion(filtro):
    return SimpleNamespace(filtro=filtro, algoritmo="algoritmo_genetico", entorno={
        "modo": "AVANZADO", "entorno": ENTORNO_PETICION, "barrido_ac": BARRIDO,
        "parametros_optimizador": _kv(PARAMS_AG), "frecuencias": _kv(FRECUENCIAS[filtro])})


def _escribir_datos(ruta: Path, filas) -> None:
    ruta.write_text("\n".join(f"{f:.8e} {v:.8e}" for f, v in filas) + "\n")


class TestLeerRespuestaFrecuencia(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_lee_dos_columnas_en_orden(self):
        _escribir_datos(self.dir / "d.txt", [(1.0, 5.0), (10.0, 4.9), (100.0, 3.5)])
        r = leer_respuesta_frecuencia(str(self.dir / "d.txt"))
        self.assertEqual(r["frecuencia_hz"], [1.0, 10.0, 100.0])
        self.assertEqual(r["vout"], [5.0, 4.9, 3.5])

    def test_acepta_una_sola_fila(self):
        _escribir_datos(self.dir / "d.txt", [(1.0, 5.0)])
        self.assertEqual(leer_respuesta_frecuencia(str(self.dir / "d.txt"))["vout"], [5.0])

    def test_recorta_cifras_y_submuestrea_conservando_extremos(self):
        f = np.logspace(0, 5, 5001)
        _escribir_datos(self.dir / "d.txt", zip(f, 1 / (1 + f)))
        r = leer_respuesta_frecuencia(str(self.dir / "d.txt"), max_puntos=100)
        self.assertLessEqual(len(r["frecuencia_hz"]), 100)
        self.assertEqual(len(r["frecuencia_hz"]), len(r["vout"]))
        self.assertAlmostEqual(r["frecuencia_hz"][0], 1.0)
        self.assertAlmostEqual(r["frecuencia_hz"][-1], 1e5, delta=1)
        self.assertEqual(r["frecuencia_hz"], sorted(r["frecuencia_hz"]))
        self.assertTrue(all(len(f"{x:.12g}") <= len(f"{x:.7g}") + 6 for x in r["vout"]))

    def test_descarta_puntos_no_finitos(self):
        (self.dir / "d.txt").write_text("1.0 5.0\n10.0 nan\n100.0 3.0\n")
        r = leer_respuesta_frecuencia(str(self.dir / "d.txt"))
        self.assertEqual(r["frecuencia_hz"], [1.0, 100.0])

    def test_archivos_invalidos(self):
        (self.dir / "una.txt").write_text("1.0\n2.0\n")
        (self.dir / "nan.txt").write_text("nan nan\n")
        for nombre in ("una.txt", "nan.txt", "no_existe.txt"):
            with self.subTest(archivo=nombre), self.assertRaises((ValueError, OSError)):
                leer_respuesta_frecuencia(str(self.dir / nombre))


class TestExtrasDeRespuesta(unittest.TestCase):
    RESULTADO = {"componentes_optimizados": [{"nombre": "C1_1", "valor": 3.3e-9}, {"nombre": "R2_2", "valor": 4700.0}]}
    ENTORNO = {"vs_valor": 7.0, "rs_valor": 330.0, "rl_valor": 1000.0, "vpp_valor": 17.0, "vnn_valor": -17.0}

    def setUp(self):
        limpiar_cache()
        self._tmp = tempfile.TemporaryDirectory()
        self.datos = Path(self._tmp.name) / "d.txt"
        _escribir_datos(self.datos, [(1.0, 5.0), (10.0, 4.0)])

    def tearDown(self):
        self._tmp.cleanup()

    def test_aplica_componentes_y_entorno(self):
        x = extras_de_respuesta("pasa_altas", self.RESULTADO, self.ENTORNO, str(self.datos))
        self.assertIsNone(x["esquema_error"])
        v = {e["nombre"]: e["valor"] for e in x["esquema"]["elementos"]}
        self.assertEqual((v["C1_1"], v["R2_2"], v["Vs"], v["Rs"], v["Rl"]), (3.3e-9, 4700.0, 7.0, 330.0, 1000.0))
        a = {p["nombre"]: p["valor"] for p in x["esquema"]["alimentacion"]}
        self.assertEqual((a["Vpp"], a["Vnn"]), (17.0, -17.0))
        self.assertEqual(x["respuesta_frecuencia"]["vout"], [5.0, 4.0])

    def test_un_componente_desconocido_no_tumba_la_curva(self):
        malo = {"componentes_optimizados": [{"nombre": "R99", "valor": 1.0}]}
        x = extras_de_respuesta("pasa_altas", malo, self.ENTORNO, str(self.datos))
        self.assertIsNone(x["esquema"])
        self.assertIn("R99", x["esquema_error"])
        self.assertIsNotNone(x["respuesta_frecuencia"])

    def test_sin_datos_no_tumba_el_esquema(self):
        x = extras_de_respuesta("pasa_altas", self.RESULTADO, self.ENTORNO, str(Path(self._tmp.name) / "no_hay.txt"))
        self.assertIsNotNone(x["esquema"])
        self.assertIsNone(x["respuesta_frecuencia"])

    def test_cualquier_excepcion_del_esquema_queda_contenida(self):
        with mock.patch.object(modulo_respuesta, "obtener_esquema", side_effect=RuntimeError("boom")):
            x = extras_de_respuesta("pasa_altas", self.RESULTADO, self.ENTORNO, str(self.datos))
        self.assertIsNone(x["esquema"])
        self.assertEqual(x["esquema_error"], "RuntimeError: boom")

    def test_entorno_incompleto_se_ignora_sin_error(self):
        x = extras_de_respuesta("pasa_altas", self.RESULTADO, {}, str(self.datos))
        self.assertIsNone(x["esquema_error"])


class TestModelosPydantic(unittest.TestCase):
    """El contrato acepta lo que genera el backend y rechaza lo que no cumple."""

    def test_los_cuatro_esquemas_validan_y_hacen_ida_y_vuelta(self):
        for filtro in FILTROS:
            with self.subTest(filtro=filtro):
                crudo = obtener_esquema(filtro)
                self.assertEqual(EsquemaCircuito.model_validate(crudo).model_dump(), crudo)

    def test_esquema_incompleto_o_mal_tipado_es_rechazado(self):
        base = obtener_esquema("pasa_altas")
        sin_limites = {k: v for k, v in base.items() if k != "limites"}
        valor_texto = copy.deepcopy(base)
        valor_texto["elementos"][0]["valor"] = "mucho"
        sin_ruta = copy.deepcopy(base)
        del sin_ruta["elementos"][1]["ruta"]
        for descripcion, malo in {"sin limites": sin_limites, "valor no numérico": valor_texto,
                                  "elemento sin ruta": sin_ruta}.items():
            with self.subTest(caso=descripcion), self.assertRaises(ValidationError):
                EsquemaCircuito.model_validate(malo)

    def test_la_respuesta_vieja_sigue_validando(self):
        vieja = {"fitness": 0.9, "frecuencias_obtenidas": [{"clave": "amp_paso_obtenida", "valor": 4.9}],
                 "componentes_optimizados": [{"nombre": "C1_1", "tipo": "C", "valor": 1e-8, "conexion_tierra": False}],
                 "grafica_png_base64": "AAAA"}
        r = CircuitoOptimizadoResponse(**vieja).model_dump()
        self.assertIsNone(r["esquema"])
        self.assertIsNone(r["esquema_error"])
        self.assertIsNone(r["respuesta_frecuencia"])
        con_tiempo = CircuitoOptimizadoConTiempoResponse(**vieja, tiempo_ejecucion_s=1.5).model_dump()
        self.assertEqual(con_tiempo["tiempo_ejecucion_s"], 1.5)

    def test_respuesta_con_los_campos_nuevos(self):
        r = CircuitoOptimizadoResponse(
            fitness=0.9, frecuencias_obtenidas=[], componentes_optimizados=[], grafica_png_base64="AAAA",
            esquema=obtener_esquema("pasa_bajas"), respuesta_frecuencia={"frecuencia_hz": [1.0], "vout": [5.0]})
        d = r.model_dump()
        self.assertEqual(d["esquema"]["filtro"], "pasa_bajas")
        self.assertEqual(RespuestaFrecuencia.model_validate(d["respuesta_frecuencia"]).vout, [5.0])


class TestControladorDeOptimizacionConEsquema(unittest.TestCase):

    def setUp(self):
        limpiar_cache()
        self._ngspice = repositorio.NGSPICE_EXE
        repositorio.NGSPICE_EXE = FALSO
        self.controlador = IndividualOptimizationController()

    def tearDown(self):
        repositorio.NGSPICE_EXE = self._ngspice

    def _optimizar(self, filtro) -> dict:
        return self.controlador.optimize(_peticion(filtro)).model_dump()

    @staticmethod
    def _curva_de_los_componentes_reportados(filtro, componentes) -> np.ndarray:
        """Simula (con el mismo ngspice simulado) EXACTAMENTE los componentes que la API reporta como óptimos."""
        with ConstantsRepository(filtro) as repo:
            comps = []
            for linea in Path(repo.get_archivo_cir()).read_text().splitlines():
                p = linea.split()
                if len(p) >= 4 and p[0][0].upper() in "RC" and p[0].upper() not in ("RS", "RL"):
                    comps.append({"nombre": p[0], "tipo": p[0][0].upper()})
            valores = {c["nombre"]: c["valor"] for c in componentes}
            individuo = []
            for c in comps:
                serie = SERIE_E12 if c["tipo"] == "R" else SERIE_E6
                individuo.append(min(range(len(serie)), key=lambda i: abs(serie[i] - valores[c["nombre"]])))
            actualizar_circuito(individuo, comps, repo.get_archivo_cir(), vs_valor=5.0, vpp_valor=15.0,
                                vnn_valor=-15.0, rs_valor=500.0, rl_valor=470.0, f_inicial=1.0, f_final=100000.0)
            assert ejecutar_spice(FALSO, repo.get_archivo_cir())
            return np.loadtxt(repo.get_archivo_datos())

    def test_cada_filtro_devuelve_esquema_y_curva_coherentes_con_el_resultado(self):
        for filtro in FILTROS:
            with self.subTest(filtro=filtro):
                r = self._optimizar(filtro)

                self.assertTrue(CAMPOS_VIEJOS <= set(r), "se perdió algún campo de la respuesta anterior")
                self.assertIsNone(r["esquema_error"])
                self.assertEqual(r["esquema"]["filtro"], filtro)

                # los valores del esquema SON los de la optimización...
                por_nombre = {e["nombre"]: e for e in r["esquema"]["elementos"]}
                for comp in r["componentes_optimizados"]:
                    self.assertEqual(por_nombre[comp["nombre"]]["valor"], comp["valor"])
                    self.assertTrue(por_nombre[comp["nombre"]]["optimizable"])
                self.assertEqual({c["nombre"] for c in r["componentes_optimizados"]},
                                 {n for n, e in por_nombre.items() if e["optimizable"]})

                # ...y los del entorno son los de la petición (Vpp = Vs + 10, como en la simulación)
                self.assertEqual((por_nombre["Vs"]["valor"], por_nombre["Rs"]["valor"], por_nombre["Rl"]["valor"]),
                                 (5.0, 500.0, 470.0))
                a = {p["nombre"]: p["valor"] for p in r["esquema"]["alimentacion"]}
                self.assertEqual((a["Vpp"], a["Vnn"]), (15.0, -15.0))

    def test_la_curva_enviada_es_la_del_circuito_optimo_y_no_la_de_la_ultima_evaluacion(self):
        for filtro in FILTROS:
            with self.subTest(filtro=filtro):
                r = self._optimizar(filtro)
                esperada = self._curva_de_los_componentes_reportados(filtro, r["componentes_optimizados"])
                f, v = r["respuesta_frecuencia"]["frecuencia_hz"], r["respuesta_frecuencia"]["vout"]
                self.assertEqual(len(f), len(esperada))
                self.assertTrue(np.allclose(f, esperada[:, 0], rtol=1e-6))
                self.assertTrue(np.allclose(v, esperada[:, 1], rtol=1e-6))

    def test_la_curva_es_la_del_optimo_con_los_cuatro_algoritmos(self):
        otros = {
            "enjambre_particulas": ("pasa_altas", [("num_particulas", 4), ("num_iteraciones", 2), ("w", 0.7),
                                                   ("c1", 1.5), ("c2", 1.5)]),
            "optimizacion_bayesiana": ("pasa_bajas", [("n_iniciales", 3), ("n_iteraciones", 2), ("xi", 0.01),
                                                      ("n_candidatos", 20), ("n_restarts", 2), ("semilla", 42)]),
            "recocido_simulado": ("pasa_banda", [("temp_inicial", 2.0), ("temp_final", 1.0),
                                                 ("factor_enfriamiento", 0.6), ("iteraciones_por_temp", 2)]),
        }
        otros_rb = ("rechaza_banda", otros["recocido_simulado"][1])          # RS tiene exportador propio en rechaza_banda
        casos = [(alg, *datos) for alg, datos in otros.items()] + [("recocido_simulado", *otros_rb)]
        for algoritmo, filtro, params in casos:
            with self.subTest(algoritmo=algoritmo, filtro=filtro):
                peticion = _peticion(filtro)
                peticion.algoritmo = algoritmo
                peticion.entorno["parametros_optimizador"] = _kv(params)
                r = self.controlador.optimize(peticion).model_dump()
                esperada = self._curva_de_los_componentes_reportados(filtro, r["componentes_optimizados"])
                self.assertTrue(np.allclose(r["respuesta_frecuencia"]["vout"], esperada[:, 1], rtol=1e-6))
                self.assertIsNone(r["esquema_error"])

    def test_un_fallo_de_dibujo_no_descarta_la_optimizacion(self):
        with mock.patch.object(modulo_respuesta, "obtener_esquema", side_effect=TopologiaNoSoportada("no cabe")):
            r = self._optimizar("pasa_altas")
        self.assertIsNone(r["esquema"])
        self.assertEqual(r["esquema_error"], "TopologiaNoSoportada: no cabe")
        self.assertGreater(r["fitness"], 0)
        self.assertTrue(r["componentes_optimizados"])
        self.assertTrue(r["grafica_png_base64"])
        self.assertIsNotNone(r["respuesta_frecuencia"])

    def test_la_respuesta_con_tiempo_tambien_trae_esquema(self):
        peticion = _peticion("pasa_bajas")
        peticion.algoritmo = "optimizacion_bayesiana"
        peticion.entorno["parametros_optimizador"] = _kv([("n_iniciales", 3), ("n_iteraciones", 2), ("xi", 0.01),
                                                          ("n_candidatos", 20), ("n_restarts", 2), ("semilla", 42)])
        r = self.controlador.optimize(peticion).model_dump()
        self.assertIn("tiempo_ejecucion_s", r)
        self.assertIsNotNone(r["esquema"])


class TestEndpointDeEsquemas(unittest.TestCase):

    def setUp(self):
        limpiar_cache()
        self.controlador = CircuitSchemaController()

    def test_devuelve_el_esquema_de_cada_filtro_y_valida_contra_el_contrato(self):
        for filtro in FILTROS:
            with self.subTest(filtro=filtro):
                crudo = self.controlador.get_schema(filtro)
                self.assertEqual(crudo, obtener_esquema(filtro))
                EsquemaCircuito.model_validate(crudo)

    def test_filtro_inexistente_es_404_y_lista_los_disponibles(self):
        with self.assertRaises(HTTPException) as ctx:
            self.controlador.get_schema("pasa_todo")
        self.assertEqual(ctx.exception.status_code, 404)
        for filtro in FILTROS:
            self.assertIn(filtro, str(ctx.exception.detail))

    def test_plantilla_no_dibujable_es_500_con_el_motivo(self):
        with mock.patch("app.controller.circuit_schema_controller.obtener_esquema",
                        side_effect=TopologiaNoSoportada("3 ramas")):
            with self.assertRaises(HTTPException) as ctx:
                self.controlador.get_schema("pasa_altas")
        self.assertEqual(ctx.exception.status_code, 500)
        self.assertIn("3 ramas", str(ctx.exception.detail))

    def test_el_router_expone_get_api_circuitos_filtro(self):
        rutas = getattr(circuit_schema_router, "rutas", None)          # stub de pruebas
        if rutas is None:                                              # FastAPI real
            rutas = [(m, r.path, r.endpoint) for r in circuit_schema_router.routes for m in r.methods]
        self.assertIn(("GET", "/api/circuitos/{filtro}"), [(m, p) for m, p, _ in rutas])


if __name__ == "__main__":
    unittest.main()