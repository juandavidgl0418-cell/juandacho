"""NullValidator: detecta valores nulos por columna (RF04)."""

from __future__ import annotations

from typing import List

from ..modelos import Dataset, Issue, TipoProblema
from .base import ValidationRule, numero_fila


class NullValidator(ValidationRule):
    nombre_regla = "Nulos"
    tipo_regla = ValidationRule.FIJA
    tipo_problema = TipoProblema.NULO

    def validar(self, dataset: Dataset) -> List[Issue]:
        issues: List[Issue] = []
        for columna in dataset.columnas:
            mascara = dataset.mascara_nulos[columna.nombre]
            descripcion = f"La columna «{columna.nombre}» está vacía en este registro."
            issues.extend(
                self._issue(descripcion, numero_fila(i), columna) for i in mascara[mascara].index
            )
        return issues
