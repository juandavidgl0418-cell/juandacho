"""DataTypeValidator: identifica inconsistencias de tipo en cada columna (RF06).

El tipo de cada columna se infiere al crear el Dataset (ver ``dqv.tipos``).
Esta regla reporta los valores que no corresponden con ese tipo.
"""

from __future__ import annotations

from typing import List

from .. import config, tipos
from ..modelos import Dataset, Issue, TipoDato, TipoProblema
from .base import ValidationRule, numero_fila

_EXPLICACION = {
    TipoDato.NUMERICO: "no es un número",
    TipoDato.FECHA: f"no es una fecha válida (formatos aceptados: {config.FORMATOS_FECHA_LEGIBLES})",
    TipoDato.BOOLEANO: "no es un valor sí/no (sí, no, verdadero, falso, true, false)",
}


class DataTypeValidator(ValidationRule):
    nombre_regla = "Tipos"
    tipo_regla = ValidationRule.FIJA
    tipo_problema = TipoProblema.TIPO_INCONSISTENTE

    def validar(self, dataset: Dataset) -> List[Issue]:
        issues: List[Issue] = []
        for columna in dataset.columnas:
            if columna.tipo_dato == TipoDato.TEXTO:
                continue
            valores = dataset.valores_no_nulos(columna.nombre)
            conforme = tipos.mascara_conforme(columna.tipo_dato, valores)
            for indice, valor in valores[~conforme].items():
                issues.append(
                    self._issue(
                        f"El valor «{valor}» {_EXPLICACION[columna.tipo_dato]}; "
                        f"la columna «{columna.nombre}» es de tipo {columna.tipo_dato}.",
                        numero_fila(indice),
                        columna,
                    )
                )
        return issues
