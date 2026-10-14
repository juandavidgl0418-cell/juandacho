"""DuplicateValidator: detecta registros duplicados (RF05).

Un registro es duplicado cuando todas sus celdas son idénticas a las de un
registro anterior (sin tener en cuenta espacios al inicio o al final).
La primera aparición no se reporta; cada repetición se reporta una vez.
"""

from __future__ import annotations

from typing import List

import pandas as pd

from ..modelos import Dataset, Issue, TipoProblema
from .base import ValidationRule, numero_fila


class DuplicateValidator(ValidationRule):
    nombre_regla = "Duplicados"
    tipo_regla = ValidationRule.FIJA
    tipo_problema = TipoProblema.DUPLICADO

    def validar(self, dataset: Dataset) -> List[Issue]:
        datos = dataset.datos
        if datos.empty:
            return []
        duplicado = datos.duplicated(keep="first")
        if not duplicado.any():
            return []
        grupo = datos.groupby(list(datos.columns), sort=False, dropna=False).ngroup()
        primera = pd.Series(datos.index, index=datos.index).groupby(grupo).transform("min")
        return [
            self._issue(
                f"El registro es idéntico al de la fila {numero_fila(primera[i])}.",
                numero_fila(i),
            )
            for i in duplicado[duplicado].index
        ]
