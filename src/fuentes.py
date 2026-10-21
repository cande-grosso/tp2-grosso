"""Fuentes de datos: lectura de viajes desde archivos CSV y JSON.

Las dos fuentes devuelven la misma representación: una lista de diccionarios
con los mismos campos, de modo que el resto de la aplicación no depende del
formato del archivo de origen.
"""
import csv
import json
from abc import ABC, abstractmethod
from pathlib import Path


class ErrorFuente(Exception):
    """Se produce cuando un archivo de entrada no se puede leer o no tiene
    la estructura esperada."""


class FuenteDatos(ABC):
    """Contrato común de las fuentes de datos."""

    @abstractmethod
    def cargar(self, ruta):
        """Lee el archivo y devuelve una lista de diccionarios (un viaje por
        diccionario). Lanza ErrorFuente si no puede leerlo."""


class FuenteCSV(FuenteDatos):
    """Lee viajes desde un archivo CSV con fila de encabezados."""

    def cargar(self, ruta):
        ruta = Path(ruta)
        if not ruta.is_file():
            raise ErrorFuente(f"No se encontró el archivo: {ruta}")
        try:
            # utf-8-sig descarta la marca BOM que traen algunos archivos.
            with ruta.open(encoding="utf-8-sig", newline="") as archivo:
                lector = csv.DictReader(archivo)
                if lector.fieldnames is None:
                    raise ErrorFuente(f"El archivo CSV está vacío: {ruta}")
                return [dict(fila) for fila in lector]
        except UnicodeDecodeError as error:
            raise ErrorFuente(
                f"No se pudo decodificar {ruta} como UTF-8: {error}"
            ) from error
        except csv.Error as error:
            raise ErrorFuente(f"CSV mal formado en {ruta}: {error}") from error


class FuenteJSON(FuenteDatos):
    """Lee viajes desde un archivo JSON que contiene una lista de objetos."""

    def cargar(self, ruta):
        ruta = Path(ruta)
        if not ruta.is_file():
            raise ErrorFuente(f"No se encontró el archivo: {ruta}")
        try:
            with ruta.open(encoding="utf-8-sig") as archivo:
                datos = json.load(archivo)
        except json.JSONDecodeError as error:
            raise ErrorFuente(f"JSON mal formado en {ruta}: {error}") from error
        except UnicodeDecodeError as error:
            raise ErrorFuente(
                f"No se pudo decodificar {ruta} como UTF-8: {error}"
            ) from error

        if not isinstance(datos, list):
            raise ErrorFuente(
                f"Se esperaba una lista de objetos en {ruta}, "
                f"pero se encontró {type(datos).__name__}"
            )
        if not all(isinstance(item, dict) for item in datos):
            raise ErrorFuente(f"Todos los elementos de {ruta} deben ser objetos")
        return datos


def fuente_para(ruta):
    """Elige la fuente adecuada según la extensión del archivo."""
    extension = Path(ruta).suffix.lower()
    if extension == ".csv":
        return FuenteCSV()
    if extension == ".json":
        return FuenteJSON()
    raise ErrorFuente(
        f"Formato no soportado: '{extension}'. Use un archivo .csv o .json"
    )
