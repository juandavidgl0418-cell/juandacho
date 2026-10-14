# DataQuality Validator

Prototipo web para la validación básica de calidad de archivos CSV.
Detecta valores nulos, registros duplicados, tipos de dato inconsistentes y valores
fuera de un rango definido por el usuario, y presenta un resumen y el detalle de
cada problema.

Proyecto del curso **Gerencia de Proyectos Informáticos** — Institución Universitaria
Politécnico Grancolombiano, grupo 28.

Tecnologías: **Python**, **Pandas** (procesamiento) y **Streamlit** (interfaz web).
No usa base de datos: todo se procesa en memoria durante la sesión (RNF05).

---

## 1. Ejecutar en su computador

Requisitos: Python 3.10, 3.11 o 3.12 (recomendado 3.12) y Git.

```bash
git clone <URL-del-repositorio>
cd dataquality-validator

# Crear y activar un entorno virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

El navegador se abre en `http://localhost:8501`. Si no tiene un CSV a mano, pulse
**Usar archivo de ejemplo**.

## 2. Ejecutar las pruebas

```bash
pip install -r requirements-dev.txt
python -m pytest            # o, sin pytest:  python -m unittest discover -s tests -t .
```

Hay 39 pruebas automatizadas que cubren la carga del archivo, la inferencia de tipos,
las cuatro validaciones, el reporte y un caso completo con el archivo de ejemplo.

## 3. Desplegar en Streamlit Community Cloud (capítulo 24)

1. Suba esta carpeta a un repositorio **público** de GitHub (incluya `requirements.txt`
   y la carpeta `.streamlit`).
2. Entre a <https://share.streamlit.io> con su cuenta de GitHub y pulse **Create app**.
3. Seleccione el repositorio, la rama `main` y el archivo principal `app.py`.
4. En **Advanced settings** elija **Python 3.12** y pulse **Deploy**.
5. Revise el registro del servidor; si hay errores de dependencias, verifique las
   versiones de `requirements.txt` (riesgo R13).
6. Prueba de humo: abra el enlace desde otro navegador, pulse **Usar archivo de
   ejemplo**, defina el rango 0–120 para `edad` y valide. Debe obtener **13 problemas**
   (ver sección 7).
7. Registre el enlace y la fecha en la Tabla 27 del documento.

Las aplicaciones gratuitas se suspenden tras varios días sin uso; ábrala 24 horas antes
de la sustentación (riesgo R03). Como respaldo, se puede ejecutar localmente (sección 1).

## 4. Estructura del proyecto

```
dataquality-validator/
├── app.py                    Interfaz Web (Streamlit) — pasos 1 a 6 del manual de usuario
├── dqv/
│   ├── controlador.py        ValidacionController — único punto de entrada a la lógica
│   ├── servicio.py           ValidationService — orquesta las reglas y crea el reporte
│   ├── csv_file.py           CsvFile — verifica el archivo y lo convierte en Dataset
│   ├── modelos.py            Dataset, Column, Issue, QualityReport, RangoValidacion
│   ├── tipos.py              Reglas explícitas de inferencia de tipos de dato
│   ├── config.py             Parámetros: tamaño máximo, valores nulos, umbral, severidad
│   └── reglas/
│       ├── base.py           ValidationRule (clase abstracta)
│       ├── nulos.py          NullValidator
│       ├── duplicados.py     DuplicateValidator
│       ├── tipos_dato.py     DataTypeValidator
│       └── rango.py          RangeValidator (regla opcional)
├── datos/                    Archivos CSV de ejemplo con errores conocidos
├── tests/                    Pruebas automatizadas
├── .streamlit/config.toml    Límite de carga (20 MB) y tema
└── requirements.txt          Versiones fijas de las librerías
```

Cada clase corresponde a una del diagrama de clases (Figura 4) y los métodos siguen
los diagramas de secuencia (capítulo 14):

| Proceso (diagrama de secuencia) | Llamadas en el código |
|---|---|
| 14.1 Cargar archivo CSV | `ValidacionController.cargar_archivo` → `CsvFile.verificar` → `CsvFile.convertir_a_dataset` → `Dataset` crea las `Column` |
| 14.2 Ejecutar validación | `ValidacionController.ejecutar_validacion` → `ValidationService.validar` → `validar(dataset)` de cada regla → `QualityReport` |
| 14.3 Definir rango y validar | `ValidacionController.definir_rango` → `ValidationService.registrar_rango` → `RangeValidator.configurar_rango` |
| 14.4 Consultar reporte | `ValidacionController.obtener_resumen` / `obtener_detalle` → `QualityReport` |

Para agregar una validación nueva basta con crear una subclase de `ValidationRule`
y agregarla a la lista `reglas` de `ValidationService` (RNF03).

## 5. Reglas de validación

