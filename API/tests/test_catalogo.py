"""
Fase 4: catálogo filtro × algoritmo (GET /api/catalogo).

Lo que se verifica:
  1. ESTRUCTURA   el catálogo valida contra su esquema Pydantic REAL, coincide con los enums y con lo que el
                  servidor ejecuta (SERVICE_MAP y FILTRO_ALGORITMO_MAP), y el endpoint está registrado.
  2. FIDELIDAD    los valores iniciales y las claves coinciden con los config.json del equipo de algoritmos y
                  con lo que el código de cada servicio lee de verdad.
  3. EJECUCIÓN    con el catálogo se arma una petición válida para las 16 combinaciones × 2 modos: pasa el
                  esquema, el servicio la acepta, y (con ngspice simulado) la corrida completa termina bien.
  4. SENSIBILIDAD las comprobaciones fallan cuando deben (definiciones rotas, petición incompleta).
"""
import base64
import copy
import inspect
import json
import math
import re
import sys
import unittest
from itertools import product
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import app.constants_repository as repositorio
from app.controller.catalog_controller import CatalogController
from app.controller.individual_optimization_controller import IndividualOptimizationController
from app.pydantic_schema.api_request_schema.circuit_optimization_request import (
    FILTRO_ALGORITMO_MAP, AlgoritmoEnum, CircuitOptimizationRequest, FiltroEnum)
from app.pydantic_schema.api_response_schema.catalogo_esquema import CatalogoResponse
from app.routes.catalog_router import catalog_router
from app.utils.catalogo import CatalogoInvalido, construir_catalogo, cumple_limites_duros, relacion_se_cumple
from app.utils.catalogo import definiciones as definiciones

SERVICE_MAP = IndividualOptimizationController.SERVICE_MAP
FALSO = [sys.executable, str(Path(__file__).with_name("_ngspice_falso.py"))]
RAIZ_ALGORITMOS = Path(__file__).resolve().parents[2] / "ALGORITMOS_DE_OPTIMIZACION"

ENTORNO = {"v_fuente": 5, "r_fuente": 470, "r_carga": 470}
BARRIDO = {"f_inicial": 1, "f_final": 100000}
MODOS = ("BASICO", "AVANZADO")

# Hiperparámetros diminutos para que la corrida completa sea rápida. Las CLAVES se toman del catálogo; si el
# catálogo cambia de claves, la prueba falla (KeyError) en vez de seguir probando otra cosa.
DIMINUTOS = {
    "algoritmo_genetico": {"tam_poblacion": 4, "num_generaciones": 2, "prob_cruce": 0.8, "prob_mutacion": 0.3,
                           "elitismo": 1, "torneo_k": 2},
    "enjambre_particulas": {"num_particulas": 4, "num_iteraciones": 2, "w": 0.7, "c1": 1.5, "c2": 1.5},
    "optimizacion_bayesiana": {"n_iniciales": 3, "n_iteraciones": 2, "xi": 0.01, "n_candidatos": 20,
                               "n_restarts": 2, "semilla": 42},
    "recocido_simulado": {"temp_inicial": 2.0, "temp_final": 1.0, "factor_enfriamiento": 0.6,
                          "iteraciones_por_temp": 2},
}


def kv(diccionario):
    return [{"clave": k, "valor": v} for k, v in diccionario.items()]


def catalogo():
    return construir_catalogo(SERVICE_MAP.keys())


def por_id(lista, id_):
    return next(x for x in lista if x["id"] == id_)


def cuerpo_desde_catalogo(cat, filtro, algoritmo, modo, parametros=None):
    """
    Cómo un cliente arma POST /api/optimizar SOLO con el catálogo (el cliente Java hace exactamente esto):
    claves y valores iniciales salen del catálogo; entorno y barrido los pone el usuario.
    """
    frecuencias = next(f for f in por_id(cat["filtros"], filtro)["frecuencias"] if f["modo"] == modo)
    combinacion = next(c for c in cat["combinaciones"] if (c["filtro"], c["algoritmo"]) == (filtro, algoritmo))
    return {
        "filtro": filtro,
        "algoritmo": algoritmo,
        "entorno": {
            "modo": modo,
            "entorno": dict(ENTORNO),
            "barrido_ac": dict(BARRIDO),
            "parametros_optimizador": kv(parametros if parametros is not None else combinacion["valores_iniciales"]),
            "frecuencias": kv(frecuencias["valores_iniciales"]),
        },
    }


