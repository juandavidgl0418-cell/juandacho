"""Pruebas de carga y verificación del archivo (RF01, RF02, RF03, RNF04, riesgos R04 y R05)."""

import unittest
from unittest import mock

from dqv import CsvFileError, ValidacionController, config

from .utilidades import DATOS, controlador_con


class PruebasCargaCsv(unittest.TestCase):
    def test_rf01_carga_archivo_de_ejemplo(self):
        ctrl = ValidacionController()
        dataset = ctrl.cargar_archivo("clientes_ejemplo.csv", (DATOS / "clientes_ejemplo.csv").read_bytes())
        self.assertEqual(ctrl.csv_file.separador, ",")
        self.assertEqual(ctrl.csv_file.nombre_codificacion, "UTF-8")
        # RF02: filas y columnas; RF03: columnas identificadas
        self.assertEqual(dataset.numero_filas, 20)
        self.assertEqual(dataset.numero_columnas, 7)
        self.assertEqual(
            [c.nombre for c in dataset.columnas],
            ["id", "nombre", "edad", "fecha_registro", "ciudad", "saldo", "activo"],
        )
        self.assertEqual([c.posicion for c in dataset.columnas], list(range(1, 8)))

    def test_r05_punto_y_coma_y_codificacion_de_excel(self):
        ctrl = ValidacionController()
        ctrl.cargar_archivo("ventas.csv", (DATOS / "ventas_excel_punto_y_coma.csv").read_bytes())
        self.assertEqual(ctrl.csv_file.separador, ";")
        self.assertEqual(ctrl.csv_file.codificacion, "cp1252")
        self.assertIn("Café molido 500 g", ctrl.dataset.datos["producto"].tolist())

    def test_r05_utf8_con_bom(self):
        ctrl = ValidacionController()
        ctrl.cargar_archivo("bom.csv", "﻿nombre,edad\nAna,3\n".encode("utf-8"))
        self.assertEqual(ctrl.csv_file.nombre_codificacion, "UTF-8 con BOM")
        self.assertEqual(ctrl.dataset.columnas[0].nombre, "nombre")

    def test_r05_tabulacion_y_comillas_con_separador_interno(self):
        ctrl = controlador_con('a\tb\n"x, y"\t1\nz\t2\n')
        self.assertEqual(ctrl.csv_file.separador, "\t")
        ctrl = controlador_con('nombre,ciudad\n"Pérez, Ana",Cali\n"Gil, Luis",Bogotá\n')
        self.assertEqual(ctrl.dataset.datos.iloc[0, 0], "Pérez, Ana")

    def test_separador_elegido_por_el_usuario(self):
        ctrl = controlador_con("a;b\n1;2\n", separador=",")
        self.assertEqual(ctrl.dataset.numero_columnas, 1)

    def test_rnf04_rechaza_extension_distinta(self):
        with self.assertRaisesRegex(CsvFileError, "extensión .csv"):
            controlador_con("a,b\n1,2\n", nombre="datos.xlsx")

    def test_rnf04_rechaza_archivo_vacio(self):
        with self.assertRaisesRegex(CsvFileError, "vacío"):
            ValidacionController().cargar_archivo("vacio.csv", b"")
        with self.assertRaisesRegex(CsvFileError, "espacios"):
            ValidacionController().cargar_archivo("blanco.csv", b"   \n\n")

    def test_r04_rechaza_archivo_que_supera_el_tamano_maximo(self):
        with mock.patch.object(config, "MAX_TAMANIO_MB", 0.00001):
            with self.assertRaisesRegex(CsvFileError, "máximo permitido"):
                controlador_con("a,b\n1,2\n3,4\n")

    def test_rnf04_linea_con_campos_de_mas(self):
        with self.assertRaisesRegex(CsvFileError, "La línea 3 del archivo tiene 3 campos"):
            controlador_con("a,b\n1,2\n3,4,5\n")

    def test_rnf04_codificacion_forzada_incorrecta(self):
        with self.assertRaisesRegex(CsvFileError, "codificación"):
            ValidacionController().cargar_archivo(
                "x.csv", "a,b\nñ,1\n".encode("cp1252"), codificacion="utf-8-sig"
            )

    def test_carga_fallida_conserva_el_archivo_anterior(self):
        ctrl = controlador_con("a,b\n1,2\n")
        with self.assertRaises(CsvFileError):
            ctrl.cargar_archivo("malo.txt", b"a,b\n")
        self.assertEqual(ctrl.dataset.numero_filas, 1)

    def test_encabezado_vacio_y_repetido(self):
        ctrl = controlador_con("a,,a\n1,2,3\n")
        self.assertEqual([c.nombre for c in ctrl.dataset.columnas], ["a", "columna_2", "a (2)"])
        self.assertEqual(len(ctrl.advertencias), 2)

    def test_solo_encabezado(self):
        ctrl = controlador_con("a,b\n")
        self.assertEqual(ctrl.dataset.numero_filas, 0)
        self.assertTrue(any("solo tiene encabezado" in a for a in ctrl.advertencias))
        reporte = ctrl.ejecutar_validacion()
        self.assertEqual(reporte.total_problemas, 0)

    def test_filas_con_campos_de_menos_quedan_como_nulos(self):
        ctrl = controlador_con("a,b,c\n1,2\n4,5,6\n")
        self.assertEqual(ctrl.dataset.columna("c").cantidad_nulos, 1)

    def test_espacios_alrededor_se_ignoran(self):
        ctrl = controlador_con("a , b\n  1 , x \n")
        self.assertEqual([c.nombre for c in ctrl.dataset.columnas], ["a", "b"])
        self.assertEqual(ctrl.dataset.datos.iloc[0].tolist(), ["1", "x"])


if __name__ == "__main__":
    unittest.main()
