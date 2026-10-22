## Balance de movimientos de estaciones Ecobici (Buenos Aires)
Candelaria Grosso 

Trabajo Práctico 2 de Programación Orientada a Datos
Licenciatura en Ciencia de Datos, UCA

## Problema, usuario y solución propuesta

Problema. Quien revisa la operación de una red de bicicletas compartidas
necesita saber cuántas bicicletas salen y cuántas llegan a cada estación en una
franja horaria. Los archivos públicos de viajes pueden contener registros
incompletos o inconsistentes (sin estación, con el fin anterior al inicio,
con fechas inexistentes o repetidos) que alteran esos conteos. Revisarlos a
mano es lento y difícil de repetir.

Usuario. Una persona analista u operadora de la red, que quiere detectar
estaciones que en una franja dada reciben más viajes de los que despachan, o
al revés.

Solución. Una aplicación de consola en Python que lee viajes desde un
archivo CSV o JSON, valida y rechaza los registros inválidos (guardando el
motivo), selecciona una franja temporal y genera un reporte por estación con
salidas, llegadas y balance neto.

## Funcionalidades y modo de uso

- Lee viajes desde un archivo `.csv` o `.json` con la misma estructura.
- Valida cada registro y guarda los rechazados con su motivo.
- Selecciona los viajes cuyo **inicio** está en `[inicio, fin)`; de cada viaje
  seleccionado se cuentan ambos extremos (salida en el origen, llegada en el
  destino).
- Exporta el reporte por estación y el archivo de rechazados.

Argumentos:

| Argumento | Descripción |
|---|---|
| `--entrada` | Archivo de viajes (`.csv` o `.json`). Obligatorio. |
| `--inicio` | Inicio del período, `"AAAA-MM-DD HH:MM:SS"` (incluido). Obligatorio. |
| `--fin` | Fin del período, `"AAAA-MM-DD HH:MM:SS"` (excluido). Obligatorio. |
| `--salida` | CSV del reporte. Por defecto `outputs/balance_estaciones.csv`. |
| `--rechazos` | CSV de rechazados. Por defecto `outputs/viajes_rechazados.csv`. |

## Datos

- Fuente: dataset "Bicicletas Públicas", recurso "Recorridos Realizados
  2024", BA Data, Gobierno de la Ciudad de Buenos Aires.
  https://data.buenosaires.gob.ar/dataset/bicicletas-publicas
- Responsable: Secretaría de Transporte y Obras Públicas, Jefatura de
  Gabinete de Ministros.
- Licencia: CC-BY-2.5-AR. Atribución: Gobierno de la Ciudad de Buenos Aires,
  BA Data.
- Unidad de análisis: cada fila es un viaje.
- Muestra incluida: `data/viajes_muestra.csv` y `data/viajes_muestra.json`,
  200 viajes equivalentes del 2024-01-23. El detalle de las variables, la
  procedencia y cómo obtener el archivo completo está en
  [`data/README.md`](data/README.md).

## Instalación y ejecución

Se necesita Python 3. No hay dependencias externas (solo biblioteca estándar);
ver `requirements.txt`. En Windows se usa `py`; en otros sistemas, `python3`.

Ejecutar la aplicación sobre la muestra (CSV):

```
py src/main.py --entrada data/viajes_muestra.csv --inicio "2024-01-23 07:00:00" --fin "2024-01-23 10:00:00"
```

Con el JSON equivalente se obtiene el mismo reporte:

```
py src/main.py --entrada data/viajes_muestra.json --inicio "2024-01-23 07:00:00" --fin "2024-01-23 10:00:00"
```

Ejecutar las pruebas (desde la carpeta del repositorio):

```
py -m unittest discover -s tests -v
```

## Organización del código

| Archivo | Responsabilidad |
|---|---|
| `src/fuentes.py` | `FuenteDatos` (clase abstracta con `cargar()`), `FuenteCSV` y `FuenteJSON`. Ambas devuelven una lista de diccionarios con los mismos campos. `fuente_para()` elige según la extensión. |
| `src/viaje.py` | Clase `Viaje` (dominio), validación de registros y expresiones regulares. |
| `src/balance.py` | Clase `BalanceEstacion`: acumula salidas y llegadas y calcula el balance. |
| `src/pipeline.py` | Funciones del flujo: `validar_esquema`, `limpiar_datos`, `seleccionar_periodo`, `registrar_movimientos`, `generar_balance`, `verificar_resultado`, `guardar_resultado`, `guardar_rechazos`. |
| `src/main.py` | Argumentos de consola y coordinación del flujo. |
| `tests/test_pipeline.py` | Pruebas con `unittest`. |

Flujo: leer → validar esquema → limpiar → seleccionar período → calcular
balance → verificar resultado → exportar.

Expresiones regulares (en `src/viaje.py`):

- `^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$` valida solo el *formato* de las
  fechas. Que la fecha exista en el calendario (por ejemplo, que no sea
  `2024-02-30`) lo comprueba `datetime.strptime`.
- `^\d+$` valida que los identificadores de viaje y de estación y la duración
  sean números enteros no negativos.

## Decisiones de limpieza

La validación se aplica a todo el archivo antes de seleccionar el período. Se
rechaza (y se registra la fila, el id y el motivo en el CSV de rechazados):

| Motivo | Criterio |
|---|---|
| Campo obligatorio vacío | Falta alguno de los 8 campos usados. |
| Identificador no numérico | `id_recorrido` o ids de estación que no cumplen `^\d+$`. |
| Duración inválida | La duración no es un entero no negativo. |
| Fecha con formato inválido o inexistente | No cumple el patrón o no existe en el calendario. |
| Fin anterior al inicio | `fecha_destino_recorrido` < `fecha_origen_recorrido`. |
| Duración 0 entre estaciones distintas | Es físicamente imposible; en los datos aparece como registros con inicio y fin idénticos. Un viaje de duración 0 que termina en la misma estación se conserva. |
| Id de viaje duplicado | Se conserva la primera aparición. |

Otras decisiones: la clave de estación es el **id numérico** (el número que
aparece en el nombre no coincide con el id); si un id aparece con nombres
distintos se usa el primero visto; los registros rechazados nunca alteran los
conteos; un período sin viajes produce un reporte vacío con un mensaje
explícito, no ceros inventados.

## Ejemplo de resultado

[COMPLETAR: ejecutar el comando de la sección "Instalación y ejecución" con la
muestra y pegar acá el resumen que imprime el programa, por ejemplo la cantidad
de rechazados por motivo y las estaciones con mayor balance positivo y negativo.]

## Interpretación y limitaciones

- `balance = llegadas - salidas`. Un balance **positivo** significa que la
estación recibió más viajes de los que despachó en la franja; uno
**negativo**, que despachó más de los que recibió. La suma de los balances de
todas las estaciones es siempre cero.
- El balance describe **movimientos de viajes**, no el stock de bicicletas
disponibles: no incluye inventario inicial ni reposiciones hechas por la
operación.
- Los viajes se seleccionan por hora de inicio; un viaje que empieza dentro de
la franja y termina fuera igualmente suma su llegada.
- La muestra del repositorio cubre un solo día, por lo que no representa todo
el año.
- Los datos provienen de un sistema real y pueden tener errores que esta
validación no detecta (por ejemplo, una estación equivocada con fechas
coherentes).
- Fuera de alcance: stock disponible, reposición, predicción, mapas y
análisis por características de las personas usuarias.
- La muestra es un subconjunto de 200 viajes, por lo que sus balances sirven para demostrar el funcionamiento y no representan la operación    real de ese día