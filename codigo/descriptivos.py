"""Calcula descriptivos de participantes y rendimiento."""

from statistics import mean, median, quantiles, stdev


ESTADISTICAS = ("N total", "Válidos", "Faltantes", "Ceros", "Media", "Desv. estándar",
                "Mediana", "Q1", "Q3", "Mínimo", "Máximo")


def resumir(filas, campo):
    valores = [fila[campo] for fila in filas if fila[campo] is not None]
    n = len(valores)
    q1, _, q3 = quantiles(valores, method="inclusive") if n > 1 else (None, None, None)
    return (len(filas), n, len(filas) - n, valores.count(0),
            mean(valores) if n else None, stdev(valores) if n > 1 else None,
            median(valores) if n else None, q1, q3,
            min(valores) if n else None, max(valores) if n else None)
