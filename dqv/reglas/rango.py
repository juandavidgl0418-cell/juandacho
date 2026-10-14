"""RangeValidator: verifica valores numéricos fuera del rango definido (RF07, RF08).

Es una regla opcional (relación «extend» del caso de uso CU03): solo se ejecuta
si el usuario definió al menos un rango. Los valores nulos o no numéricos de la
columna se omiten porque ya los reportan NullValidator y DataTypeValidator.
"""

from __future__ import annotations

from typing import Dict, List

from .. import tipos
from ..modelos import Dataset, Issue, RangoValidacion, TipoDato, TipoProblema
from .base import ValidationRule, numero_fila


class RangeValidator(ValidationRule):
    nombre_regla = "Rango"
    tipo_regla = ValidationRule.OPCIONAL
    tipo_problema = TipoProblema.FUERA_DE_RANGO

    def __init__(self):
        super().__init__()
        self._rangos: Dict[str, RangoValidacion] = {}

    # Configuración (diagrama de secuencia 14.3)
    def configurar_rango(self, dataset: Dataset, nombre_columna: str, minimo: float, maximo: float) -> RangoValidacion:
        columna = dataset.columna(nombre_columna)
        if columna.tipo_dato != TipoDato.NUMERICO:
            raise ValueError(
                f"Solo se puede definir un rango en columnas numéricas; «{nombre_columna}» es de tipo {columna.tipo_dato}."
            )
        rango = RangoValidacion(
            id_columna=columna.id_columna,
            id_regla=self.id_regla,
            nombre_columna=nombre_columna,
            valor_minimo=float(minimo),
            valor_maximo=float(maximo),
        )
        self._rangos[nombre_columna] = rango  # una columna tiene como máximo un rango (1 : 0..1)
        return rango

    def quitar_rango(self, nombre_columna: str) -> None:
        self._rangos.pop(nombre_columna, None)

    def limpiar(self) -> None:
        self._rangos.clear()

    @property
    def rangos(self) -> List[RangoValidacion]:
        return list(self._rangos.values())

    def esta_configurada(self) -> bool:
        return bool(self._rangos)

    def validar(self, dataset: Dataset) -> List[Issue]:
        issues: List[Issue] = []
        for rango in self._rangos.values():
            columna = dataset.columna(rango.nombre_columna)
            valores = dataset.valores_no_nulos(columna.nombre)
            numeros = tipos.convertir_numerico(valores)
            debajo = numeros < rango.valor_minimo
            encima = numeros > rango.valor_maximo
            for indice in numeros[debajo | encima].index:
                if debajo[indice]:
                    motivo = f"es menor que el mínimo permitido ({rango.valor_minimo:g})"
                else:
                    motivo = f"es mayor que el máximo permitido ({rango.valor_maximo:g})"
                issues.append(
                    self._issue(
                        f"El valor «{valores[indice]}» {motivo} en la columna «{columna.nombre}»; "
                        f"rango válido: {rango.valor_minimo:g} a {rango.valor_maximo:g}.",
                        numero_fila(indice),
                        columna,
                    )
                )
        return issues
