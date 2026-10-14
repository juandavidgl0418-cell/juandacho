"""ValidacionController: único punto de entrada de la interfaz a la lógica del sistema."""

from __future__ import annotations

from typing import List, Optional

import pandas as pd

from .csv_file import CsvFile, CsvFileError
from .modelos import Dataset, QualityReport, RangoValidacion
from .servicio import ValidationService


class ValidacionController:
    def __init__(self):
        self.servicio = ValidationService()
        self.csv_file: Optional[CsvFile] = None
        self.dataset: Optional[Dataset] = None
        self.reporte: Optional[QualityReport] = None

    # ------------------------------------------------- CU01 Cargar archivo CSV
    def cargar_archivo(
        self,
        nombre_archivo: str,
        contenido: bytes,
        separador: Optional[str] = None,
        codificacion: Optional[str] = None,
    ) -> Dataset:
        """Verifica el archivo y lo convierte en Dataset. Lanza CsvFileError (RNF04)."""
        csv_file = CsvFile(nombre_archivo, contenido, separador, codificacion)
        csv_file.verificar()
        dataset = csv_file.convertir_a_dataset()
        # Solo se reemplaza el estado si la carga fue exitosa.
        self.csv_file, self.dataset, self.reporte = csv_file, dataset, None
        self.servicio.limpiar_rangos()
        return dataset

    @property
    def advertencias(self) -> List[str]:
        return list(self.csv_file.advertencias) if self.csv_file else []

    # ------------------------------------------ CU06 Analizar estructura y tipos
    def obtener_estructura(self) -> pd.DataFrame:
        dataset = self._dataset_requerido()
        n = dataset.numero_filas
        return pd.DataFrame(
            [
                {
                    "Posición": c.posicion,
                    "Columna": c.nombre,
                    "Tipo de dato": c.tipo_dato,
                    "Valores nulos": c.cantidad_nulos,
                    "% nulos": round(100 * c.cantidad_nulos / n, 1) if n else 0.0,
                }
                for c in dataset.columnas
            ]
        )

    def columnas_numericas(self) -> List[str]:
        return [c.nombre for c in self._dataset_requerido().columnas_numericas()]

    def limites_observados(self, nombre_columna: str):
        """Mínimo y máximo presentes en una columna numérica (ayuda para definir el rango)."""
        from . import tipos

        dataset = self._dataset_requerido()
        numeros = tipos.convertir_numerico(dataset.valores_no_nulos(nombre_columna)).dropna()
        if numeros.empty:
            return None, None
        return float(numeros.min()), float(numeros.max())

    # --------------------------------------------- CU03 Definir rango válido
    def definir_rango(self, nombre_columna: str, minimo: float, maximo: float) -> RangoValidacion:
        rango = self.servicio.registrar_rango(self._dataset_requerido(), nombre_columna, minimo, maximo)
        self.reporte = None  # la configuración cambió: el reporte anterior ya no aplica
        return rango

    def quitar_rango(self, nombre_columna: str) -> None:
        self.servicio.quitar_rango(nombre_columna)
        self.reporte = None

    @property
    def rangos(self) -> List[RangoValidacion]:
        return self.servicio.rangos

    # ------------------------------------ CU02 Ejecutar validación de calidad
    def ejecutar_validacion(self) -> QualityReport:
        self.reporte = self.servicio.validar(self._dataset_requerido())
        return self.reporte

    # -------------------------------------- CU04 / CU05 Consultar el reporte
    def obtener_resumen(self) -> dict:
        return self._reporte_requerido().resumen()

    def obtener_problemas_por_columna(self) -> pd.DataFrame:
        return self._reporte_requerido().problemas_por_columna()

    def obtener_detalle(self, tipos=None, columnas=None, severidades=None) -> pd.DataFrame:
        return self._reporte_requerido().detalle(tipos, columnas, severidades)

    # ------------------------------------------------------------- auxiliares
    def _dataset_requerido(self) -> Dataset:
        if self.dataset is None:
            raise CsvFileError("Primero cargue un archivo CSV.")
        return self.dataset

    def _reporte_requerido(self) -> QualityReport:
        if self.reporte is None:
            raise RuntimeError("Primero ejecute la validación.")
        return self.reporte
