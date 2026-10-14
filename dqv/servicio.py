"""ValidationService: orquesta las reglas y construye el reporte de calidad."""

from __future__ import annotations

from typing import List

from .modelos import Dataset, QualityReport, RangoValidacion
from .reglas import DataTypeValidator, DuplicateValidator, NullValidator, RangeValidator, ValidationRule


class ValidationService:
    def __init__(self):
        self.validador_rango = RangeValidator()
        #: Catálogo de reglas registradas (entidad ValidationRule del MER).
        self.reglas: List[ValidationRule] = [
            NullValidator(),
            DuplicateValidator(),
            DataTypeValidator(),
            self.validador_rango,
        ]

    def registrar_rango(self, dataset: Dataset, nombre_columna: str, minimo: float, maximo: float) -> RangoValidacion:
        return self.validador_rango.configurar_rango(dataset, nombre_columna, minimo, maximo)

    def quitar_rango(self, nombre_columna: str) -> None:
        self.validador_rango.quitar_rango(nombre_columna)

    def limpiar_rangos(self) -> None:
        self.validador_rango.limpiar()

    @property
    def rangos(self) -> List[RangoValidacion]:
        return self.validador_rango.rangos

    def validar(self, dataset: Dataset) -> QualityReport:
        """Ejecuta las reglas fijas y las opcionales configuradas (diagrama 14.2)."""
        reporte = QualityReport(dataset)
        for regla in self.reglas:
            if regla.tipo_regla == ValidationRule.OPCIONAL and not regla.esta_configurada():
                continue
            reporte.agregar_issues(regla.validar(dataset))
            reporte.reglas_ejecutadas.append(regla.nombre_regla)
        return reporte
