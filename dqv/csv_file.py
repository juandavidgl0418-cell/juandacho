"""CsvFile: representa el archivo cargado, lo verifica y lo convierte en Dataset."""

from __future__ import annotations

import csv
import io
import re
from collections import Counter
from typing import List, Optional

import pandas as pd

from . import config
from .modelos import Dataset, nuevo_id


class CsvFileError(Exception):
    """Error de carga con un mensaje comprensible para el usuario (RNF04)."""


class CsvFile:
    def __init__(
        self,
        nombre_archivo: str,
        contenido: bytes,
        separador: Optional[str] = None,
        codificacion: Optional[str] = None,
    ):
        """
        :param separador: separador elegido por el usuario o ``None`` para detectarlo.
        :param codificacion: codificación elegida por el usuario o ``None`` para detectarla.
        """
        self.id_csv_file = nuevo_id("CsvFile")
        self.nombre_archivo = (nombre_archivo or "").strip()
        self.contenido = contenido or b""
        self.tamanio_bytes = len(self.contenido)
        self._separador_solicitado = separador
        self._codificacion_solicitada = codificacion
        self.codificacion: Optional[str] = None
        self.separador: Optional[str] = None
        self.advertencias: List[str] = []
        self._texto: Optional[str] = None

    # ------------------------------------------------------------------ verificar
    def verificar(self) -> None:
        """Valida nombre, tamaño, codificación y separador. Lanza CsvFileError."""
        if not self.nombre_archivo.lower().endswith(config.EXTENSIONES_PERMITIDAS):
            raise CsvFileError(
                f"El archivo «{self.nombre_archivo}» no tiene extensión .csv. "
                "Guárdelo como CSV y vuelva a cargarlo."
            )
        if self.tamanio_bytes == 0:
            raise CsvFileError("El archivo está vacío (0 bytes). Verifique que se haya guardado correctamente.")
        limite = config.MAX_TAMANIO_MB * 1024 * 1024
        if self.tamanio_bytes > limite:
            raise CsvFileError(
                f"El archivo pesa {self.tamanio_bytes / 1024 / 1024:.1f} MB y el máximo permitido es "
                f"{config.MAX_TAMANIO_MB} MB. Divida el archivo en partes más pequeñas."
            )
        self._texto = self._decodificar()
        if not self._texto.strip():
            raise CsvFileError("El archivo solo contiene espacios o líneas en blanco.")
        self.separador = self._separador_solicitado or self._detectar_separador(self._texto)

    def _decodificar(self) -> str:
        if self._codificacion_solicitada:
            try:
                texto = self.contenido.decode(self._codificacion_solicitada)
            except (UnicodeDecodeError, LookupError):
                nombre = config.CODIFICACIONES.get(self._codificacion_solicitada, self._codificacion_solicitada)
                raise CsvFileError(
                    f"El archivo no se puede leer con la codificación {nombre}. "
                    "Elija «Automática» en las opciones de lectura o guarde el archivo como CSV UTF-8."
                )
            self.codificacion = self._codificacion_solicitada
            return texto.lstrip("﻿")
        for codificacion in config.CODIFICACIONES:
            try:
                texto = self.contenido.decode(codificacion)
            except UnicodeDecodeError:
                continue
            self.codificacion = codificacion
            return texto
        raise CsvFileError("No fue posible identificar la codificación del archivo.")  # pragma: no cover

    @staticmethod
    def _detectar_separador(texto: str) -> str:
        """Elige el separador que produce un número de campos más consistente."""
        lineas = [l for l in texto.splitlines() if l.strip()][: config.LINEAS_MUESTRA_SEPARADOR]
        mejor, mejor_puntaje = ",", None
        for separador in config.SEPARADORES:
            try:
                conteos = [len(fila) for fila in csv.reader(lineas, delimiter=separador)]
            except csv.Error:
                continue
            if not conteos:
                continue
            moda, frecuencia = Counter(conteos).most_common(1)[0]
            if moda < 2:
                continue
            puntaje = (conteos[0] == moda, frecuencia / len(conteos), moda)
            if mejor_puntaje is None or puntaje > mejor_puntaje:
                mejor, mejor_puntaje = separador, puntaje
        return mejor

    # -------------------------------------------------------- convertir a dataset
    def convertir_a_dataset(self) -> Dataset:
        if self._texto is None:
            self.verificar()
        try:
            crudo = pd.read_csv(
                io.StringIO(self._texto),
                sep=self.separador,
                header=None,
                dtype=str,
                keep_default_na=False,
                na_filter=False,
                skip_blank_lines=True,
                engine="c",
            )
        except pd.errors.EmptyDataError:
            raise CsvFileError("El archivo no contiene datos ni encabezado.")
        except pd.errors.ParserError as error:
            raise CsvFileError(self._mensaje_error_lectura(str(error)))
        except Exception as error:  # cualquier otro error de lectura
            raise CsvFileError(f"No fue posible leer el archivo como CSV ({error}).")

        crudo = crudo.fillna("")
        encabezado = [str(v).strip() for v in crudo.iloc[0].tolist()]
        datos = crudo.iloc[1:].reset_index(drop=True)
        nombres = self._normalizar_encabezado(encabezado)
        datos = pd.DataFrame(
            {nombre: datos.iloc[:, i].astype(str).str.strip() for i, nombre in enumerate(nombres)},
            index=datos.index,
            columns=nombres,
        )

        if len(datos.columns) == 1 and self._separador_solicitado is None:
            self.advertencias.append(
                "Solo se identificó una columna. Si el archivo usa otro separador, "
                "elíjalo en «Opciones de lectura»."
            )
        if len(datos) == 0:
            self.advertencias.append("El archivo solo tiene encabezado; no contiene registros para validar.")
        return Dataset(datos, self.id_csv_file)

    def _normalizar_encabezado(self, encabezado: List[str]) -> List[str]:
        nombres: List[str] = []
        vacias, repetidas = [], []
        for posicion, nombre in enumerate(encabezado, start=1):
            if not nombre:
                nombre = f"columna_{posicion}"
                vacias.append(posicion)
            base, k = nombre, 2
            while nombre in nombres:
                nombre = f"{base} ({k})"
                k += 1
            if nombre != base:
                repetidas.append(base)
            nombres.append(nombre)
        if vacias:
            self.advertencias.append(
                "Las columnas en las posiciones "
                + ", ".join(map(str, vacias))
                + " no tienen nombre en el encabezado; se nombraron como «columna_N»."
            )
        if repetidas:
            self.advertencias.append(
                "El encabezado repite los nombres "
                + ", ".join(f"«{n}»" for n in dict.fromkeys(repetidas))
                + "; se agregó un número para distinguirlos."
            )
        return nombres

    @staticmethod
    def _mensaje_error_lectura(detalle: str) -> str:
        m = re.search(r"Expected (\d+) fields in line (\d+), saw (\d+)", detalle)
        if m:
            esperados, linea, encontrados = m.groups()
            return (
                f"La línea {linea} del archivo tiene {encontrados} campos y el encabezado tiene {esperados}. "
                "Revise el separador elegido o si hay comillas sin cerrar en esa línea."
            )
        if "EOF inside string" in detalle:
            return "El archivo tiene comillas sin cerrar. Revise las celdas que contienen comillas (\")."
        return f"No fue posible leer el archivo como CSV. Detalle técnico: {detalle}"

    # ------------------------------------------------------------------- display
    @property
    def nombre_codificacion(self) -> str:
        if self.codificacion == "utf-8-sig" and self.contenido.startswith(b"\xef\xbb\xbf"):
            return "UTF-8 con BOM"
        return config.CODIFICACIONES.get(self.codificacion, self.codificacion or "—")

    @property
    def nombre_separador(self) -> str:
        return config.SEPARADORES.get(self.separador, repr(self.separador))
