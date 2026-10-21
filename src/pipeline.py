"""Flujo de procesamiento: validar, limpiar, seleccionar, calcular y exportar.

Estas funciones reciben datos ya cargados (listas de diccionarios o de Viaje)
y no dependen del formato del archivo de origen.
"""
import csv
from collections import Counter
from pathlib import Path

from balance import BalanceEstacion
from viaje import CAMPOS_OBLIGATORIOS, ErrorValidacion, Viaje

COLUMNAS_REPORTE = (
    "id_estacion", "nombre_estacion", "salidas", "llegadas", "balance",
)
COLUMNAS_RECHAZOS = ("fila", "id_recorrido", "motivo")


class ErrorResultado(Exception):
    """El resultado calculado incumple una propiedad que debería cumplir."""


def validar_esquema(registros):
    """Comprueba que haya datos y que estén las columnas necesarias."""
    if not registros:
        raise ErrorValidacion("No hay registros para procesar.")
    faltantes = [c for c in CAMPOS_OBLIGATORIOS if c not in registros[0]]
    if faltantes:
        raise ErrorValidacion(
            "Faltan columnas obligatorias: " + ", ".join(faltantes)
        )


def limpiar_datos(registros):
    """Separa los registros en viajes válidos y rechazos con su motivo.

    Se rechazan: campos vacíos, formatos o fechas inválidas, fin anterior al
    inicio, duración inválida, duración 0 entre estaciones distintas e
    identificadores de viaje repetidos (se conserva la primera aparición).
    Devuelve (viajes_validos, rechazos). Cada rechazo indica la fila del
    archivo (empezando en 1, sin contar el encabezado), el id y el motivo.
    """
    validos = []
    rechazos = []
    vistos = set()
    for numero, registro in enumerate(registros, start=1):
        id_viaje = str(registro.get("id_recorrido") or "").strip()
        try:
            viaje = Viaje.desde_registro(registro)
            if viaje.id_recorrido in vistos:
                raise ErrorValidacion("id de viaje duplicado")
        except ErrorValidacion as error:
            rechazos.append(
                {"fila": numero, "id_recorrido": id_viaje, "motivo": str(error)}
            )
            continue
        vistos.add(viaje.id_recorrido)
        validos.append(viaje)
    return validos, rechazos


def contar_rechazos_por_motivo(rechazos):
    """Cuenta los rechazos agrupados por motivo."""
    return Counter(r["motivo"] for r in rechazos)


def seleccionar_periodo(viajes, inicio, fin):
    """Elige los viajes cuyo inicio está en [inicio, fin)."""
    if inicio >= fin:
        raise ErrorValidacion("El inicio del período debe ser anterior al fin.")
    return [v for v in viajes if inicio <= v.inicio < fin]


def registrar_movimientos(viajes):
    """Acumula salidas y llegadas por estación (clave: id de estación).

    De cada viaje seleccionado se cuentan ambos extremos. Si una misma
    estación aparece con nombres distintos, se conserva el primero visto.
    """
    estaciones = {}

    def estacion(id_estacion, nombre):
        if id_estacion not in estaciones:
            estaciones[id_estacion] = BalanceEstacion(id_estacion, nombre)
        return estaciones[id_estacion]

    for viaje in viajes:
        estacion(viaje.id_origen, viaje.nombre_origen).registrar_salida()
        estacion(viaje.id_destino, viaje.nombre_destino).registrar_llegada()
    return estaciones


def generar_balance(estaciones):
    """Devuelve las filas del reporte ordenadas por balance descendente.

    El desempate es por id de estación, para que el orden sea siempre el mismo.
    """
    filas = [e.a_fila() for e in estaciones.values()]
    filas.sort(key=lambda f: (-f["balance"], int(f["id_estacion"])))
    return filas


def verificar_resultado(filas, cantidad_viajes):
    """Comprueba las propiedades que el reporte debe cumplir."""
    if any(f["salidas"] < 0 or f["llegadas"] < 0 for f in filas):
        raise ErrorResultado("Hay conteos negativos en el reporte.")
    total_salidas = sum(f["salidas"] for f in filas)
    total_llegadas = sum(f["llegadas"] for f in filas)
    if total_salidas != cantidad_viajes or total_llegadas != cantidad_viajes:
        raise ErrorResultado(
            "Las salidas y llegadas totales no coinciden con la cantidad de "
            "viajes seleccionados."
        )
    if sum(f["balance"] for f in filas) != 0:
        raise ErrorResultado("La suma de los balances no es cero.")


def _guardar_csv(filas, columnas, ruta):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows(filas)


def guardar_resultado(filas, ruta):
    """Guarda el reporte de balance por estación en un CSV."""
    _guardar_csv(filas, COLUMNAS_REPORTE, ruta)


def guardar_rechazos(rechazos, ruta):
    """Guarda los viajes rechazados con su motivo en un CSV."""
    _guardar_csv(rechazos, COLUMNAS_RECHAZOS, ruta)

    