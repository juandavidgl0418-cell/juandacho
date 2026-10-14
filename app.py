"""Interfaz web de DataQuality Validator (Streamlit).

Ejecutar con:  streamlit run app.py

La interfaz solo se comunica con ValidacionController, único punto de entrada a
la lógica del sistema. Los pasos siguen el manual de usuario (capítulo 25).
"""

import hashlib
from pathlib import Path

import streamlit as st

from dqv import CsvFileError, Severidad, TipoProblema, ValidacionController, __version__, config

RUTA_EJEMPLO = Path(__file__).parent / "datos" / "clientes_ejemplo.csv"

st.set_page_config(page_title="DataQuality Validator", page_icon="✅", layout="wide")


def obtener_controlador() -> ValidacionController:
    """Un controlador por sesión de usuario; nada se guarda en disco (RNF05)."""
    if "controlador" not in st.session_state:
        st.session_state.controlador = ValidacionController()
    return st.session_state.controlador


def numero(valor: float) -> str:
    """Formatea un número con separador de miles en estilo colombiano."""
    texto = f"{valor:,.2f}".rstrip("0").rstrip(".")
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


ctrl = obtener_controlador()

# --------------------------------------------------------------------- Encabezado
st.title("✅ DataQuality Validator")
st.caption(
    "Cargue un archivo CSV y obtenga un diagnóstico básico de calidad: valores nulos, "
    "registros duplicados, tipos de dato inconsistentes y valores fuera de rango."
)
st.info(
    "🔒 El archivo se procesa en memoria y no se guarda. Aun así, no cargue archivos "
    "con información personal o sensible; use datos de prueba o anonimizados."
)

# ------------------------------------------------------------ Barra lateral
with st.sidebar:
    st.header("Opciones de lectura")
    opciones_separador = {"Automático": None, **{v: k for k, v in config.SEPARADORES.items()}}
    etiqueta_separador = st.selectbox(
        "Separador de columnas",
        list(opciones_separador),
        help="Déjelo en «Automático». Cámbielo solo si las columnas no se reconocen bien.",
    )
    opciones_codificacion = {"Automática": None, **{v: k for k, v in config.CODIFICACIONES.items()}}
    etiqueta_codificacion = st.selectbox(
        "Codificación de caracteres",
        list(opciones_codificacion),
        help="Si ve caracteres extraños en tildes o eñes, pruebe «Windows-1252 (Excel)».",
    )
    st.divider()
    st.header("¿Cómo se usa?")
    st.markdown(
        "1. Cargue su archivo CSV.\n"
        "2. Revise la estructura detectada.\n"
        "3. (Opcional) Defina un rango válido para columnas numéricas.\n"
        "4. Pulse **Validar calidad del archivo**.\n"
        "5. Lea el resumen de calidad.\n"
        "6. Consulte el detalle para corregir su archivo."
    )
    st.caption(f"Versión {__version__} · Gerencia de Proyectos Informáticos")

separador = opciones_separador[etiqueta_separador]
codificacion = opciones_codificacion[etiqueta_codificacion]

# ------------------------------------------------- Paso 1. Cargar el archivo
st.subheader("Paso 1. Cargar el archivo")
archivo = st.file_uploader(
    f"Seleccione o arrastre un archivo CSV (máximo {config.MAX_TAMANIO_MB} MB)",
    type=["csv"],
)

if archivo is None:
    if st.button("Usar archivo de ejemplo", help="Carga un archivo de clientes con errores conocidos."):
        st.session_state.usar_ejemplo = True
else:
    st.session_state.usar_ejemplo = False

if archivo is not None:
    nombre, contenido = archivo.name, archivo.getvalue()
elif st.session_state.get("usar_ejemplo"):
    nombre, contenido = RUTA_EJEMPLO.name, RUTA_EJEMPLO.read_bytes()
else:
    st.session_state.firma = None
    st.write("Para comenzar, cargue un archivo o use el archivo de ejemplo.")
    st.stop()

