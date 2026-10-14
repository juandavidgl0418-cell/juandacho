"""Contrato común de las reglas de validación (clase abstracta ValidationRule)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from .. import config
from ..modelos import Column, Dataset, Issue, nuevo_id


class ValidationRule(ABC):
    """Cada regla concreta implementa ``validar(dataset)`` y retorna una lista de Issue.

    Para agregar una nueva validación basta con crear una subclase y registrarla
    en ValidationService, sin modificar las demás reglas (RNF03).
    """

    FIJA = "Fija"
    OPCIONAL = "Opcional"

    nombre_regla: str = ""
    tipo_regla: str = FIJA
    tipo_problema: str = ""

    def __init__(self):
        self.id_regla = nuevo_id("ValidationRule")

    @abstractmethod
    def validar(self, dataset: Dataset) -> List[Issue]:
        """Ejecuta la regla sobre el Dataset."""

    def esta_configurada(self) -> bool:
        """Las reglas opcionales solo se ejecutan si el usuario las configuró."""
        return True

    def _issue(self, descripcion: str, fila: Optional[int] = None, columna: Optional[Column] = None) -> Issue:
        return Issue(
            id_regla=self.id_regla,
            tipo_problema=self.tipo_problema,
            descripcion=descripcion,
            severidad=config.SEVERIDAD_POR_TIPO[self.tipo_problema],
            fila=fila,
            id_columna=columna.id_columna if columna else None,
            nombre_columna=columna.nombre if columna else None,
        )


def numero_fila(indice) -> int:
    """Convierte el índice interno (base 0) en número de registro (base 1)."""
    return int(indice) + 1
