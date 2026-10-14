"""Entidades del modelo de información (MER y diccionario de datos).

Todas las estructuras existen únicamente en memoria durante la sesión; no hay
base de datos ni almacenamiento permanente (RNF05).
"""

from __future__ import annotations

import itertools
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from . import config


class TipoDato:
    NUMERICO = "Numérico"
    TEXTO = "Texto"
    FECHA = "Fecha"
    BOOLEANO = "Booleano"


class TipoProblema:
    NULO = "Nulo"
    DUPLICADO = "Duplicado"
    TIPO_INCONSISTENTE = "TipoInconsistente"
    FUERA_DE_RANGO = "FueraDeRango"

    #: Nombres en lenguaje claro para la interfaz (RNF02, riesgo R18).
    ETIQUETAS = {
        NULO: "Valor nulo",
        DUPLICADO: "Registro duplicado",
        TIPO_INCONSISTENTE: "Tipo inconsistente",
        FUERA_DE_RANGO: "Fuera de rango",
    }


class Severidad:
    CRITICO = "Crítico"
    MAYOR = "Mayor"
    MENOR = "Menor"
    ORDEN = {CRITICO: 0, MAYOR: 1, MENOR: 2}


# Identificadores asignados por el sistema, únicos dentro del proceso.
_contadores: Dict[str, "itertools.count[int]"] = {}


def nuevo_id(entidad: str) -> int:
    if entidad not in _contadores:
        _contadores[entidad] = itertools.count(1)
    return next(_contadores[entidad])


@dataclass
class Column:
    """Columna identificada dentro del Dataset, con su perfil (RF03, RF04, RF06)."""

    id_dataset: int
    nombre: str
    tipo_dato: str
    posicion: int
    cantidad_nulos: int
    id_columna: int = field(default_factory=lambda: nuevo_id("Column"))


class Dataset:
    """Estructura tabular en memoria derivada del CSV; entidad central del modelo.

    ``datos`` guarda todas las celdas como texto (sin espacios al inicio ni al
    final) para que la detección de nulos y la inferencia de tipos sigan reglas
    explícitas y no las conversiones automáticas de Pandas (riesgo R06).
    """

    def __init__(self, datos: pd.DataFrame, id_csv_file: int):
        from . import tipos  # importación local para evitar ciclos

        self.id_dataset = nuevo_id("Dataset")
        self.id_csv_file = id_csv_file
        self.datos = datos.reset_index(drop=True)
        self.mascara_nulos = pd.DataFrame(
            {c: self.datos[c].str.lower().isin(config.VALORES_NULOS) for c in self.datos.columns},
            index=self.datos.index,
        )
        # El Dataset crea las instancias Column (diagrama de secuencia 14.1).
        self.columnas: List[Column] = []
        for posicion, nombre in enumerate(self.datos.columns, start=1):
            valores = self.valores_no_nulos(nombre)
            tipo, _ = tipos.inferir_tipo(valores)
            self.columnas.append(
                Column(
                    id_dataset=self.id_dataset,
                    nombre=nombre,
                    tipo_dato=tipo,
                    posicion=posicion,
                    cantidad_nulos=int(self.mascara_nulos[nombre].sum()),
                )
            )

    @property
    def numero_filas(self) -> int:
        return len(self.datos)

    @property
    def numero_columnas(self) -> int:
        return len(self.columnas)

    def columna(self, nombre: str) -> Column:
        for col in self.columnas:
            if col.nombre == nombre:
                return col
        raise KeyError(f"La columna «{nombre}» no existe en el archivo.")

    def columnas_numericas(self) -> List[Column]:
        return [c for c in self.columnas if c.tipo_dato == TipoDato.NUMERICO]

    def valores_no_nulos(self, nombre: str) -> pd.Series:
        return self.datos.loc[~self.mascara_nulos[nombre], nombre]


@dataclass
class RangoValidacion:
    """Rango numérico definido por el usuario para una columna (RF07)."""

    id_columna: int
    id_regla: int
    nombre_columna: str
    valor_minimo: float
    valor_maximo: float
    id_rango: int = field(default_factory=lambda: nuevo_id("RangoValidacion"))

    def __post_init__(self):
        if self.valor_minimo > self.valor_maximo:
            raise ValueError(
                f"En la columna «{self.nombre_columna}» el valor mínimo "
                f"({self.valor_minimo:g}) no puede ser mayor que el máximo ({self.valor_maximo:g})."
            )


@dataclass
class Issue:
    """Problema individual de calidad detectado por una regla (RF10).

    ``fila`` es el número de registro: 1 corresponde al primer registro debajo
    del encabezado. ``nombre_columna`` se guarda junto con ``id_columna`` para
    presentar el detalle sin consultas adicionales.
    """

    id_regla: int
    tipo_problema: str
    descripcion: str
    severidad: str
    fila: Optional[int] = None
    id_columna: Optional[int] = None
    nombre_columna: Optional[str] = None
    id_reporte: Optional[int] = None
    id_issue: int = field(default_factory=lambda: nuevo_id("Issue"))


