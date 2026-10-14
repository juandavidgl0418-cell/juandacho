"""Parámetros de configuración de DataQuality Validator.

Centralizar estos valores permite ajustar el comportamiento del prototipo sin
modificar la lógica de las reglas (RNF03).
"""

# --- Carga de archivos (RF01, RNF04, riesgos R04 y R05) ----------------------

#: Tamaño máximo recomendado del archivo. Debe coincidir con
#: ``server.maxUploadSize`` en ``.streamlit/config.toml`` (riesgo R04).
MAX_TAMANIO_MB = 20

EXTENSIONES_PERMITIDAS = (".csv",)

#: Separadores que se prueban en la detección automática (riesgo R05).
SEPARADORES = {
    ",": "Coma (,)",
    ";": "Punto y coma (;)",
    "\t": "Tabulación",
    "|": "Barra vertical (|)",
}

#: Codificaciones que se prueban en orden. UTF-8 admite archivos con y sin BOM;
#: Windows-1252 es la codificación habitual de Excel en español; Latin-1 nunca
#: falla, por eso va al final (riesgo R05).
CODIFICACIONES = {
    "utf-8-sig": "UTF-8",
    "cp1252": "Windows-1252 (Excel)",
    "latin-1": "Latin-1 (ISO-8859-1)",
}

#: Número de líneas del archivo que se analizan para detectar el separador.
LINEAS_MUESTRA_SEPARADOR = 50

# --- Valores nulos (RF04) -----------------------------------------------------

#: Una celda se considera nula si, sin espacios y en minúsculas, es uno de
#: estos valores.
VALORES_NULOS = frozenset({"", "na", "n/a", "#n/a", "nan", "null", "none", "nulo"})

# --- Inferencia de tipos de dato (RF06, riesgo R06) ---------------------------

#: Proporción mínima de valores no nulos que deben ajustarse a un tipo para que
#: la columna se clasifique con ese tipo. Los valores restantes se reportan como
#: inconsistencias de tipo. Si ningún tipo alcanza el umbral, la columna es Texto.
UMBRAL_TIPO = 0.8

VALORES_BOOLEANOS = frozenset(
    {"true", "false", "verdadero", "falso", "si", "sí", "no", "yes"}
)

#: Formatos de fecha aceptados. Se asume día/mes/año (convención en Colombia).
FORMATOS_FECHA = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
)

FORMATOS_FECHA_LEGIBLES = "AAAA-MM-DD, DD/MM/AAAA, DD-MM-AAAA o AAAA/MM/DD"

# --- Severidad de los problemas (Plan de Gestión de Calidad) ------------------

SEVERIDAD_POR_TIPO = {
    "Nulo": "Menor",
    "Duplicado": "Mayor",
    "TipoInconsistente": "Mayor",
    "FueraDeRango": "Crítico",
}
