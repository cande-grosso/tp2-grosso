"""Balance de movimientos de una estación."""


class BalanceEstacion:
    """Acumula las salidas y llegadas de una estación.

    balance = llegadas - salidas. Es un balance de movimientos de viajes,
    no el stock de bicicletas disponibles: no incluye inventario inicial
    ni reposiciones.
    """

    def __init__(self, id_estacion, nombre):
        self.id_estacion = id_estacion
        self.nombre = nombre
        self.salidas = 0
        self.llegadas = 0

    def registrar_salida(self):
        self.salidas += 1

    def registrar_llegada(self):
        self.llegadas += 1

    @property
    def balance(self):
        return self.llegadas - self.salidas

    def a_fila(self):
        """Representa la estación como una fila del reporte."""
        return {
            "id_estacion": self.id_estacion,
            "nombre_estacion": self.nombre,
            "salidas": self.salidas,
            "llegadas": self.llegadas,
            "balance": self.balance,
        }

