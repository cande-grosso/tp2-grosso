"""Balance de movimientos de estaciones Ecobici.

Ejemplo:
    py src/main.py --entrada data/viajes_muestra.csv ^
        --inicio "2024-01-23 07:00:00" --fin "2024-01-23 10:00:00"
"""
import argparse
import sys

from fuentes import ErrorFuente, fuente_para
from pipeline import (
    ErrorResultado,
    contar_rechazos_por_motivo,
    generar_balance,
    guardar_rechazos,
    guardar_resultado,
    limpiar_datos,
    registrar_movimientos,
    seleccionar_periodo,
    validar_esquema,
    verificar_resultado,
)
from viaje import ErrorValidacion, parsear_fecha

CANTIDAD_DESTACADAS = 5


def crear_parser():
    parser = argparse.ArgumentParser(
        description="Calcula salidas, llegadas y balance por estación "
        "de los viajes de Ecobici en una franja temporal."
    )
    parser.add_argument("--entrada", required=True,
                        help="archivo de viajes (.csv o .json)")
    parser.add_argument("--inicio", required=True,
                        help='inicio del período, "AAAA-MM-DD HH:MM:SS" (incluido)')
    parser.add_argument("--fin", required=True,
                        help='fin del período, "AAAA-MM-DD HH:MM:SS" (excluido)')
    parser.add_argument("--salida", default="outputs/balance_estaciones.csv",
                        help="CSV del reporte (por defecto: %(default)s)")
    parser.add_argument("--rechazos", default="outputs/viajes_rechazados.csv",
                        help="CSV de rechazados (por defecto: %(default)s)")
    return parser


def _linea_estacion(fila):
    return (f"  {fila['nombre_estacion']}: {fila['balance']:+d} "
            f"({fila['llegadas']} llegadas, {fila['salidas']} salidas)")


def mostrar_resumen(leidos, validos, rechazos, seleccionados, filas):
    print(f"Registros leídos: {leidos}")
    print(f"Viajes válidos: {len(validos)}")
    print(f"Viajes rechazados: {len(rechazos)}")
    for motivo, cantidad in contar_rechazos_por_motivo(rechazos).most_common():
        print(f"  - {motivo}: {cantidad}")
    print(f"Viajes en el período: {len(seleccionados)}")
    print(f"Estaciones con movimientos: {len(filas)}")
    if not filas:
        print("No hay viajes válidos en el período indicado.")
        return
    positivas = [f for f in filas if f["balance"] > 0][:CANTIDAD_DESTACADAS]
    negativas = [f for f in reversed(filas) if f["balance"] < 0][:CANTIDAD_DESTACADAS]
    print("\nMayor balance positivo (reciben más de lo que despachan):")
    for fila in positivas:
        print(_linea_estacion(fila))
    if not positivas:
        print("  (ninguna estación con balance positivo)")
    print("\nMayor balance negativo (despachan más de lo que reciben):")
    for fila in negativas:
        print(_linea_estacion(fila))
    if not negativas:
        print("  (ninguna estación con balance negativo)")


def main(argv=None):
    args = crear_parser().parse_args(argv)
    try:
        inicio = parsear_fecha(args.inicio, "--inicio")
        fin = parsear_fecha(args.fin, "--fin")

        registros = fuente_para(args.entrada).cargar(args.entrada)
        validar_esquema(registros)
        validos, rechazos = limpiar_datos(registros)
        seleccionados = seleccionar_periodo(validos, inicio, fin)
        filas = generar_balance(registrar_movimientos(seleccionados))
        verificar_resultado(filas, len(seleccionados))

        guardar_resultado(filas, args.salida)
        guardar_rechazos(rechazos, args.rechazos)
    except (ErrorFuente, ErrorValidacion, ErrorResultado) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    mostrar_resumen(len(registros), validos, rechazos, seleccionados, filas)
    print(f"\nReporte guardado en: {args.salida}")
    print(f"Rechazados guardados en: {args.rechazos}")
    return 0


if __name__ == "__main__":
    sys.exit(main())