class TestEstructura(unittest.TestCase):

    def test_valida_contra_el_esquema_pydantic_real(self):
        modelo = CatalogoResponse.model_validate(catalogo())
        self.assertEqual(modelo.version_catalogo, definiciones.VERSION_CATALOGO)
        json.dumps(catalogo())          # serializable tal cual

    def test_las_combinaciones_son_exactamente_lo_que_el_servidor_ejecuta(self):
        cat = catalogo()
        pares = {(c["filtro"], c["algoritmo"]) for c in cat["combinaciones"]}
        self.assertEqual(len(cat["combinaciones"]), 16)
        self.assertEqual(pares, set(SERVICE_MAP))
        self.assertEqual(pares, set(FILTRO_ALGORITMO_MAP))
        self.assertTrue(all(c["disponible"] for c in cat["combinaciones"]))

    def test_filtros_algoritmos_y_modos_coinciden_con_los_enums_y_el_cliente_los_encuentra(self):
        cat = catalogo()
        self.assertEqual([f["id"] for f in cat["filtros"]], [f.value for f in FiltroEnum])
        self.assertEqual({a["id"] for a in cat["algoritmos"]}, {a.value for a in AlgoritmoEnum})
        self.assertEqual([m["id"] for m in cat["modos"]], list(MODOS))
        for filtro in cat["filtros"]:
            self.assertEqual([f["modo"] for f in filtro["frecuencias"]], list(MODOS))

    def test_una_combinacion_no_ejecutable_se_marca_no_disponible(self):
        faltante = ("rechaza_banda", "recocido_simulado")
        cat = construir_catalogo([par for par in SERVICE_MAP if par != faltante])
        estado = {(c["filtro"], c["algoritmo"]): c["disponible"] for c in cat["combinaciones"]}
        self.assertFalse(estado[faltante])
        self.assertEqual(sum(estado.values()), 15)

    def test_el_endpoint_esta_registrado_y_su_respuesta_valida(self):
        rutas = [(m, r.path, r.endpoint) for r in catalog_router.routes for m in r.methods]
        self.assertEqual([(m, p) for m, p, _ in rutas], [("GET", "/api/catalogo")])
        respuesta = rutas[0][2]()
        CatalogoResponse.model_validate(respuesta)
        self.assertIs(respuesta, CatalogController().get_catalog())      # mismo objeto: se construye una sola vez

    def test_main_incluye_el_router_del_catalogo(self):
        from app.main import app
        self.assertIn("/api/catalogo", [r.path for r in app.routes])

    def test_cada_llamada_a_construir_devuelve_una_copia_independiente(self):
        a = catalogo()
        a["algoritmos"][0]["parametros"][0]["minimo"] = 999
        a["filtros"][0]["frecuencias"][0]["valores_iniciales"]["fc_objetivo"] = -1
        b = catalogo()
        self.assertEqual(b["algoritmos"][0]["parametros"][0]["minimo"], 1)
        self.assertEqual(b["filtros"][0]["frecuencias"][0]["valores_iniciales"]["fc_objetivo"], 2000)


