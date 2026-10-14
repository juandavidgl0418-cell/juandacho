"""Pruebas de las reglas de validación y del reporte (RF04 a RF10, RNF03)."""

import unittest

from dqv import Severidad, TipoDato, TipoProblema, ValidacionController
from dqv.reglas import ValidationRule

from .utilidades import DATOS, controlador_con


def issues_de(reporte, tipo):
    return [i for i in reporte.issues if i.tipo_problema == tipo]


class PruebasNulos(unittest.TestCase):
    def test_rf04_nulos_por_columna_y_fila(self):
        ctrl = controlador_con("a,b\n1,\n,NA\n3,ok\n4,null\n")
        self.assertEqual([c.cantidad_nulos for c in ctrl.dataset.columnas], [1, 3])
        nulos = issues_de(ctrl.ejecutar_validacion(), TipoProblema.NULO)
        self.assertEqual(sorted((i.nombre_columna, i.fila) for i in nulos), [("a", 2), ("b", 1), ("b", 2), ("b", 4)])
        self.assertTrue(all(i.severidad == Severidad.MENOR for i in nulos))


class PruebasDuplicados(unittest.TestCase):
    def test_rf05_registros_duplicados_y_primera_aparicion(self):
        ctrl = controlador_con("a,b\n1,x\n2,y\n1,x\n1, x \n3,z\n2,y\n")
        duplicados = issues_de(ctrl.ejecutar_validacion(), TipoProblema.DUPLICADO)
        self.assertEqual([i.fila for i in duplicados], [3, 4, 6])
        self.assertIn("fila 1", duplicados[0].descripcion)
        self.assertIn("fila 2", duplicados[2].descripcion)
        self.assertTrue(all(i.id_columna is None for i in duplicados))

    def test_sin_duplicados(self):
        ctrl = controlador_con("a\n1\n2\n")
        self.assertEqual(issues_de(ctrl.ejecutar_validacion(), TipoProblema.DUPLICADO), [])


class PruebasTiposInconsistentes(unittest.TestCase):
    def test_rf06_valor_no_numerico_en_columna_numerica(self):
        ctrl = controlador_con("edad\n10\n20\ntreinta\n40\n50\n")
        self.assertEqual(ctrl.dataset.columna("edad").tipo_dato, TipoDato.NUMERICO)
        inconsistentes = issues_de(ctrl.ejecutar_validacion(), TipoProblema.TIPO_INCONSISTENTE)
        self.assertEqual([(i.fila, i.nombre_columna) for i in inconsistentes], [(3, "edad")])
        self.assertIn("treinta", inconsistentes[0].descripcion)

    def test_columna_de_texto_no_genera_inconsistencias(self):
        ctrl = controlador_con("nombre\nAna\n12\nLuis\n")
        self.assertEqual(issues_de(ctrl.ejecutar_validacion(), TipoProblema.TIPO_INCONSISTENTE), [])

    def test_fecha_inexistente(self):
        ctrl = controlador_con("f\n2024-01-01\n2024-02-30\n2024-03-01\n2024-04-01\n2024-05-01\n")
        inconsistentes = issues_de(ctrl.ejecutar_validacion(), TipoProblema.TIPO_INCONSISTENTE)
        self.assertEqual([i.fila for i in inconsistentes], [2])


class PruebasRango(unittest.TestCase):
    def setUp(self):
        self.ctrl = controlador_con("edad,nombre\n-4,a\n30,b\n135,c\n,d\ntreinta,e\n120,f\n0,g\n")

    def test_rf07_rf08_valores_fuera_de_rango(self):
        self.ctrl.definir_rango("edad", 0, 120)
        reporte = self.ctrl.ejecutar_validacion()
        fuera = issues_de(reporte, TipoProblema.FUERA_DE_RANGO)
        self.assertEqual([i.fila for i in fuera], [1, 3])  # los límites 0 y 120 son válidos
        self.assertIn("menor que el mínimo", fuera[0].descripcion)
        self.assertIn("mayor que el máximo", fuera[1].descripcion)
        self.assertTrue(all(i.severidad == Severidad.CRITICO for i in fuera))
        self.assertIn("Rango", reporte.reglas_ejecutadas)

    def test_regla_opcional_no_se_ejecuta_sin_rango(self):
        reporte = self.ctrl.ejecutar_validacion()
        self.assertNotIn("Rango", reporte.reglas_ejecutadas)
        self.assertEqual(issues_de(reporte, TipoProblema.FUERA_DE_RANGO), [])

    def test_minimo_mayor_que_maximo(self):
        with self.assertRaisesRegex(ValueError, "no puede ser mayor"):
            self.ctrl.definir_rango("edad", 10, 5)

    def test_rango_solo_en_columnas_numericas(self):
        with self.assertRaisesRegex(ValueError, "columnas numéricas"):
            self.ctrl.definir_rango("nombre", 0, 1)

    def test_un_rango_por_columna_y_quitar_rango(self):
        self.ctrl.definir_rango("edad", 0, 10)
        self.ctrl.definir_rango("edad", 0, 200)
        self.assertEqual(len(self.ctrl.rangos), 1)
        self.assertEqual(issues_de(self.ctrl.ejecutar_validacion(), TipoProblema.FUERA_DE_RANGO)[0].fila, 1)
        self.ctrl.quitar_rango("edad")
        self.assertEqual(self.ctrl.rangos, [])

    def test_cambiar_rango_invalida_el_reporte(self):
        self.ctrl.ejecutar_validacion()
        self.ctrl.definir_rango("edad", 0, 120)
        self.assertIsNone(self.ctrl.reporte)

    def test_rango_con_coma_decimal(self):
        ctrl = controlador_con("precio\n4.200\n12.500,50\n800\n", separador=";")
        ctrl.definir_rango("precio", 1000, 10000)
        fuera = issues_de(ctrl.ejecutar_validacion(), TipoProblema.FUERA_DE_RANGO)
        self.assertEqual([i.fila for i in fuera], [2, 3])