firma = (nombre, hashlib.md5(contenido).hexdigest(), separador, codificacion)
if st.session_state.get("firma") != firma:
    st.session_state.firma = firma
    st.session_state.error_carga = None
    try:
        with st.spinner("Leyendo el archivo..."):
            ctrl.cargar_archivo(nombre, contenido, separador, codificacion)
    except CsvFileError as error:
        st.session_state.error_carga = str(error)

if st.session_state.get("error_carga"):
    st.error(f"No se pudo procesar el archivo. {st.session_state.error_carga}")
    st.stop()

dataset = ctrl.dataset
csv_file = ctrl.csv_file
st.success(f"Archivo «{csv_file.nombre_archivo}» cargado correctamente.")
for advertencia in ctrl.advertencias:
    st.warning(advertencia)

# --------------------------------------------- Paso 2. Revisar la estructura
st.subheader("Paso 2. Estructura del archivo")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Filas (registros)", numero(dataset.numero_filas))
m2.metric("Columnas", dataset.numero_columnas)
m3.metric("Separador", csv_file.nombre_separador)
m4.metric("Codificación", csv_file.nombre_codificacion)
st.dataframe(ctrl.obtener_estructura(), hide_index=True, use_container_width=True)
with st.expander("Vista previa de los primeros 20 registros"):
    vista = dataset.datos.head(20).copy()
    vista.index = vista.index + 1
    st.dataframe(vista, use_container_width=True)

# ------------------------------------------- Paso 3. Definir rango (opcional)
st.subheader("Paso 3. Definir un rango válido (opcional)")
numericas = ctrl.columnas_numericas()
if not numericas:
    st.info("El archivo no tiene columnas numéricas, por lo que no es posible definir rangos.")
else:
    st.write(
        "Indique el valor mínimo y máximo aceptables para una columna numérica. "
        "Por ejemplo, para una columna de edad: mínimo 0 y máximo 120."
    )
    with st.form("form_rango"):
        c1, c2, c3 = st.columns(3)
        columna_rango = c1.selectbox("Columna numérica", numericas)
        minimo = c2.number_input("Valor mínimo", value=0.0, step=1.0)
        maximo = c3.number_input("Valor máximo", value=100.0, step=1.0)
        agregar = st.form_submit_button("Agregar o actualizar rango")
    if agregar:
        try:
            ctrl.definir_rango(columna_rango, minimo, maximo)
            st.success(f"Rango definido para «{columna_rango}»: {numero(minimo)} a {numero(maximo)}.")
        except ValueError as error:
            st.error(str(error))

    observados = []
    for nombre_col in numericas:
        bajo, alto = ctrl.limites_observados(nombre_col)
        if bajo is not None:
            observados.append(f"«{nombre_col}»: {numero(bajo)} a {numero(alto)}")
    if observados:
        st.caption("Valores presentes en el archivo — " + "; ".join(observados) + ".")

    if ctrl.rangos:
        st.markdown("**Rangos definidos**")
        for rango in ctrl.rangos:
            t, b = st.columns([4, 1])
            t.write(
                f"• «{rango.nombre_columna}»: de {numero(rango.valor_minimo)} a {numero(rango.valor_maximo)}"
            )
            if b.button("Quitar", key=f"quitar_{rango.nombre_columna}"):
                ctrl.quitar_rango(rango.nombre_columna)
                st.rerun()

# ------------------------------------------- Paso 4. Ejecutar la validación
st.subheader("Paso 4. Ejecutar la validación")
if st.button("Validar calidad del archivo", type="primary"):
    with st.spinner("Ejecutando las validaciones..."):
        ctrl.ejecutar_validacion()

if ctrl.reporte is None:
    st.write(
        "Pulse **Validar calidad del archivo** para revisar nulos, duplicados, tipos de dato"
        + (" y rangos." if ctrl.rangos else ". Si define un rango, también se revisarán los valores fuera de rango.")
    )
    st.stop()