class TestCoherenciaInterna(unittest.TestCase):

    def test_los_valores_iniciales_cumplen_sus_limites_y_relaciones(self):
        cat = catalogo()
        for c in cat["combinaciones"]:
            algoritmo = por_id(cat["algoritmos"], c["algoritmo"])
            campos = {p["clave"]: p for p in algoritmo["parametros"]}
            for clave, valor in c["valores_iniciales"].items():
                self.assertTrue(cumple_limites_duros(campos[clave], valor), (c["filtro"], c["algoritmo"], clave))
            for r in algoritmo["relaciones"]:
                self.assertTrue(relacion_se_cumple(r, c["valores_iniciales"]), (c["filtro"], c["algoritmo"], r))

    def test_las_frecuencias_iniciales_cumplen_orden_y_margen_con_el_barrido_por_defecto(self):
        cat = catalogo()
        factor = cat["reglas"]["margen_decada"]["factor"]
        for filtro in cat["filtros"]:
            for modo in filtro["frecuencias"]:
                v = modo["valores_iniciales"]
                for r in modo["relaciones"]:
                    self.assertTrue(relacion_se_cumple(r, v), (filtro["id"], modo["modo"], r))
                self.assertGreaterEqual(v[modo["extremos"]["minima"]], BARRIDO["f_inicial"] * factor)
                self.assertLessEqual(v[modo["extremos"]["maxima"]], BARRIDO["f_final"] / factor)

    def test_las_frecuencias_estan_en_orden_ascendente_y_el_orden_encadena_todos_los_campos(self):
        for filtro in catalogo()["filtros"]:
            for modo in filtro["frecuencias"]:
                claves = [c["clave"] for c in modo["campos"]]
                valores = [modo["valores_iniciales"][k] for k in claves]
                self.assertEqual(valores, sorted(valores), (filtro["id"], modo["modo"]))
                self.assertEqual((modo["extremos"]["minima"], modo["extremos"]["maxima"]), (claves[0], claves[-1]))
                # n campos => n-1 relaciones encadenadas (cada una une dos vecinos)
                self.assertEqual(len(modo["relaciones"]), len(claves) - 1)

    def test_pasa_banda_y_rechaza_banda_comparten_claves_pero_no_el_significado(self):
        cat = catalogo()
        avanzado = {f["id"]: next(m for m in f["frecuencias"] if m["modo"] == "AVANZADO") for f in cat["filtros"]}
        claves = {f: [c["clave"] for c in m["campos"]] for f, m in avanzado.items()}
        self.assertEqual(set(claves["pasa_banda"]), set(claves["rechaza_banda"]))
        self.assertNotEqual(claves["pasa_banda"], claves["rechaza_banda"])        # distinto orden ascendente
        self.assertEqual(claves["pasa_banda"], ["f_aten_1", "f_paso_1", "f_paso_2", "f_aten_2"])
        self.assertEqual(claves["rechaza_banda"], ["f_paso_1", "f_aten_1", "f_aten_2", "f_paso_2"])

    def test_pasa_altas_y_pasa_bajas_comparten_claves_con_orden_invertido(self):
        cat = catalogo()
        avanzado = {f["id"]: next(m for m in f["frecuencias"] if m["modo"] == "AVANZADO") for f in cat["filtros"]}
        self.assertEqual([c["clave"] for c in avanzado["pasa_altas"]["campos"]], ["f_aten", "f_paso"])
        self.assertEqual([c["clave"] for c in avanzado["pasa_bajas"]["campos"]], ["f_paso", "f_aten"])

    def test_los_hiperparametros_dependen_solo_del_algoritmo(self):
        # Todos los filtros comparten las MISMAS claves para un algoritmo (solo cambian los valores iniciales).
        cat = catalogo()
        for algoritmo in cat["algoritmos"]:
            conjuntos = {frozenset(c["valores_iniciales"]) for c in cat["combinaciones"]
                         if c["algoritmo"] == algoritmo["id"]}
            self.assertEqual(conjuntos, {frozenset(p["clave"] for p in algoritmo["parametros"])}, algoritmo["id"])

    def test_las_frecuencias_dependen_solo_del_filtro_y_el_modo(self):
        # Y a la inversa: ningún dato de frecuencias cuelga del algoritmo (no hay campo así en la combinación).
        for c in catalogo()["combinaciones"]:
            self.assertEqual(set(c), {"filtro", "algoritmo", "disponible", "valores_iniciales"})


