"""Genera una muestra reproducible de viajes de Ecobici en CSV y JSON.

Uso (desde la carpeta del repositorio):
    py src/crear_muestra.py RUTA_AL_CSV_COMPLETO
"""
import csv
import json
import random
import sys
from pathlib import Path

DIA = "2024-01-23"
CANTIDAD = 200
SEMILLA = 42
CAMPOS = [
    "id_recorrido",
    "duracion_recorrido",
    "fecha_origen_recorrido",
    "fecha_destino_recorrido",
    "id_estacion_origen",
    "nombre_estacion_origen",
    "id_estacion_destino",
    "nombre_estacion_destino",
]
CARPETA_DATOS = Path(__file__).resolve().parents[1] / "data"


def leer_viajes_del_dia(ruta, dia):
    """Devolve solo las columnas necesarias de los viajes que empiezan en `dia`."""
    with open(ruta, encoding="utf-8-sig", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            if fila["fecha_origen_recorrido"].startswith(dia):
                yield {campo: fila[campo] for campo in CAMPOS}


def main():
    if len(sys.argv) != 2:
        print("Uso: py src/crear_muestra.py RUTA_AL_CSV_COMPLETO")
        return
    viajes = list(leer_viajes_del_dia(sys.argv[1], DIA))
    print(f"Viajes encontrados el {DIA}: {len(viajes)}")
    if len(viajes) < CANTIDAD:
        print("No hay viajes suficientes para la muestra.")
        return

    random.seed(SEMILLA)
    muestra = random.sample(viajes, CANTIDAD)
    muestra.sort(key=lambda v: v["fecha_origen_recorrido"])

    CARPETA_DATOS.mkdir(exist_ok=True)
    with open(CARPETA_DATOS / "viajes_muestra.csv", "w",
              encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows(muestra)
    with open(CARPETA_DATOS / "viajes_muestra.json", "w",
              encoding="utf-8") as f:
        json.dump(muestra, f, ensure_ascii=False, indent=2)
    print(f"Muestra de {CANTIDAD} viajes guardada en {CARPETA_DATOS}")


if __name__ == "__main__":
    main()