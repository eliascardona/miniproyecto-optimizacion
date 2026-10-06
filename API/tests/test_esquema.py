"""Fase 1: parser de netlist, análisis de topología y layout de esquemas (los 4 filtros reales + casos límite)."""
import hashlib
import json
import unittest
from pathlib import Path

from app.constants_repository import ConstantsRepository
from app.utils.esquema import (EsquemaError, NetlistInvalido, TopologiaNoSoportada, construir_esquema,
                               limpiar_cache, obtener_esquema, parse_netlist, validar_esquema)
from app.utils.esquema.netlist import valor_spice_a_float

FILTROS = ["pasa_altas", "pasa_bajas", "pasa_banda", "rechaza_banda"]

# Roles esperados por filtro (la topología es fija: solo cambian los valores).
ESPERADO = {
    "pasa_altas": dict(serie={"C1_1", "C2_1", "C1_2", "C2_2"}, derivacion={"R2_1", "R2_2"},
                       realimentacion={"R1_1", "R1_2"}, etapas=2, elementos=11),
    "pasa_bajas": dict(serie={"R1_1", "R2_1", "R1_2", "R2_2"}, derivacion={"C2_1", "C2_2"},
                       realimentacion={"C1_1", "C1_2"}, etapas=2, elementos=11),
    "pasa_banda": dict(serie={"C1_HP", "C2_HP", "R1_LP", "R2_LP"}, derivacion={"R2_HP", "C2_LP"},
                       realimentacion={"R1_HP", "C1_LP"}, etapas=2, elementos=11),
    "rechaza_banda": dict(serie={"R1", "R2", "C1", "C2"}, derivacion={"C3", "R3"},
                          realimentacion=set(), etapas=2, elementos=9),
}

# Sallen-Key pasa-altas de UNA etapa: base para las variantes de los casos límite.
MINIMO = """.title MINIMO
Vs 1000 0 AC 5.0
Rs 1000 1 500.0
C1 1 2 1e-8
C2 2 3 1e-8
R1 2 1001 1e+4
R2 3 0 1e+4
XOP1 3 1001 Vp Vn 1001 LM741
Vpp Vp 0 DC 15.0
Vnn Vn 0 DC -15.0
Rl 1001 0 500.0
.control
wrdata datos_filtro.txt vm(1001)
.endc
.END
"""

# Escalera LC pasiva del frontend legacy (primera línea = título, 'ac 5.000000V', '500ohms', sin vm()).
ESCALERA_LEGACY = """CIRCUITO GENERADO
Vs 1000 0 ac 5.000000V
Rs 1000 1 500ohms
L1 1 2 27e-4
C1 2 0 33e-9
L2 2 3 27e-2
C2 3 0 68e-8
L3 3 1002 68e-6
C3 1002 0 15e-9
Rl 1002 0 500ohms
.AC DEC 20 1Hz 100000Hz
.END
"""


def _plantilla(filtro):
    return Path(ConstantsRepository.plantilla_cir(filtro)).read_text(encoding="utf-8")


def _por_rol(esquema, rol):
    return {e["nombre"] for e in esquema["elementos"] if e["rol"] == rol}


def _huella(filtro):
    carpeta = ConstantsRepository.directorio_plantilla_de(filtro)
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in carpeta.iterdir() if p.is_file()}