class PruebasReporteDeEjemplo(unittest.TestCase):
    """Prueba de extremo a extremo con el archivo de ejemplo y errores conocidos."""

    def setUp(self):
        self.ctrl = ValidacionController()
        self.ctrl.cargar_archivo("clientes_ejemplo.csv", (DATOS / "clientes_ejemplo.csv").read_bytes())
        self.ctrl.definir_rango("edad", 0, 120)
        self.reporte = self.ctrl.ejecutar_validacion()

    def test_rf06_tipos_detectados(self):
        self.assertEqual(
            {c.nombre: c.tipo_dato for c in self.ctrl.dataset.columnas},
            {
                "id": "Numérico",
                "nombre": "Texto",
                "edad": "Numérico",
                "fecha_registro": "Fecha",
                "ciudad": "Texto",
                "saldo": "Numérico",
                "activo": "Booleano",
            },
        )

    def test_rf09_resumen(self):
        r = self.ctrl.obtener_resumen()
        self.assertEqual((r["numero_filas"], r["numero_columnas"]), (20, 7))
        self.assertEqual(
            (r["nulos"], r["duplicados"], r["tipos_inconsistentes"], r["fuera_de_rango"], r["total_problemas"]),
            (4, 2, 5, 2, 13),
        )
        self.assertEqual(r["por_severidad"], {"Crítico": 2, "Mayor": 7, "Menor": 4})
        self.assertEqual(r["filas_afectadas"], 13)
        self.assertEqual(r["total_problemas"], len(self.reporte.issues))

    def test_rf10_detalle_y_filtros(self):
        detalle = self.ctrl.obtener_detalle()
        self.assertEqual(list(detalle.columns), ["Fila", "Columna", "Tipo de problema", "Severidad", "Descripción"])
        self.assertEqual(len(detalle), 13)
        self.assertEqual(detalle["Fila"].tolist(), sorted(detalle["Fila"].tolist()))
        self.assertEqual(len(self.ctrl.obtener_detalle(tipos=["Nulo"])), 4)
        self.assertEqual(len(self.ctrl.obtener_detalle(columnas=["edad"])), 5)
        self.assertEqual(len(self.ctrl.obtener_detalle(severidades=["Crítico"])), 2)

    def test_integridad_referencial(self):
        ids_reglas = {r.id_regla for r in self.ctrl.servicio.reglas}
        ids_columnas = {c.id_columna for c in self.ctrl.dataset.columnas}
        for issue in self.reporte.issues:
            self.assertEqual(issue.id_reporte, self.reporte.id_reporte)
            self.assertIn(issue.id_regla, ids_reglas)
            self.assertTrue(issue.id_columna is None or issue.id_columna in ids_columnas)
            self.assertGreaterEqual(issue.fila, 1)
        self.assertEqual(len({i.id_issue for i in self.reporte.issues}), len(self.reporte.issues))
        self.assertEqual(self.reporte.id_dataset, self.ctrl.dataset.id_dataset)
        self.assertEqual(self.ctrl.dataset.id_csv_file, self.ctrl.csv_file.id_csv_file)

    def test_problemas_por_columna(self):
        tabla = self.ctrl.obtener_problemas_por_columna().set_index("Columna")
        self.assertEqual(tabla.loc["edad", "Valores nulos"], 2)
        self.assertEqual(tabla.loc["edad", "Tipo inconsistente"], 1)
        self.assertEqual(tabla.loc["edad", "Fuera de rango"], 2)


class PruebasModularidad(unittest.TestCase):
    def test_rnf03_se_puede_registrar_una_regla_nueva(self):
        class ReglaDemo(ValidationRule):
            nombre_regla = "Demo"
            tipo_problema = TipoProblema.NULO

            def validar(self, dataset):
                return [self._issue("demo", fila=1)]

        ctrl = controlador_con("a\n1\n")
        ctrl.servicio.reglas.append(ReglaDemo())
        reporte = ctrl.ejecutar_validacion()
        self.assertIn("Demo", reporte.reglas_ejecutadas)
        self.assertEqual(reporte.total_problemas, 1)


if __name__ == "__main__":
    unittest.main()
