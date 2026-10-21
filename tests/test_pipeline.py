"""Pruebas del balance de movimientos de Ecobici.

Ejecución (desde la carpeta del repositorio):
    py -m unittest discover -s tests -v
"""
import csv
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from fuentes import ErrorFuente, FuenteCSV, FuenteJSON, fuente_para  # noqa: E402
from pipeline import (  # noqa: E402
    ErrorResultado,
    generar_balance,
    guardar_rechazos,
    guardar_resultado,
    limpiar_datos,
    registrar_movimientos,
    seleccionar_periodo,
    validar_esquema,
    verificar_resultado,
)
from viaje import CAMPOS_OBLIGATORIOS, ErrorValidacion, Viaje, parsear_fecha  # noqa: E402


def registro(**cambios):
    """Un registro válido de ejemplo; los argumentos reemplazan campos."""
    base = {
        "id_recorrido": "1",
        "duracion_recorrido": "600",
        "fecha_origen_recorrido": "2024-01-23 10:00:00",
        "fecha_destino_recorrido": "2024-01-23 10:10:00",
        "id_estacion_origen": "10",
        "nombre_estacion_origen": "Estación A",
        "id_estacion_destino": "20",
        "nombre_estacion_destino": "Estación B",
    }
    base.update(cambios)
    return base


def procesar(registros, inicio="2024-01-23 00:00:00", fin="2024-01-24 00:00:00"):
    """Ejecuta limpieza, selección y balance sobre registros crudos."""
    validos, rechazos = limpiar_datos(registros)
    elegidos = seleccionar_periodo(
        validos, parsear_fecha(inicio), parsear_fecha(fin)
    )
    filas = generar_balance(registrar_movimientos(elegidos))
    return filas, validos, rechazos, elegidos


class CasoNormal(unittest.TestCase):
    def test_viaje_de_a_a_b_suma_salida_en_a_y_llegada_en_b(self):
        filas, _, rechazos, _ = procesar([registro()])
        por_id = {f["id_estacion"]: f for f in filas}
        self.assertEqual(rechazos, [])
        self.assertEqual(por_id["10"]["salidas"], 1)
        self.assertEqual(por_id["10"]["llegadas"], 0)
        self.assertEqual(por_id["10"]["balance"], -1)
        self.assertEqual(por_id["20"]["salidas"], 0)
        self.assertEqual(por_id["20"]["llegadas"], 1)
        self.assertEqual(por_id["20"]["balance"], 1)

    def test_varios_viajes_acumulan_por_estacion(self):
        registros = [
            registro(id_recorrido="1"),
            registro(id_recorrido="2"),
            registro(id_recorrido="3", id_estacion_origen="20",
                     nombre_estacion_origen="Estación B",
                     id_estacion_destino="10",
                     nombre_estacion_destino="Estación A"),
        ]
        filas, *_ = procesar(registros)
        por_id = {f["id_estacion"]: f for f in filas}
        self.assertEqual(por_id["10"]["salidas"], 2)
        self.assertEqual(por_id["10"]["llegadas"], 1)
        self.assertEqual(por_id["20"]["salidas"], 1)
        self.assertEqual(por_id["20"]["llegadas"], 2)

    def test_periodo_incluye_inicio_y_excluye_fin(self):
        registros = [
            registro(id_recorrido="1",
                     fecha_origen_recorrido="2024-01-23 10:00:00"),
            registro(id_recorrido="2",
                     fecha_origen_recorrido="2024-01-23 11:00:00",
                     fecha_destino_recorrido="2024-01-23 11:10:00"),
        ]
        _, _, _, elegidos = procesar(
            registros, "2024-01-23 10:00:00", "2024-01-23 11:00:00"
        )
        self.assertEqual([v.id_recorrido for v in elegidos], ["1"])

    def test_duracion_minutos(self):
        viaje = Viaje.desde_registro(registro(duracion_recorrido="90"))
        self.assertEqual(viaje.duracion_minutos(), 1.5)

    def test_orden_del_reporte_es_determinista(self):
        registros = [
            registro(id_recorrido="1"),
            registro(id_recorrido="2", id_estacion_destino="30",
                     nombre_estacion_destino="Estación C"),
        ]
        filas, *_ = procesar(registros)
        self.assertEqual([f["id_estacion"] for f in filas], ["20", "30", "10"])


