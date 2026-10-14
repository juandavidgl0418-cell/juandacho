from pathlib import Path

from dqv import ValidacionController

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"


def controlador_con(texto: str, nombre: str = "prueba.csv", codificacion: str = "utf-8", **opciones) -> ValidacionController:
    ctrl = ValidacionController()
    ctrl.cargar_archivo(nombre, texto.encode(codificacion), **opciones)
    return ctrl