# ------------------------------------------- Paso 5. Resumen de calidad
st.subheader("Paso 5. Resumen de calidad")
resumen = ctrl.obtener_resumen()
if resumen["total_problemas"] == 0:
    st.success("¡Excelente! No se encontraron problemas de calidad con las validaciones ejecutadas.")

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total de problemas", numero(resumen["total_problemas"]))
k2.metric("Valores nulos", numero(resumen["nulos"]))
k3.metric("Registros duplicados", numero(resumen["duplicados"]))
k4.metric("Tipos inconsistentes", numero(resumen["tipos_inconsistentes"]))
k5.metric(
    "Fuera de rango",
    numero(resumen["fuera_de_rango"]) if "Rango" in resumen["reglas_ejecutadas"] else "No aplica",
)

filas = resumen["numero_filas"]
porcentaje = f"{100 * resumen['filas_afectadas'] / filas if filas else 0:.1f}".replace(".", ",")
severidad = resumen["por_severidad"]
st.write(
    f"**{numero(resumen['filas_afectadas'])} de {numero(filas)} registros ({porcentaje} %)** "
    f"tienen al menos un problema. Por severidad: Crítico {severidad['Crítico']} · "
    f"Mayor {severidad['Mayor']} · Menor {severidad['Menor']}."
)

por_columna = ctrl.obtener_problemas_por_columna()
izquierda, derecha = st.columns([3, 2])
with izquierda:
    st.markdown("**Problemas por columna**")
    st.dataframe(por_columna, hide_index=True, use_container_width=True)
with derecha:
    st.markdown("**Valores nulos por columna**")
    if resumen["nulos"]:
        st.bar_chart(por_columna.set_index("Columna")["Valores nulos"])
    else:
        st.write("Ninguna columna tiene valores nulos.")
st.caption(
    f"Reporte n.º {resumen['id_reporte']} generado el {resumen['fecha_generacion']:%d/%m/%Y %H:%M:%S}. "
    f"Reglas ejecutadas: {', '.join(resumen['reglas_ejecutadas'])}."
)

# ------------------------------------------- Paso 6. Detalle de problemas
st.subheader("Paso 6. Detalle de los problemas encontrados")
if resumen["total_problemas"] == 0:
    st.write("No hay problemas para mostrar.")
    st.stop()

f1, f2, f3 = st.columns(3)
filtro_tipos = f1.multiselect(
    "Tipo de problema",
    options=list(TipoProblema.ETIQUETAS),
    format_func=lambda t: TipoProblema.ETIQUETAS[t],
    placeholder="Todos",
)
filtro_columnas = f2.multiselect("Columna", options=[c.nombre for c in dataset.columnas], placeholder="Todas")
filtro_severidad = f3.multiselect("Severidad", options=list(Severidad.ORDEN), placeholder="Todas")

detalle = ctrl.obtener_detalle(filtro_tipos or None, filtro_columnas or None, filtro_severidad or None)
st.caption(
    f"Mostrando {numero(len(detalle))} de {numero(resumen['total_problemas'])} problemas. "
    "La fila 1 es el primer registro debajo del encabezado (en Excel corresponde a la fila 2)."
)
st.dataframe(detalle, hide_index=True, use_container_width=True)

with st.expander("¿Cómo interpretar los resultados?"):
    st.markdown(
        "| Resultado | Qué significa | Qué hacer |\n"
        "|---|---|---|\n"
        "| Valor nulo | La celda está vacía o dice NA, N/A, null o similar. | Completar el dato o definir cómo se tratará. |\n"
        "| Registro duplicado | La fila es idéntica a una fila anterior. | Revisar si está repetida por error y eliminarla. |\n"
        "| Tipo inconsistente | El valor no corresponde al tipo del resto de la columna (por ejemplo, texto en una columna numérica o una fecha que no existe). | Corregir el valor indicado. |\n"
        "| Fuera de rango | El número es menor que el mínimo o mayor que el máximo definido. | Verificar si es un error de captura o ajustar el rango. |\n\n"
        "**Severidad:** Crítico = incumple una regla definida por usted (rango); "
        "Mayor = registro duplicado o tipo inconsistente; Menor = valor nulo."
    )
