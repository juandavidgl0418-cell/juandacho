"""Reglas explícitas de inferencia de tipos de dato (RF06, riesgo R06).

Cada función recibe una Serie de texto sin valores nulos y devuelve una máscara
booleana que indica qué valores se ajustan al tipo.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd

from . import config
from .modelos import TipoDato

_MILES_COMA = r"[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?"   # 1,234,567.89
_MILES_PUNTO = r"[-+]?\d{1,3}(?:\.\d{3})+(?:,\d+)?"  # 1.234.567,89
_DECIMAL_COMA = r"[-+]?\d+,\d+"                      # 3,5


#: Valores que solo pueden leerse con coma decimal: 12.500,50 o 3,5 / 3,25 / 3,1416
#: («1,234» es ambiguo y no cuenta como evidencia).
_EVIDENCIA_COMA_DECIMAL = r"[-+]?\d{1,3}(?:\.\d{3})+,\d+|[-+]?\d+,(?:\d{1,2}|\d{4,})"


def usa_coma_decimal(texto: pd.Series) -> bool:
    """Indica si la columna usa coma decimal y punto de miles (formato de Excel en español)."""
    return bool(texto.str.fullmatch(_EVIDENCIA_COMA_DECIMAL).any())


def convertir_numerico(valores: pd.Series) -> pd.Series:
    """Convierte texto a número; lo que no es numérico queda como NaN.

    El formato se decide por columna: si algún valor solo puede leerse con coma
    decimal (p. ej. «12.500,50» o «3,5»), toda la columna se interpreta con punto
    de miles y coma decimal, de modo que «4.200» vale 4200. En caso contrario se
    usa el formato estándar (1234.5, -3, 1e5) y se acepta coma de miles (1,234,567.8).
    """
    texto = valores.astype(str).str.strip()
    resultado = pd.Series(np.nan, index=texto.index, dtype="float64")
    if len(texto) == 0:
        return resultado
    if usa_coma_decimal(texto):
        latino = texto.str.fullmatch(_MILES_PUNTO) | texto.str.fullmatch(_DECIMAL_COMA)
        if latino.any():
            resultado[latino] = pd.to_numeric(
                texto[latino].str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
                errors="coerce",
            )
        resto = ~latino
    else:
        miles_coma = texto.str.fullmatch(_MILES_COMA)
        if miles_coma.any():
            resultado[miles_coma] = pd.to_numeric(
                texto[miles_coma].str.replace(",", "", regex=False), errors="coerce"
            )
        resto = ~miles_coma
    if resto.any():
        resultado[resto] = pd.to_numeric(texto[resto], errors="coerce").astype("float64")
    # inf/-inf no se consideran números válidos para el análisis.
    resultado[np.isinf(resultado)] = np.nan
    return resultado


def mascara_numerico(valores: pd.Series) -> pd.Series:
    return convertir_numerico(valores).notna()


def mascara_booleano(valores: pd.Series) -> pd.Series:
    return valores.astype(str).str.strip().str.lower().isin(config.VALORES_BOOLEANOS)


def mascara_fecha(valores: pd.Series) -> pd.Series:
    texto = valores.astype(str).str.strip()
    mascara = pd.Series(False, index=texto.index)
    for formato in config.FORMATOS_FECHA:
        pendientes = ~mascara
        if not pendientes.any():
            break
        convertidas = pd.to_datetime(texto[pendientes], format=formato, errors="coerce")
        mascara[convertidas[convertidas.notna()].index] = True
    return mascara


_MASCARAS = {
    TipoDato.BOOLEANO: mascara_booleano,
    TipoDato.NUMERICO: mascara_numerico,
    TipoDato.FECHA: mascara_fecha,
}


def mascara_conforme(tipo: str, valores: pd.Series) -> pd.Series:
    """Indica qué valores se ajustan al tipo dado (Texto acepta cualquier valor)."""
    if tipo == TipoDato.TEXTO:
        return pd.Series(True, index=valores.index)
    return _MASCARAS[tipo](valores)


def inferir_tipo(valores: pd.Series) -> Tuple[str, pd.Series]:
    """Determina el tipo predominante de una columna.

    Se prueban Booleano, Numérico y Fecha, en ese orden. Gana el tipo con mayor
    proporción de valores conformes, siempre que alcance ``UMBRAL_TIPO``; si
    ninguno lo alcanza, la columna es Texto. Una columna sin valores es Texto.
    """
    if len(valores) == 0:
        return TipoDato.TEXTO, pd.Series(True, index=valores.index)
    mejor_tipo, mejor_mascara, mejor_proporcion = None, None, 0.0
    for tipo, funcion in _MASCARAS.items():
        mascara = funcion(valores)
        proporcion = float(mascara.mean())
        if proporcion >= config.UMBRAL_TIPO and proporcion > mejor_proporcion:
            mejor_tipo, mejor_mascara, mejor_proporcion = tipo, mascara, proporcion
            if proporcion == 1.0:
                break
    if mejor_tipo is None:
        return TipoDato.TEXTO, pd.Series(True, index=valores.index)
    return mejor_tipo, mejor_mascara