class EntradasInvalidas(unittest.TestCase):
    def motivo_de(self, **cambios):
        _, rechazos = limpiar_datos([registro(**cambios)])
        self.assertEqual(len(rechazos), 1)
        return rechazos[0]["motivo"]

    def test_fin_anterior_al_inicio(self):
        motivo = self.motivo_de(fecha_destino_recorrido="2024-01-23 09:00:00")
        self.assertEqual(motivo, "fin anterior al inicio")

    def test_fecha_con_formato_invalido(self):
        motivo = self.motivo_de(fecha_origen_recorrido="23/01/2024 10:00")
        self.assertIn("formato inválido", motivo)

    def test_fecha_inexistente_en_el_calendario(self):
        # Cumple el formato de la expresión regular pero no existe.
        motivo = self.motivo_de(fecha_origen_recorrido="2024-02-30 10:00:00")
        self.assertIn("inexistente en el calendario", motivo)

    def test_estacion_faltante(self):
        motivo = self.motivo_de(id_estacion_destino="")
        self.assertIn("campo obligatorio vacío", motivo)

    def test_identificador_no_numerico(self):
        motivo = self.motivo_de(id_estacion_origen="abc")
        self.assertIn("identificador no numérico", motivo)

    def test_duracion_negativa_o_texto(self):
        self.assertIn("duración", self.motivo_de(duracion_recorrido="-5"))
        self.assertIn("duración", self.motivo_de(duracion_recorrido="rápido"))

    def test_duracion_cero_entre_estaciones_distintas(self):
        motivo = self.motivo_de(duracion_recorrido="0")
        self.assertEqual(motivo, "duración 0 entre estaciones distintas")

    def test_duracion_cero_en_la_misma_estacion_es_valida(self):
        validos, rechazos = limpiar_datos([
            registro(duracion_recorrido="0", id_estacion_destino="10",
                     nombre_estacion_destino="Estación A")
        ])
        self.assertEqual(len(validos), 1)
        self.assertEqual(rechazos, [])

    def test_id_duplicado_conserva_la_primera_aparicion(self):
        validos, rechazos = limpiar_datos([
            registro(id_recorrido="7"),
            registro(id_recorrido="7", id_estacion_destino="30",
                     nombre_estacion_destino="Estación C"),
        ])
        self.assertEqual(len(validos), 1)
        self.assertEqual(validos[0].id_destino, "20")
        self.assertEqual(rechazos[0]["motivo"], "id de viaje duplicado")
        self.assertEqual(rechazos[0]["fila"], 2)

    def test_faltan_columnas_en_el_esquema(self):
        sin_columna = registro()
        del sin_columna["id_estacion_destino"]
        with self.assertRaises(ErrorValidacion) as ctx:
            validar_esquema([sin_columna])
        self.assertIn("id_estacion_destino", str(ctx.exception))

    def test_sin_registros(self):
        with self.assertRaises(ErrorValidacion):
            validar_esquema([])

    def test_periodo_invertido(self):
        with self.assertRaises(ErrorValidacion):
            seleccionar_periodo(
                [], datetime(2024, 1, 24), datetime(2024, 1, 23)
            )

    def test_periodo_sin_viajes_da_reporte_vacio(self):
        filas, *_ = procesar(
            [registro()], "2025-01-01 00:00:00", "2025-01-02 00:00:00"
        )
        self.assertEqual(filas, [])
        verificar_resultado(filas, 0)

    def test_formato_de_archivo_no_soportado(self):
        with self.assertRaises(ErrorFuente):
            fuente_para("datos.xlsx")

    def test_archivo_inexistente(self):
        with self.assertRaises(ErrorFuente):
            FuenteCSV().cargar("no_existe.csv")

    def test_json_que_no_es_una_lista(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "malo.json"
            ruta.write_text('{"a": 1}', encoding="utf-8")
            with self.assertRaises(ErrorFuente):
                FuenteJSON().cargar(ruta)

    def test_json_mal_formado(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "roto.json"
            ruta.write_text("[{", encoding="utf-8")
            with self.assertRaises(ErrorFuente):
                FuenteJSON().cargar(ruta)


class PropiedadesDelResultado(unittest.TestCase):
    def registros_variados(self):
        return [
            registro(id_recorrido="1"),
            registro(id_recorrido="2", id_estacion_destino="30",
                     nombre_estacion_destino="Estación C"),
            registro(id_recorrido="3", id_estacion_origen="30",
                     nombre_estacion_origen="Estación C"),
            registro(id_recorrido="4", id_estacion_destino="10",
                     nombre_estacion_destino="Estación A"),
            # Inválidos: no deben alterar los conteos.
            registro(id_recorrido="5", id_estacion_destino=""),
            registro(id_recorrido="6",
                     fecha_destino_recorrido="2024-01-23 08:00:00"),
            registro(id_recorrido="1"),
        ]

    def test_la_suma_de_balances_es_cero(self):
        filas, *_ = procesar(self.registros_variados())
        self.assertEqual(sum(f["balance"] for f in filas), 0)

    def test_salidas_y_llegadas_igualan_los_viajes_seleccionados(self):
        filas, _, _, elegidos = procesar(self.registros_variados())
        self.assertEqual(sum(f["salidas"] for f in filas), len(elegidos))
        self.assertEqual(sum(f["llegadas"] for f in filas), len(elegidos))
        verificar_resultado(filas, len(elegidos))

    def test_los_rechazados_no_alteran_los_conteos(self):
        todos = self.registros_variados()
        solo_validos = todos[:4]
        self.assertEqual(procesar(todos)[0], procesar(solo_validos)[0])

    def test_toda_fila_rechazada_tiene_motivo(self):
        _, _, rechazos, _ = procesar(self.registros_variados())
        self.assertEqual(len(rechazos), 3)
        self.assertTrue(all(r["motivo"] for r in rechazos))

    def test_validos_mas_rechazados_igualan_los_leidos(self):
        registros = self.registros_variados()
        _, validos, rechazos, _ = procesar(registros)
        self.assertEqual(len(validos) + len(rechazos), len(registros))

    def test_resultado_repetible_con_las_mismas_entradas(self):
        registros = self.registros_variados()
        self.assertEqual(procesar(registros)[0], procesar(registros)[0])

    def test_verificar_resultado_detecta_balance_inconsistente(self):
        filas = [{"id_estacion": "1", "nombre_estacion": "A",
                  "salidas": 1, "llegadas": 0, "balance": -1}]
        with self.assertRaises(ErrorResultado):
            verificar_resultado(filas, 1)


class EquivalenciaCSVyJSON(unittest.TestCase):
    def escribir_equivalentes(self, carpeta, registros):
        ruta_csv = Path(carpeta) / "viajes.csv"
        ruta_json = Path(carpeta) / "viajes.json"
        with ruta_csv.open("w", encoding="utf-8", newline="") as f:
            escritor = csv.DictWriter(f, fieldnames=CAMPOS_OBLIGATORIOS)
            escritor.writeheader()
            escritor.writerows(registros)
        ruta_json.write_text(
            json.dumps(registros, ensure_ascii=False), encoding="utf-8"
        )
        return ruta_csv, ruta_json

    def test_ambas_lecturas_dan_los_mismos_registros(self):
        registros = [registro(id_recorrido=str(i)) for i in range(1, 6)]
        registros[2]["nombre_estacion_origen"] = "Estación, con coma"
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_csv, ruta_json = self.escribir_equivalentes(carpeta, registros)
            self.assertEqual(
                FuenteCSV().cargar(ruta_csv), FuenteJSON().cargar(ruta_json)
            )

    def test_ambas_lecturas_generan_el_mismo_reporte(self):
        registros = [
            registro(id_recorrido="1"),
            registro(id_recorrido="2", id_estacion_destino="30",
                     nombre_estacion_destino="Estación C"),
        ]
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_csv, ruta_json = self.escribir_equivalentes(carpeta, registros)
            reporte_csv = procesar(fuente_para(ruta_csv).cargar(ruta_csv))[0]
            reporte_json = procesar(fuente_para(ruta_json).cargar(ruta_json))[0]
        self.assertEqual(reporte_csv, reporte_json)

    @unittest.skipUnless(
        (RAIZ / "data" / "viajes_muestra.csv").exists()
        and (RAIZ / "data" / "viajes_muestra.json").exists(),
        "no está la muestra de datos en data/",
    )
    def test_muestra_del_repositorio_es_equivalente_en_csv_y_json(self):
        desde_csv = FuenteCSV().cargar(RAIZ / "data" / "viajes_muestra.csv")
        desde_json = FuenteJSON().cargar(RAIZ / "data" / "viajes_muestra.json")
        self.assertGreaterEqual(len(desde_csv), 50)
        self.assertEqual(desde_csv, desde_json)


class Exportacion(unittest.TestCase):
    def test_guardar_resultado_y_rechazos(self):
        filas, _, rechazos, _ = procesar(
            [registro(), registro(id_recorrido="2", id_estacion_destino="")]
        )
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_reporte = Path(carpeta) / "sub" / "reporte.csv"
            ruta_rechazos = Path(carpeta) / "sub" / "rechazos.csv"
            guardar_resultado(filas, ruta_reporte)
            guardar_rechazos(rechazos, ruta_rechazos)
            leido = FuenteCSV().cargar(ruta_reporte)
            leido_rechazos = FuenteCSV().cargar(ruta_rechazos)
        self.assertEqual(len(leido), 2)
        self.assertEqual(
            {f["id_estacion"]: int(f["balance"]) for f in leido},
            {"10": -1, "20": 1},
        )
        self.assertEqual(len(leido_rechazos), 1)
        self.assertEqual(leido_rechazos[0]["id_recorrido"], "2")


if __name__ == "__main__":
    unittest.main()