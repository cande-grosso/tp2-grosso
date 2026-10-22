"""Diagnóstico de calidad sobre el archivo completo de viajes (CSV).

Recorre el archivo registro por registro, sin cargarlo en memoria, y aplica
la misma validación que usa la aplicación. Informa cuántos registros se
rechazan y por qué motivo, los ids duplicados y la cantidad de viajes por día.

Uso (desde la carpeta del repositorio):
    py src/diagnostico.py RUTA_AL_CSV_COMPLETO
"""
import csv
import sys
from collections import Counter

from viaje import ErrorValidacion, Viaje

AVISO_CADA = 500_000


def diagnosticar(ruta):
    """Devuelve (total, rechazos_por_motivo, duplicados, viajes_por_dia)."""
    motivos = Counter()
    por_dia = Counter()
    ids = set()
    total = 0
    duplicados = 0
    with open(ruta, encoding="utf-8-sig", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            total += 1
            if total % AVISO_CADA == 0:
                print(f"Procesados {total} registros...", flush=True)
            por_dia[(fila.get("fecha_origen_recorrido") or "")[:10]] += 1
            try:
                viaje = Viaje.desde_registro(fila)
            except ErrorValidacion as error:
                motivos[str(error)] += 1
                continue
            if viaje.id_recorrido in ids:
                duplicados += 1
            ids.add(viaje.id_recorrido)
    return total, motivos, duplicados, por_dia


def main():
    if len(sys.argv) != 2:
        print("Uso: py src/diagnostico.py RUTA_AL_CSV_COMPLETO")
        return 1
    total, motivos, duplicados, por_dia = diagnosticar(sys.argv[1])

    rechazados = sum(motivos.values())
    print(f"\nRegistros totales: {total}")
    print(f"Rechazados: {rechazados} ({100 * rechazados / total:.2f} %)")
    for motivo, cantidad in motivos.most_common():
        print(f"  {motivo}: {cantidad} ({100 * cantidad / total:.2f} %)")
    print(f"Ids duplicados entre los válidos: {duplicados}")

    # Días con fecha de inicio bien formada (AAAA-MM-DD).
    dias = {d: c for d, c in por_dia.items() if len(d) == 10 and d[4] == "-"}
    if dias:
        print(f"\nDías con viajes: {len(dias)}")
        print(f"Promedio diario: {round(sum(dias.values()) / len(dias))}")
        print("Día con menos viajes:", min(dias.items(), key=lambda x: x[1]))
        print("Día con más viajes:", max(dias.items(), key=lambda x: x[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())