class TestFidelidadConElContrato(unittest.TestCase):

    def _configs(self):
        carpetas = {"ALGORITMO_GENETICO": "algoritmo_genetico", "ENJAMBRE_DE_PARTICULAS": "enjambre_particulas",
                    "OPTIMIZACION_BAYESIANA": "optimizacion_bayesiana", "RECOCIDO_SIMULADO": "recocido_simulado"}
        filtros = {"FILTRO_PASAALTAS": "pasa_altas", "FILTRO_PASABAJAS": "pasa_bajas",
                   "FILTRO_PASABANDA": "pasa_banda", "FILTRO_RECHAZABANDA": "rechaza_banda"}
        for carpeta, algoritmo in carpetas.items():
            for sub, filtro in filtros.items():
                ruta = RAIZ_ALGORITMOS / carpeta / sub / "config.json"
                yield filtro, algoritmo, json.loads(ruta.read_text(encoding="utf-8"))

    def test_valores_iniciales_y_claves_coinciden_con_los_config_json_del_equipo(self):
        if not RAIZ_ALGORITMOS.is_dir():
            self.skipTest("no está la carpeta ALGORITMOS_DE_OPTIMIZACION junto a API/")
        cat = catalogo()
        vistos = 0
        for filtro, algoritmo, cfg in self._configs():
            with self.subTest(filtro=filtro, algoritmo=algoritmo):
                combinacion = next(c for c in cat["combinaciones"]
                                   if (c["filtro"], c["algoritmo"]) == (filtro, algoritmo))
                esperados = {p["clave"]: p["valor"] for p in cfg["parametros_optimizador"]}
                self.assertEqual(combinacion["valores_iniciales"], esperados)
                modo = next(m for m in por_id(cat["filtros"], filtro)["frecuencias"] if m["modo"] == cfg["modo"])
                self.assertEqual({c["clave"] for c in modo["campos"]}, {p["clave"] for p in cfg["frecuencias"]})
                vistos += 1
        self.assertEqual(vistos, 16)

    def test_los_parametros_del_catalogo_son_los_que_cada_servicio_lee(self):
        cat = catalogo()
        patron = re.compile(r'_buscar\(params,\s*"(\w+)"\)')
        for (filtro, algoritmo), clase in SERVICE_MAP.items():
            with self.subTest(filtro=filtro, algoritmo=algoritmo):
                leidos = set()
                for base in clase.__mro__:
                    if base.__module__.startswith("app."):
                        leidos |= set(patron.findall(inspect.getsource(sys.modules[base.__module__])))
                declarados = {p["clave"] for p in por_id(cat["algoritmos"], algoritmo)["parametros"]}
                self.assertEqual(declarados, leidos)

    def test_las_claves_de_frecuencia_del_catalogo_estan_en_el_codigo_de_cada_servicio(self):
        cat = catalogo()
        patron = re.compile(r'_buscar\(frecuencias,\s*"(\w+)"\)')
        for (filtro, algoritmo), clase in SERVICE_MAP.items():
            with self.subTest(filtro=filtro, algoritmo=algoritmo):
                leidos = set()
                for base in clase.__mro__:
                    if base.__module__.startswith("app."):
                        leidos |= set(patron.findall(inspect.getsource(sys.modules[base.__module__])))
                declaradas = {c["clave"] for m in por_id(cat["filtros"], filtro)["frecuencias"] for c in m["campos"]}
                self.assertTrue(declaradas <= leidos, f"declaradas sin leer: {declaradas - leidos}")


