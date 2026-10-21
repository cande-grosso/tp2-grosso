"""Modelo del dominio: un viaje de Ecobici y su validación.

La validación de fechas combina dos controles: una expresión regular que
comprueba el *formato* textual y datetime.strptime, que comprueba que la fecha
*exista en el calendario* (por ejemplo, rechaza 2024-02-30).
"""
import re
from dataclasses import dataclass
from datetime import datetime

FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"

# Valida solo la forma: AAAA-MM-DD HH:MM:SS con dígitos. No garantiza que la
# fecha exista; eso lo comprueba strptime.
PATRON_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")

# Identificadores numéricos (viaje y estaciones) y duración en segundos.
PATRON_ENTERO = re.compile(r"^\d+$")

CAMPOS_OBLIGATORIOS = (
    "id_recorrido",
    "duracion_recorrido",
    "fecha_origen_recorrido",
    "fecha_destino_recorrido",
    "id_estacion_origen",
    "nombre_estacion_origen",
    "id_estacion_destino",
    "nombre_estacion_destino",
)


class ErrorValidacion(Exception):
    """Un registro o un parámetro no cumple las condiciones necesarias.

    El mensaje es estable (no incluye valores variables) para poder contar
    los rechazos por motivo.
    """


def parsear_fecha(texto, nombre="fecha"):
    """Convierte 'AAAA-MM-DD HH:MM:SS' en datetime o lanza ErrorValidacion."""
    texto = (texto or "").strip()
    if not PATRON_FECHA.match(texto):
        raise ErrorValidacion(
            f"{nombre} con formato inválido (se espera AAAA-MM-DD HH:MM:SS)"
        )
    try:
        return datetime.strptime(texto, FORMATO_FECHA)
    except ValueError:
        raise ErrorValidacion(
            f"{nombre} inexistente en el calendario"
        ) from None


def _texto(registro, campo):
    valor = registro.get(campo)
    return "" if valor is None else str(valor).strip()


@dataclass(frozen=True)
class Viaje:
    """Un viaje válido: de una estación de origen a una de destino."""

    id_recorrido: str
    inicio: datetime
    fin: datetime
    id_origen: str
    nombre_origen: str
    id_destino: str
    nombre_destino: str
    duracion_segundos: int

    @classmethod
    def desde_registro(cls, registro):
        """Construye un Viaje desde un diccionario crudo.

        Lanza ErrorValidacion con el motivo si el registro no es válido.
        """
        for campo in CAMPOS_OBLIGATORIOS:
            if not _texto(registro, campo):
                raise ErrorValidacion(f"campo obligatorio vacío: {campo}")

        for campo in ("id_recorrido", "id_estacion_origen", "id_estacion_destino"):
            if not PATRON_ENTERO.match(_texto(registro, campo)):
                raise ErrorValidacion(f"identificador no numérico: {campo}")

        if not PATRON_ENTERO.match(_texto(registro, "duracion_recorrido")):
            raise ErrorValidacion("duración no es un entero no negativo")

        inicio = parsear_fecha(
            _texto(registro, "fecha_origen_recorrido"), "fecha de inicio"
        )
        fin = parsear_fecha(
            _texto(registro, "fecha_destino_recorrido"), "fecha de fin"
        )
        if fin < inicio:
            raise ErrorValidacion("fin anterior al inicio")

        viaje = cls(
            id_recorrido=_texto(registro, "id_recorrido"),
            inicio=inicio,
            fin=fin,
            id_origen=_texto(registro, "id_estacion_origen"),
            nombre_origen=_texto(registro, "nombre_estacion_origen"),
            id_destino=_texto(registro, "id_estacion_destino"),
            nombre_destino=_texto(registro, "nombre_estacion_destino"),
            duracion_segundos=int(_texto(registro, "duracion_recorrido")),
        )
        if viaje.duracion_segundos == 0 and not viaje.es_circular():
            raise ErrorValidacion("duración 0 entre estaciones distintas")
        return viaje

    def duracion_minutos(self):
        """Duración del viaje en minutos."""
        return self.duracion_segundos / 60

    def es_circular(self):
        """True si el viaje termina en la misma estación donde empezó."""
        return self.id_origen == self.id_destino

        