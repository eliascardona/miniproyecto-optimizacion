"""Fase 0: los exportadores generan la gráfica sin pyplot (sin estado global ni fugas) y en paralelo."""
import importlib
import inspect
import sys
import tempfile
import threading
import unittest
from pathlib import Path

import numpy as np

MODULOS = [
    "app.utils.genetico.pasa_altas.result_exporter",
    "app.utils.genetico.pasa_bajas.result_exporter",
    "app.utils.genetico.pasa_banda.result_exporter",
    "app.utils.genetico.rechaza_banda.result_exporter",
    "app.utils.recocido_simulado.rechaza_banda.result_exporter",
]
# Valores para los parámetros que cada exportador pueda pedir (se pasan solo los que existan en su firma).
VALORES = dict(vs_valor=5.0, fc_objetivo=1000.0, f_paso=10000.0, f_aten=1000.0, amp_paso_objetivo=5.0,
               amp_aten_objetivo=0.0, fc_inferior_objetivo=100.0, fc_superior_objetivo=1000.0,
               f_paso_1=10.0, f_aten_1=100.0, f_aten_2=500.0, f_paso_2=10000.0)


def _datos(ruta: Path):
    f = np.logspace(0, 5, 301)
    np.savetxt(ruta, np.column_stack([f, 5.0 / np.sqrt(1 + (f / 1500.0) ** 4)]))


def _generar(modulo, modo, datos: Path, salida: Path):
    firma = inspect.signature(modulo.graficar_resultado).parameters
    kwargs = {k: v for k, v in VALORES.items() if k in firma}
    modulo.graficar_resultado(archivo_datos=str(datos), archivo_salida=str(salida), modo=modo, **kwargs)


class TestExportadoresSinPyplot(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.datos = self.dir / "datos.txt"
        _datos(self.datos)

    def tearDown(self):
        self._tmp.cleanup()

    def test_genera_png_valido_en_ambos_modos_y_no_deja_figuras_abiertas(self):
        for nombre in MODULOS:
            modulo = importlib.import_module(nombre)
            for modo in ("BASICO", "AVANZADO"):
                with self.subTest(modulo=nombre, modo=modo):
                    salida = self.dir / f"{nombre.split('.')[-2]}_{modo}.png"
                    _generar(modulo, modo, self.datos, salida)
                    contenido = salida.read_bytes()
                    self.assertTrue(contenido.startswith(b"\x89PNG"))
                    self.assertGreater(len(contenido), 5000)
        if "matplotlib.pyplot" in sys.modules:            # si alguien más lo cargó, al menos que no haya figuras
            self.assertEqual(sys.modules["matplotlib.pyplot"].get_fignums(), [])

    def test_los_exportadores_no_importan_pyplot(self):
        for nombre in MODULOS:
            codigo = Path(importlib.import_module(nombre).__file__).read_text(encoding="utf-8")
            self.assertNotIn("matplotlib.pyplot", codigo, nombre)
            self.assertNotIn("plt.", codigo, nombre)

    def test_generacion_en_paralelo(self):
        modulo = importlib.import_module(MODULOS[0])
        errores = []

        def tarea(i):
            try:
                _generar(modulo, "AVANZADO", self.datos, self.dir / f"par_{i}.png")
            except Exception as e:                         # pragma: no cover
                errores.append(e)

        hilos = [threading.Thread(target=tarea, args=(i,)) for i in range(8)]
        [h.start() for h in hilos]
        [h.join() for h in hilos]
        self.assertEqual(errores, [])
        for i in range(8):
            self.assertTrue((self.dir / f"par_{i}.png").read_bytes().startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()