class TestElCatalogoArmaPeticionesValidas(unittest.TestCase):

    def test_la_peticion_con_valores_iniciales_pasa_el_esquema_y_el_servicio(self):
        cat = catalogo()
        for (filtro, algoritmo), modo in product(SERVICE_MAP, MODOS):
            with self.subTest(filtro=filtro, algoritmo=algoritmo, modo=modo):
                cuerpo = cuerpo_desde_catalogo(cat, filtro, algoritmo, modo)
                peticion = CircuitOptimizationRequest(**cuerpo)               # esquema real de la API
                servicio = SERVICE_MAP[(filtro, algoritmo)]()
                try:
                    cfg = servicio.validate_json_config(peticion.entorno)
                    contexto = servicio._build_run_context(cfg)               # lee TODAS las claves o lanza
                finally:
                    servicio.constants_repository.cleanup()
                self.assertEqual(contexto["modo"], modo)
                self.assertTrue(contexto["frecuencias_ctx"])

    def test_control_negativo_una_clave_de_frecuencia_faltante_se_detecta(self):
        cat = catalogo()
        for filtro, modo in product(("pasa_altas", "rechaza_banda"), MODOS):
            with self.subTest(filtro=filtro, modo=modo):
                cuerpo = cuerpo_desde_catalogo(cat, filtro, "algoritmo_genetico", modo)
                cuerpo["entorno"]["frecuencias"].pop()
                peticion = CircuitOptimizationRequest(**cuerpo)
                servicio = SERVICE_MAP[(filtro, "algoritmo_genetico")]()
                try:
                    cfg = servicio.validate_json_config(peticion.entorno)
                    with self.assertRaisesRegex(ValueError, "Falta el parámetro requerido"):
                        servicio._build_run_context(cfg)
                finally:
                    servicio.constants_repository.cleanup()

    def test_control_negativo_las_claves_de_otro_algoritmo_se_detectan(self):
        cat = catalogo()
        cuerpo = cuerpo_desde_catalogo(cat, "pasa_altas", "algoritmo_genetico", "AVANZADO")
        otra = next(c for c in cat["combinaciones"] if c["algoritmo"] == "enjambre_particulas")
        cuerpo["entorno"]["parametros_optimizador"] = kv(otra["valores_iniciales"])
        servicio = SERVICE_MAP[("pasa_altas", "algoritmo_genetico")]()
        try:
            cfg = servicio.validate_json_config(CircuitOptimizationRequest(**cuerpo).entorno)
            with self.assertRaisesRegex(ValueError, "Falta el parámetro requerido"):
                servicio._build_run_context(cfg)
        finally:
            servicio.constants_repository.cleanup()


class TestCorridaCompletaConNgspiceSimulado(unittest.TestCase):

    def setUp(self):
        self._original = repositorio.NGSPICE_EXE
        repositorio.NGSPICE_EXE = FALSO
        self.controlador = IndividualOptimizationController()

    def tearDown(self):
        repositorio.NGSPICE_EXE = self._original

    def test_las_16_combinaciones_en_los_dos_modos_terminan_con_una_respuesta_valida(self):
        cat = catalogo()
        corridas = 0
        for (filtro, algoritmo), modo in product(SERVICE_MAP, MODOS):
            with self.subTest(filtro=filtro, algoritmo=algoritmo, modo=modo):
                claves = [p["clave"] for p in por_id(cat["algoritmos"], algoritmo)["parametros"]]
                parametros = {k: DIMINUTOS[algoritmo][k] for k in claves}       # KeyError si cambian las claves
                self.assertEqual(set(DIMINUTOS[algoritmo]), set(claves))
                cuerpo = cuerpo_desde_catalogo(cat, filtro, algoritmo, modo, parametros)
                respuesta = self.controlador.optimize(SimpleNamespace(**CircuitOptimizationRequest(**cuerpo).model_dump()))
                self.assertTrue(math.isfinite(respuesta.fitness))
                self.assertGreaterEqual(respuesta.fitness, 0.0)
                self.assertTrue(respuesta.componentes_optimizados)
                self.assertTrue(base64.b64decode(respuesta.grafica_png_base64).startswith(b"\x89PNG"))
                corridas += 1
        self.assertEqual(corridas, 32)


