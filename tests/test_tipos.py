"""Pruebas de la inferencia de tipos de dato (RF06, riesgo R06)."""

import math
import unittest

import pandas as pd

from dqv import TipoDato, tipos


def serie(valores):
    return pd.Series(valores, dtype=str)


class PruebasTipos(unittest.TestCase):
    def test_conversion_numerica_formatos(self):
        casos = {
            ("12.500,50", "4.200", "3.150,75"): [12500.5, 4200.0, 3150.75],
            ("1,234,567.89", "12"): [1234567.89, 12.0],
            ("3,5", "-4"): [3.5, -4.0],
            ("1e3", "+7", "0.25"): [1000.0, 7.0, 0.25],
        }
        for entrada, esperado in casos.items():
            self.assertEqual(tipos.convertir_numerico(serie(list(entrada))).tolist(), esperado, entrada)

    def test_valores_no_numericos(self):
        resultado = tipos.convertir_numerico(serie(["abc", "inf", "12abc", "1.2.3"]))
        self.assertTrue(all(math.isnan(v) for v in resultado))

    def test_fechas_validas_e_invalidas(self):
        mascara = tipos.mascara_fecha(
            serie(["2024-01-15", "15/05/2024", "15-05-2024", "2024/05/15", "2024-02-30", "2024-13-01", "ayer"])
        )
        self.assertEqual(mascara.tolist(), [True, True, True, True, False, False, False])

    def test_inferencia_por_umbral(self):
        self.assertEqual(tipos.inferir_tipo(serie(["1", "2", "3", "4", "x"]))[0], TipoDato.NUMERICO)  # 80 %
        self.assertEqual(tipos.inferir_tipo(serie(["1", "2", "3", "x", "y"]))[0], TipoDato.TEXTO)      # 60 %
        self.assertEqual(tipos.inferir_tipo(serie(["si", "no", "Sí", "NO"]))[0], TipoDato.BOOLEANO)
        self.assertEqual(tipos.inferir_tipo(serie(["0", "1", "1"]))[0], TipoDato.NUMERICO)
        self.assertEqual(tipos.inferir_tipo(serie(["2024-01-01", "01/02/2024"]))[0], TipoDato.FECHA)
        self.assertEqual(tipos.inferir_tipo(serie([]))[0], TipoDato.TEXTO)

    def test_mascara_de_la_inferencia_marca_los_inconsistentes(self):
        tipo, mascara = tipos.inferir_tipo(serie(["10", "20", "treinta", "40", "50"]))
        self.assertEqual(tipo, TipoDato.NUMERICO)
        self.assertEqual(mascara.tolist(), [True, True, False, True, True])


if __name__ == "__main__":
    unittest.main()
