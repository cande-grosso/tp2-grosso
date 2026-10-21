# Datos

## Fuente
- Dataset: Bicicletas Públicas, recurso "Recorridos Realizados 2024".
- Portal: BA Data, Gobierno de la Ciudad de Buenos Aires.
- URL: https://data.buenosaires.gob.ar/dataset/bicicletas-publicas
- Responsable: [COMPLETAR, según la página del dataset]
- Licencia: [COMPLETAR, según la página del dataset]
- Fecha de consulta: [COMPLETAR, día de la descarga]

## Unidad de análisis
Cada fila es un viaje realizado en el sistema Ecobici.

## Variables utilizadas
| Variable | Descripción |
|---|---|
| id_recorrido | Identificador del viaje |
| duracion_recorrido | Duración en segundos |
| fecha_origen_recorrido | Fecha y hora de inicio (AAAA-MM-DD HH:MM:SS) |
| fecha_destino_recorrido | Fecha y hora de fin (AAAA-MM-DD HH:MM:SS) |
| id_estacion_origen | Identificador numérico de la estación de salida |
| nombre_estacion_origen | Nombre de la estación de salida |
| id_estacion_destino | Identificador numérico de la estación de llegada |
| nombre_estacion_destino | Nombre de la estación de llegada |

## Muestra incluida
`viajes_muestra.csv` y `viajes_muestra.json`: 200 viajes elegidos al azar
(semilla 42) entre los 2041 que comienzan el 2024-01-23 en el archivo
completo (más de 3,5 millones de líneas, no incluido en el repositorio).
Ambos archivos tienen el mismo contenido; todos los valores se guardan
como texto.

## Variables excluidas
El archivo original incluye datos de las personas usuarias (`id_usuario`,
`genero`), el modelo de bicicleta, direcciones y coordenadas. No se usan en
esta versión y no se copian a la muestra.

## Limitaciones
- Hay viajes con duración 0 y mismo instante de inicio y fin, aun entre
  estaciones distintas. Se tratan en la limpieza.
- El número que aparece en el nombre de una estación no coincide con su id
  numérico. Se usa el id como clave.
- La muestra cubre un solo día y no representa todo el año.
- El balance mide movimientos de viajes, no bicicletas disponibles.