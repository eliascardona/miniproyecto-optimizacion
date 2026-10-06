"""Fase 0: la plantilla del repositorio es de solo lectura y cada corrida usa su propio directorio."""
import gc
import hashlib
import tempfile
import unittest
from pathlib import Path

from app.constants_repository import ConstantsRepository

FILTROS = ["pasa_altas", "pasa_bajas", "pasa_banda", "rechaza_banda"]


def _huella_plantilla(filtro: str) -> dict:
    carpeta = ConstantsRepository.directorio_plantilla_de(filtro)
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in carpeta.iterdir() if p.is_file()}


def _temporales_de_corridas() -> set:
    return {p.name for p in Path(tempfile.gettempdir()).glob("opt_*")}


class TestConstantsRepository(unittest.TestCase):

    def test_el_directorio_de_trabajo_es_propio_y_distinto_de_la_plantilla(self):
        for filtro in FILTROS:
            with self.subTest(filtro=filtro), ConstantsRepository(filtro) as repo:
                trabajo = Path(repo.get_directorio_trabajo())
                self.assertTrue(trabajo.is_dir())
                self.assertNotEqual(trabajo, ConstantsRepository.directorio_plantilla_de(filtro))
                for ruta in (repo.get_archivo_cir(), repo.get_archivo_datos(), repo.get_grafica_archivo(),
                             repo.get_resultado_json()):
                    self.assertEqual(Path(ruta).parent, trabajo)

    def test_se_copian_el_cir_y_la_libreria(self):
        with ConstantsRepository("pasa_altas") as repo:
            self.assertTrue(Path(repo.get_archivo_cir()).is_file())
            self.assertTrue((Path(repo.get_directorio_trabajo()) / "lm741.lib").is_file())

    def test_dos_instancias_nunca_comparten_directorio(self):
        with ConstantsRepository("pasa_altas") as a, ConstantsRepository("pasa_altas") as b:
            self.assertNotEqual(a.get_directorio_trabajo(), b.get_directorio_trabajo())
            self.assertNotEqual(a.get_archivo_cir(), b.get_archivo_cir())

    def test_modificar_el_cir_de_trabajo_no_toca_la_plantilla(self):
        for filtro in FILTROS:
            with self.subTest(filtro=filtro):
                antes = _huella_plantilla(filtro)
                with ConstantsRepository(filtro) as repo:
                    Path(repo.get_archivo_cir()).write_text("* sobrescrito por una corrida")
                    Path(repo.get_archivo_datos()).write_text("1 1\n")
                self.assertEqual(antes, _huella_plantilla(filtro))

    def test_cleanup_borra_el_directorio_y_es_idempotente(self):
        repo = ConstantsRepository("pasa_bajas")
        trabajo = Path(repo.get_directorio_trabajo())
        repo.cleanup()
        self.assertFalse(trabajo.exists())
        repo.cleanup()                                   # segunda llamada: sin error

    def test_si_se_pierde_la_referencia_el_directorio_se_borra_igual(self):
        repo = ConstantsRepository("pasa_banda")
        trabajo = Path(repo.get_directorio_trabajo())
        del repo
        gc.collect()
        self.assertFalse(trabajo.exists())

    def test_un_filtro_invalido_falla_sin_dejar_directorios_huerfanos(self):
        antes = _temporales_de_corridas()
        for malo in ("no_existe", "../pasa_altas", "", "..", "pasa_altas/../pasa_bajas"):
            with self.subTest(filtro=malo), self.assertRaises(ValueError):
                ConstantsRepository(malo)
        self.assertEqual(antes, _temporales_de_corridas())

    def test_plantilla_cir_apunta_a_la_plantilla_y_no_a_un_directorio_de_trabajo(self):
        ruta = Path(ConstantsRepository.plantilla_cir("pasa_altas"))
        self.assertEqual(ruta.parent, ConstantsRepository.directorio_plantilla_de("pasa_altas"))
        self.assertTrue(ruta.is_file())


if __name__ == "__main__":
    unittest.main()