class TestParser(unittest.TestCase):

    def test_valores_spice(self):
        casos = {"1.5e-8": 1.5e-8, "5.6e+7": 5.6e7, "4.7u": 4.7e-6, "10k": 1e4, "1meg": 1e6, "2.2n": 2.2e-9,
                 "500ohms": 500.0, "5.000000V": 5.0, "1Hz": 1.0, "100p": 1e-10}
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertAlmostEqual(valor_spice_a_float(texto), esperado, delta=abs(esperado) * 1e-12)

    def test_las_cuatro_plantillas_se_leen_completas(self):
        for filtro in FILTROS:
            with self.subTest(filtro=filtro):
                net = parse_netlist(_plantilla(filtro))
                self.assertTrue(net.titulo.startswith("FILTRO"))
                self.assertEqual(net.nodo_observado, "1002")
                self.assertEqual(len(net.opamps), 2)
                self.assertEqual(sorted(f.nombre for f in net.fuentes), ["Vnn", "Vpp", "Vs"])
                self.assertEqual(sorted(o.modelo for o in net.opamps), ["LM741", "LM741"])

    def test_netlist_legacy_con_titulo_en_primera_linea(self):
        net = parse_netlist(ESCALERA_LEGACY)
        self.assertEqual(net.titulo, "CIRCUITO GENERADO")
        self.assertEqual({p.tipo for p in net.pasivos}, {"R", "L", "C"})
        self.assertIsNone(net.nodo_observado)

    def test_netlists_mal_formados(self):
        malos = {
            "elemento no soportado": MINIMO.replace("Rl 1001 0 500.0", "D1 1001 0 diodo"),
            "valor inválido": MINIMO.replace("C1 1 2 1e-8", "C1 1 2 abc"),
            "componente repetido": MINIMO + "\nC1 5 6 1e-9",
            "op-amp con pocos pines": MINIMO.replace("XOP1 3 1001 Vp Vn 1001 LM741", "XOP1 3 1001 Vp"),
            "pasivo con pocos campos": MINIMO.replace("C2 2 3 1e-8", "C2 2 3"),
        }
        for descripcion, texto in malos.items():
            with self.subTest(caso=descripcion), self.assertRaises(NetlistInvalido):
                parse_netlist(texto)


