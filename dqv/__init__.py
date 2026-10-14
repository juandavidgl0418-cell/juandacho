"""DataQuality Validator: validación básica de calidad de archivos CSV."""

from .controlador import ValidacionController
from .csv_file import CsvFile, CsvFileError
from .modelos import Column, Dataset, Issue, QualityReport, RangoValidacion, Severidad, TipoDato, TipoProblema
from .servicio import ValidationService

__version__ = "1.0.0"

__all__ = [
    "ValidacionController",
    "ValidationService",
    "CsvFile",
    "CsvFileError",
    "Dataset",
    "Column",
    "Issue",
    "QualityReport",
    "RangoValidacion",
    "TipoDato",
    "TipoProblema",
    "Severidad",
]