class TestComprobacionesDelConstructor(unittest.TestCase):
    """Un catálogo inconsistente debe fallar al construirse, no entregarse roto."""

    def test_falta_una_combinacion_de_valores_iniciales(self):
        parcial = {k: v for k, v in definiciones.VALORES_INICIALES.items() if k != ("pasa_altas", "recocido_simulado")}
        with mock.patch.object(definiciones, "VALORES_INICIALES", parcial):
            with self.assertRaisesRegex(CatalogoInvalido, "no cubre las 16 combinaciones"):
                catalogo()

    def test_un_valor_inicial_viola_un_limite_duro(self):
        roto = copy.deepcopy(definiciones.VALORES_INICIALES)
        roto[("pasa_altas", "recocido_simulado")]["factor_enfriamiento"] = 1.0       # maximo exclusivo
        with mock.patch.object(definiciones, "VALORES_INICIALES", roto):
            with self.assertRaisesRegex(CatalogoInvalido, "factor_enfriamiento"):
                catalogo()

    def test_un_valor_inicial_incumple_una_relacion_de_error(self):
        roto = copy.deepcopy(definiciones.VALORES_INICIALES)
        roto[("pasa_altas", "algoritmo_genetico")]["elitismo"] = 30                  # = tam_poblacion
        with mock.patch.object(definiciones, "VALORES_INICIALES", roto):
            with self.assertRaisesRegex(CatalogoInvalido, "elitismo < tam_poblacion"):
                catalogo()

    def test_una_clave_de_mas_o_de_menos_en_los_valores_iniciales(self):
        roto = copy.deepcopy(definiciones.VALORES_INICIALES)
        roto[("pasa_bajas", "enjambre_particulas")]["inventada"] = 1
        with mock.patch.object(definiciones, "VALORES_INICIALES", roto):
            with self.assertRaisesRegex(CatalogoInvalido, "no coinciden con los campos"):
                catalogo()

    def test_un_valor_entero_con_decimales(self):
        roto = copy.deepcopy(definiciones.VALORES_INICIALES)
        roto[("pasa_altas", "algoritmo_genetico")]["tam_poblacion"] = 30.5
        with mock.patch.object(definiciones, "VALORES_INICIALES", roto):
            with self.assertRaisesRegex(CatalogoInvalido, "es entero"):
                catalogo()

    def test_frecuencias_iniciales_en_desorden(self):
        roto = copy.deepcopy(definiciones.FRECUENCIAS)
        roto["pasa_altas"]["AVANZADO"]["valores"] = {"f_aten": 10000, "f_paso": 1000}
        with mock.patch.object(definiciones, "FRECUENCIAS", roto):
            with self.assertRaises(CatalogoInvalido):
                catalogo()

    def test_una_combinacion_disponible_que_el_catalogo_no_define(self):
        with self.assertRaisesRegex(CatalogoInvalido, "no define"):
            construir_catalogo([*SERVICE_MAP, ("pasa_todo", "algoritmo_genetico")])


class TestLimitesYRelaciones(unittest.TestCase):

    def test_cumple_limites_duros_respeta_los_extremos_exclusivos(self):
        campo = {"minimo": 0, "minimo_exclusivo": True, "maximo": 1, "maximo_exclusivo": True}
        self.assertFalse(cumple_limites_duros(campo, 0))
        self.assertFalse(cumple_limites_duros(campo, 1))
        self.assertTrue(cumple_limites_duros(campo, 0.5))
        incluyente = {"minimo": 0, "minimo_exclusivo": False, "maximo": 1, "maximo_exclusivo": False}
        self.assertTrue(cumple_limites_duros(incluyente, 0))
        self.assertTrue(cumple_limites_duros(incluyente, 1))
        self.assertFalse(cumple_limites_duros(incluyente, 1.0001))
        self.assertTrue(cumple_limites_duros({"minimo": None, "minimo_exclusivo": False,
                                              "maximo": None, "maximo_exclusivo": False}, -1e9))

    def test_relacion_menor_o_igual_acepta_la_igualdad_y_menor_estricto_no(self):
        self.assertTrue(relacion_se_cumple({"izquierda": "a", "operador": "<=", "derecha": "b"}, {"a": 2, "b": 2}))
        self.assertFalse(relacion_se_cumple({"izquierda": "a", "operador": "<", "derecha": "b"}, {"a": 2, "b": 2}))


if __name__ == "__main__":
    unittest.main()