| Regla | Qué detecta | Severidad |
|---|---|---|
| Nulos | Celdas vacías o con `NA`, `N/A`, `#N/A`, `NaN`, `null`, `None`, `nulo` (sin distinguir mayúsculas) | Menor |
| Duplicados | Registros idénticos a uno anterior en todas sus columnas (sin contar espacios al inicio o al final). La primera aparición no se reporta | Mayor |
| Tipos | Valores que no corresponden al tipo de su columna | Mayor |
| Rango (opcional) | Números menores que el mínimo o mayores que el máximo definidos. Los límites son válidos | Crítico |

**Inferencia de tipos (riesgo R06).** Para cada columna se calcula qué proporción de
sus valores no nulos es Booleano (sí, no, verdadero, falso, true, false), Numérico o
Fecha. La columna toma el tipo con mayor proporción si alcanza el **80 %**; los demás
valores se reportan como inconsistentes. Si ningún tipo llega al 80 %, la columna es
Texto y no genera inconsistencias.

- Números: `1234.5`, `-3`, `1e5`, `1,234,567.89`. Si la columna usa coma decimal
  (`12.500,50` o `3,5`), toda la columna se lee con punto de miles y coma decimal.
- Fechas: `AAAA-MM-DD`, `DD/MM/AAAA`, `DD-MM-AAAA`, `AAAA/MM/DD` (con hora opcional).
  Fechas inexistentes como `2024-02-30` se reportan.

**Lectura del archivo (riesgo R05).** El separador (coma, punto y coma, tabulación o
barra) y la codificación (UTF-8 con o sin BOM, Windows-1252 de Excel, Latin-1) se
detectan automáticamente y también se pueden elegir en la barra lateral.

**Numeración de filas.** La fila 1 es el primer registro debajo del encabezado (en
Excel corresponde a la fila 2).

Los parámetros se pueden ajustar en `dqv/config.py`.

## 6. Trazabilidad con los requerimientos

| ID | Implementación | Prueba |
|---|---|---|
| RF01 Cargar CSV | `CsvFile`, paso 1 de `app.py` | `test_rf01_carga_archivo_de_ejemplo` |
| RF02 Filas y columnas | `Dataset.numero_filas/numero_columnas`, paso 2 | `test_rf01_…`, `test_rf09_resumen` |
| RF03 Columnas identificadas | `Dataset.columnas`, `obtener_estructura` | `test_rf01_…` |
| RF04 Nulos por columna | `NullValidator`, `Column.cantidad_nulos` | `test_rf04_nulos_por_columna_y_fila` |
| RF05 Duplicados | `DuplicateValidator` | `test_rf05_registros_duplicados_…` |
| RF06 Tipos de dato | `tipos.inferir_tipo`, `DataTypeValidator` | `test_rf06_…`, `test_tipos.py` |
| RF07 Definir rango | `RangoValidacion`, `RangeValidator.configurar_rango`, paso 3 | `test_rf07_rf08_…`, `test_minimo_mayor_que_maximo` |
| RF08 Fuera de rango | `RangeValidator.validar` | `test_rf07_rf08_valores_fuera_de_rango` |
| RF09 Resumen | `QualityReport.resumen`, paso 5 | `test_rf09_resumen` |
| RF10 Detalle | `QualityReport.detalle` con filtros, paso 6 | `test_rf10_detalle_y_filtros` |
| RNF01 Navegador | Streamlit | Despliegue |
| RNF02 Sin programación | Textos en lenguaje claro, ayuda en la barra lateral | Prueba de uso |
| RNF03 Modular | `ValidationRule` y una clase por regla | `test_rnf03_…` |
| RNF04 Mensajes claros | `CsvFileError` con mensajes en español | `test_rnf04_…` |
| RNF05 Sin almacenamiento | Todo en memoria por sesión | Revisión de código |
| RNF06 Código abierto | Python, Pandas, Streamlit | `requirements.txt` |

## 7. Archivos de ejemplo

`datos/clientes_ejemplo.csv` — 20 registros y 7 columnas con errores conocidos. Con el
rango 0–120 en `edad` el resultado esperado es:

| Problema | Cantidad | Filas |
|---|---|---|
| Valores nulos | 4 | 2 y 14 (edad), 5 (saldo), 11 (ciudad) |
| Registros duplicados | 2 | 8 (igual a la 1), 16 (igual a la 7) |
| Tipos inconsistentes | 5 | 3 y 18 (fecha inexistente), 6 (edad «treinta»), 12 (saldo «mil»), 15 (activo «tal vez») |
| Fuera de rango | 2 | 4 (edad −4), 9 (edad 135) |
| **Total** | **13** | 13 de 20 registros afectados |

`datos/ventas_excel_punto_y_coma.csv` — archivo con separador punto y coma, codificación
de Excel en español y coma decimal, para comprobar la lectura automática.

## 8. Limitaciones conocidas

- Tamaño máximo de archivo: 20 MB (riesgo R04). Un archivo de 12 MB (≈280.000
  registros) se carga en unos 4 segundos y se valida en 2.
- Los duplicados se buscan en filas completas, no por una columna clave.
- Las fechas se interpretan como día/mes/año; el formato mes/día/año no se reconoce.