class TestEsquemasDeLosCuatroFiltros(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        limpiar_cache()
        cls.esquemas = {f: obtener_esquema(f) for f in FILTROS}

    def test_estructura_por_filtro(self):
        for filtro, esp in ESPERADO.items():
            with self.subTest(filtro=filtro):
                e = self.esquemas[filtro]
                self.assertEqual(e["num_etapas"], esp["etapas"])
                self.assertEqual(len(e["elementos"]), esp["elementos"])
                self.assertEqual(len(e["opamps"]), 2)
                self.assertEqual(_por_rol(e, "serie"), esp["serie"])
                self.assertEqual(_por_rol(e, "derivacion"), esp["derivacion"])
                self.assertEqual(_por_rol(e, "realimentacion"), esp["realimentacion"])
                self.assertEqual(_por_rol(e, "fuente"), {"Vs"})
                self.assertEqual(_por_rol(e, "resistencia_fuente"), {"Rs"})
                self.assertEqual(_por_rol(e, "carga"), {"Rl"})
                self.assertEqual((e["nodo_fuente"], e["nodo_entrada"], e["nodo_salida"]), ("1000", "1", "1002"))

    def test_invariantes_geometricos(self):
        """Cobertura exacta, 0 símbolos encimados, extremos sobre sus nodos, tierras con símbolo."""
        for filtro in FILTROS:
            with self.subTest(filtro=filtro):
                net = parse_netlist(_plantilla(filtro))
                self.assertEqual(validar_esquema(self.esquemas[filtro], net), [])

    def test_optimizable_coincide_con_lo_que_optimiza_el_backend(self):
        """Lo que el dibujo marca como optimizable == los componentes del vector que evoluciona el optimizador."""
        from app.preparation_service.pasa_altas_service import PasaAltasPreparationService
        from app.preparation_service.pasa_bajas_service import PasaBajasPreparationService
        from app.preparation_service.pasa_banda_service import PasaBandaPreparationService
        from app.preparation_service.rechaza_banda_service import RechazaBandaPreparationService
        servicios = {"pasa_altas": PasaAltasPreparationService, "pasa_bajas": PasaBajasPreparationService,
                     "pasa_banda": PasaBandaPreparationService, "rechaza_banda": RechazaBandaPreparationService}
        for filtro, clase in servicios.items():
            with self.subTest(filtro=filtro):
                servicio = clase()
                try:
                    del_optimizador = [c["nombre"] for c in servicio.extract_components()]
                    del_dibujo = {e["nombre"] for e in self.esquemas[filtro]["elementos"] if e["optimizable"]}
                    self.assertEqual(set(del_optimizador), del_dibujo)
                    self.assertEqual(len(del_optimizador), len(del_dibujo))
                    # y la marca "a tierra" que ya usaba la API coincide con el rol de derivación
                    a_tierra = {c["nombre"] for c in servicio.extract_components() if c["es_shunt"]}
                    self.assertEqual(a_tierra, _por_rol(self.esquemas[filtro], "derivacion"))
                finally:
                    servicio.constants_repository.cleanup()

    def test_twin_t_usa_dos_filas_y_deriva_hacia_lados_opuestos(self):
        e = self.esquemas["rechaza_banda"]
        el = {x["nombre"]: x for x in e["elementos"]}
        fila = lambda n: el[n]["ruta"][el[n]["seg"]][1]            # y del segmento donde va el símbolo
        self.assertLess(fila("R1"), 0)
        self.assertEqual(fila("R1"), fila("R2"))
        self.assertGreater(fila("C1"), 0)
        self.assertEqual(fila("C1"), fila("C2"))
        self.assertLess(el["C3"]["ruta"][1][1], el["C3"]["ruta"][0][1])     # C3 sube
        self.assertGreater(el["R3"]["ruta"][1][1], el["R3"]["ruta"][0][1])  # R3 baja
        self.assertEqual(e["opamps"][0]["nodos"]["in_p"], "1")             # buffer de entrada
        self.assertEqual(e["opamps"][1]["nodos"]["in_p"], "5")

    def test_la_realimentacion_pasa_por_encima_de_la_fila_principal(self):
        for filtro in ("pasa_altas", "pasa_bajas", "pasa_banda"):
            with self.subTest(filtro=filtro):
                for x in self.esquemas[filtro]["elementos"]:
                    if x["rol"] == "realimentacion":
                        carril = x["ruta"][x["seg"]][1]
                        self.assertLess(carril, 0)
                        self.assertEqual(x["ruta"][-1][1], 0.0)             # vuelve a la salida del op-amp

    def test_las_etapas_avanzan_de_izquierda_a_derecha(self):
        for filtro in FILTROS:
            with self.subTest(filtro=filtro):
                e = self.esquemas[filtro]
                self.assertLess(e["nodos"]["1"]["x"], e["nodos"]["1001" if filtro != "rechaza_banda" else "2"]["x"])
                self.assertLess(e["nodos"][e["opamps"][0]["nodos"]["out"]]["x"], e["nodos"]["1002"]["x"])

    def test_es_deterministico_y_serializable(self):
        for filtro in FILTROS:
            with self.subTest(filtro=filtro):
                net = parse_netlist(_plantilla(filtro))
                a, b = construir_esquema(net), construir_esquema(net)
                self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
                self.assertEqual(json.loads(json.dumps(a)), a)             # ida y vuelta por JSON sin pérdidas

    def test_el_json_es_pequeno(self):
        for filtro in FILTROS:
            self.assertLess(len(json.dumps(self.esquemas[filtro])), 6000)


class TestEscaleraLegacy(unittest.TestCase):
    """El mismo algoritmo dibuja las escaleras LC del frontend legacy (generalidad del enfoque)."""

    def test_se_dibuja_completa_y_sin_choques(self):
        net = parse_netlist(ESCALERA_LEGACY)
        e = construir_esquema(net)
        self.assertEqual(validar_esquema(e, net), [])
        self.assertEqual(e["num_etapas"], 1)
        self.assertEqual(e["opamps"], [])
        self.assertEqual(_por_rol(e, "serie"), {"L1", "L2", "L3"})
        self.assertEqual(_por_rol(e, "derivacion"), {"C1", "C2", "C3"})
        self.assertEqual(_por_rol(e, "carga"), {"Rl"})            # y no C3, que también va a tierra en la salida
        self.assertEqual(e["nodo_salida"], "1002")


class TestTopologiasNoSoportadas(unittest.TestCase):
    """Lo que no cabe en el modelo se rechaza con un mensaje claro, no se dibuja mal."""

    def _rechazado(self, texto, fragmento):
        with self.assertRaises(TopologiaNoSoportada) as ctx:
            construir_esquema(parse_netlist(texto))
        self.assertIn(fragmento, str(ctx.exception))

    def test_el_circuito_minimo_si_se_dibuja(self):
        net = parse_netlist(MINIMO)
        e = construir_esquema(net)
        self.assertEqual(validar_esquema(e, net), [])
        self.assertEqual((e["num_etapas"], e["nodo_salida"]), (1, "1001"))

    def test_opamp_inversor_o_con_ganancia(self):
        self._rechazado(MINIMO.replace("XOP1 3 1001 Vp Vn 1001", "XOP1 3 4 Vp Vn 1001"), "seguidor")

    def test_elemento_huerfano(self):
        self._rechazado(MINIMO.replace(".control", "C9 7 8 1e-9\n.control"), "ninguna etapa")

    def test_tres_ramas_en_paralelo(self):
        tres = MINIMO.replace("C1 1 2 1e-8\nC2 2 3 1e-8\n", "R4 1 3 1e3\nR5 1 5 1e3\nR6 5 3 1e3\nR7 1 6 1e3\nR8 6 3 1e3\n"
                              ).replace("R1 2 1001 1e+4\n", "")
        self._rechazado(tres, "ramas en paralelo")

    def test_derivacion_en_el_punto_de_union_de_dos_ramas(self):
        dos = MINIMO.replace("C1 1 2 1e-8\nC2 2 3 1e-8\n", "R4 1 5 1e3\nR5 5 3 1e3\nC4 1 6 1e-9\nC5 6 3 1e-9\n"
                             ).replace("R1 2 1001 1e+4\n", "") + "\nC9 3 0 1e-9"
        self._rechazado(dos.replace("R2 3 0 1e+4\n", ""), "donde se unen las ramas")

    def test_ramas_de_distinto_largo(self):
        desigual = MINIMO.replace("C1 1 2 1e-8\nC2 2 3 1e-8\n", "R4 1 5 1e3\nR5 5 3 1e3\nC4 1 3 1e-9\n"
                                  ).replace("R1 2 1001 1e+4\n", "")
        self._rechazado(desigual, "distinto número de elementos")

    def test_sin_fuente_ac(self):
        self._rechazado(MINIMO.replace("Vs 1000 0 AC 5.0", "Vs 1000 0 DC 5.0"), "fuente de señal AC")

    def test_sin_resistencia_de_fuente(self):
        self._rechazado(MINIMO.replace("Rs 1000 1 500.0\n", ""), "resistencia de la fuente")

    def test_carga_ambigua(self):
        ambiguo = MINIMO.replace("Rl 1001 0 500.0", "Ra 1001 0 500.0\nRb 1001 0 500.0")
        self._rechazado(ambiguo, "sin ambigüedad")

    def test_opamp_fuera_de_la_cadena(self):
        self._rechazado(MINIMO.replace(".control", "XOP9 8 9 Vp Vn 9 LM741\n.control"), "no están en la cadena")

    def test_sin_salida_identificable(self):
        sin = MINIMO.replace("wrdata datos_filtro.txt vm(1001)", "run").replace("Rl 1001 0 500.0", "Rx 1001 0 500.0")
        self._rechazado(sin, "nodo de salida")


class TestElValidadorDetectaErrores(unittest.TestCase):
    """Pruebas de la prueba: se rompe un esquema bueno de formas concretas y el validador debe notarlo."""

    def setUp(self):
        import copy
        self.net = parse_netlist(_plantilla("pasa_altas"))
        self.bueno = construir_esquema(self.net)
        self.malo = copy.deepcopy(self.bueno)

    def _problemas(self):
        return " | ".join(validar_esquema(self.malo, self.net))

    def test_el_esquema_sin_tocar_es_valido(self):
        self.assertEqual(validar_esquema(self.malo, self.net), [])

    def test_componente_duplicado(self):
        self.malo["elementos"].append(dict(self.malo["elementos"][2]))
        self.assertIn("más de una vez", self._problemas())

    def test_componente_faltante(self):
        del self.malo["elementos"][3]
        self.assertIn("está en el netlist y no en el esquema", self._problemas())

    def test_componente_inventado(self):
        extra = dict(self.malo["elementos"][2], nombre="R_FANTASMA")
        self.malo["elementos"].append(extra)
        self.assertIn("está en el esquema y no en el netlist", self._problemas())

    def test_opamp_sin_dibujar(self):
        self.malo["opamps"].pop()
        self.assertIn("op-amps sin dibujar", self._problemas())

    def test_ruta_desconectada_de_su_nodo(self):
        serie = next(e for e in self.malo["elementos"] if e["rol"] == "serie")
        serie["ruta"][0][0] += 0.7
        self.assertIn("extremos de la ruta no coinciden", self._problemas())

    def test_simbolos_encimados(self):
        a, b = [e for e in self.malo["elementos"] if e["rol"] == "serie"][:2]
        b["ruta"] = [list(p) for p in a["ruta"]]
        b["nodos"] = list(a["nodos"])
        self.assertIn("se encimen", self._problemas())

    def test_segmento_de_largo_cero(self):
        e = next(e for e in self.malo["elementos"] if e["rol"] == "derivacion")
        e["ruta"][1] = list(e["ruta"][0])
        self.assertIn("largo cero", self._problemas())

    def test_derivacion_sin_simbolo_de_tierra(self):
        self.malo["tierras"].pop()
        self.assertIn("símbolo de tierra", self._problemas())

    def test_geometria_fuera_de_limites(self):
        self.malo["limites"]["x_max"] = 1.0
        self.assertIn("fuera de 'limites'", self._problemas())


class TestUniones(unittest.TestCase):
    """Los puntos de unión (>= 3 conductores) los calcula el backend; el cliente solo los pinta."""

    def _uniones(self, filtro):
        e = obtener_esquema(filtro)
        return e, {tuple(u) for u in e["uniones"]}

    def _en(self, e, nodo):
        return (e["nodos"][nodo]["x"], e["nodos"][nodo]["y"])

    def test_sallen_key(self):
        for filtro in ("pasa_altas", "pasa_bajas", "pasa_banda"):
            with self.subTest(filtro=filtro):
                e, u = self._uniones(filtro)
                for nodo in ("2", "3", "1001", "4", "5", "1002"):
                    self.assertIn(self._en(e, nodo), u, f"falta el punto de unión en el nodo {nodo}")
                self.assertNotIn(self._en(e, "1"), u)           # solo es una esquina (Rs -> C1)

    def test_twin_t(self):
        e, u = self._uniones("rechaza_banda")
        for nodo in ("2", "3", "4", "5", "1002"):
            self.assertIn(self._en(e, nodo), u, f"falta el punto de unión en el nodo {nodo}")
        self.assertNotIn(self._en(e, "1"), u)


class TestServicio(unittest.TestCase):

    def setUp(self):
        limpiar_cache()

    def test_aplica_valores_por_nombre_sin_distinguir_mayusculas(self):
        e = obtener_esquema("pasa_altas", {"c1_1": 3.3e-9, "R2_2": 4700, "Vs": 7.0, "Vpp": 12.0})
        valores = {x["nombre"]: x["valor"] for x in e["elementos"]}
        self.assertEqual((valores["C1_1"], valores["R2_2"], valores["Vs"]), (3.3e-9, 4700.0, 7.0))
        self.assertEqual({a["nombre"]: a["valor"] for a in e["alimentacion"]}["Vpp"], 12.0)

    def test_un_nombre_desconocido_es_un_error(self):
        with self.assertRaises(EsquemaError):
            obtener_esquema("pasa_altas", {"R99": 1000})

    def test_valores_no_finitos_son_un_error(self):
        for malo in (float("nan"), float("inf"), "mil"):
            with self.subTest(valor=malo), self.assertRaises(EsquemaError):
                obtener_esquema("pasa_altas", {"R1_1": malo})

    def test_cada_llamada_devuelve_una_copia_independiente(self):
        a = obtener_esquema("pasa_bajas")
        a["elementos"][0]["valor"] = -1
        a["opamps"].clear()
        b = obtener_esquema("pasa_bajas")
        self.assertNotEqual(b["elementos"][0]["valor"], -1)
        self.assertEqual(len(b["opamps"]), 2)

    def test_filtro_inexistente(self):
        with self.assertRaises(ValueError):
            obtener_esquema("no_existe")

    def test_no_modifica_la_plantilla_ni_crea_directorios_de_trabajo(self):
        import tempfile
        antes = {f: _huella(f) for f in FILTROS}
        temporales = {p.name for p in Path(tempfile.gettempdir()).glob("opt_*")}
        for f in FILTROS:
            obtener_esquema(f, {"Vs": 5.0})
        self.assertEqual(antes, {f: _huella(f) for f in FILTROS})
        self.assertEqual(temporales, {p.name for p in Path(tempfile.gettempdir()).glob("opt_*")})


if __name__ == "__main__":
    unittest.main()