class QualityReport:
    """Reporte consolidado del diagnóstico de calidad (RF09, RF10)."""

    COLUMNAS_DETALLE = ["Fila", "Columna", "Tipo de problema", "Severidad", "Descripción"]

    def __init__(self, dataset: Dataset):
        self.id_reporte = nuevo_id("QualityReport")
        self.id_dataset = dataset.id_dataset
        self.dataset = dataset
        self.fecha_generacion = datetime.now()
        self.issues: List[Issue] = []
        self.reglas_ejecutadas: List[str] = []

    def agregar_issues(self, issues: List[Issue]) -> None:
        for issue in issues:
            issue.id_reporte = self.id_reporte
        self.issues.extend(issues)

    @property
    def total_problemas(self) -> int:
        return len(self.issues)

    def conteo_por_tipo(self) -> Dict[str, int]:
        conteo = {t: 0 for t in TipoProblema.ETIQUETAS}
        for issue in self.issues:
            conteo[issue.tipo_problema] += 1
        return conteo

    def conteo_por_severidad(self) -> Dict[str, int]:
        conteo = {s: 0 for s in Severidad.ORDEN}
        for issue in self.issues:
            conteo[issue.severidad] += 1
        return conteo

    def filas_afectadas(self) -> int:
        return len({i.fila for i in self.issues if i.fila is not None})

    def problemas_por_columna(self) -> pd.DataFrame:
        """Perfil por columna: tipo, nulos y problemas de cada clase."""
        conteo = Counter((i.id_columna, i.tipo_problema) for i in self.issues)
        filas = []
        for col in self.dataset.columnas:
            filas.append(
                {
                    "Posición": col.posicion,
                    "Columna": col.nombre,
                    "Tipo de dato": col.tipo_dato,
                    "Valores nulos": col.cantidad_nulos,
                    "% nulos": round(100 * col.cantidad_nulos / self.dataset.numero_filas, 1)
                    if self.dataset.numero_filas
                    else 0.0,
                    "Tipo inconsistente": conteo[(col.id_columna, TipoProblema.TIPO_INCONSISTENTE)],
                    "Fuera de rango": conteo[(col.id_columna, TipoProblema.FUERA_DE_RANGO)],
                }
            )
        return pd.DataFrame(filas)

    def resumen(self) -> dict:
        """Resumen de calidad (RF02, RF04, RF05, RF09)."""
        por_tipo = self.conteo_por_tipo()
        return {
            "id_reporte": self.id_reporte,
            "fecha_generacion": self.fecha_generacion,
            "numero_filas": self.dataset.numero_filas,
            "numero_columnas": self.dataset.numero_columnas,
            "total_problemas": self.total_problemas,
            "nulos": por_tipo[TipoProblema.NULO],
            "duplicados": por_tipo[TipoProblema.DUPLICADO],
            "tipos_inconsistentes": por_tipo[TipoProblema.TIPO_INCONSISTENTE],
            "fuera_de_rango": por_tipo[TipoProblema.FUERA_DE_RANGO],
            "por_severidad": self.conteo_por_severidad(),
            "filas_afectadas": self.filas_afectadas(),
            "reglas_ejecutadas": list(self.reglas_ejecutadas),
        }

    def detalle(
        self,
        tipos: Optional[List[str]] = None,
        columnas: Optional[List[str]] = None,
        severidades: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Detalle de los problemas, con filtros opcionales (RF10).

        ``tipos`` usa los valores del diccionario de datos (p. ej. "Nulo").
        Al filtrar por columnas se excluyen los duplicados, que afectan a la
        fila completa y no a una columna.
        """
        seleccion = self.issues
        if tipos:
            seleccion = [i for i in seleccion if i.tipo_problema in tipos]
        if columnas:
            seleccion = [i for i in seleccion if i.nombre_columna in columnas]
        if severidades:
            seleccion = [i for i in seleccion if i.severidad in severidades]
        posicion = {c.id_columna: c.posicion for c in self.dataset.columnas}
        seleccion = sorted(
            seleccion,
            key=lambda i: (
                i.fila if i.fila is not None else 10**12,
                posicion.get(i.id_columna, 0),
            ),
        )
        return pd.DataFrame(
            [
                {
                    "Fila": i.fila,
                    "Columna": i.nombre_columna or "(fila completa)",
                    "Tipo de problema": TipoProblema.ETIQUETAS[i.tipo_problema],
                    "Severidad": i.severidad,
                    "Descripción": i.descripcion,
                }
                for i in seleccion
            ],
            columns=self.COLUMNAS_DETALLE,
        )
