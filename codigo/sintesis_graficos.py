"""Genera las figuras de síntesis de asociaciones ajustadas entre tareas."""

import numpy as np
from openpyxl import load_workbook
from reportlab.pdfgen.canvas import Canvas

from modelos import ajustar


TAREAS = (
    ("P", "p", "#176542", 0),
    ("R", "r", "#683C72", 1),
    ("Supermercado", "SEM", "#AE480A", 2),
)
COMPARACIONES = (
    "Mujeres frente a hombres",
    "40–59 frente a 18–39 años",
    "60 o más frente a 18–39 años",
    "Más de 12 frente a hasta 12 años",
)


def marcar(pdf, x, y, forma):
    if forma == 0:
        pdf.circle(x, y, 4.5, stroke=0, fill=1)
    elif forma == 1:
        pdf.rect(x - 4, y - 4, 8, 8, stroke=0, fill=1)
    else:
        rombo = pdf.beginPath()
        rombo.moveTo(x, y + 5)
        rombo.lineTo(x + 5, y)
        rombo.lineTo(x, y - 5)
        rombo.lineTo(x - 5, y)
        rombo.close()
        pdf.drawPath(rombo, stroke=0, fill=1)


def figura(ruta, resultado, datos, n, conteo=True):
    pdf = Canvas(str(ruta), pagesize=(790, 490))
    tinta = "#222A27"
    x0, ancho = 297, 443
    # Las razones se grafican en logaritmos y las diferencias en su escala original.
    if conteo:
        menor, mayor = .65, 1.5
        marcas = (.7, .8, .9, 1, 1.1, 1.2, 1.3, 1.4, 1.5)
        igualdad = 1
        familia = "Modelos de Poisson"
        eje = "Razón de conteos esperados (escala logarítmica)"
    else:
        limite = max(.4, np.ceil(np.abs(datos).max() / .2) * .2)
        menor, mayor = -limite, limite
        marcas = np.linspace(menor, mayor, 9).round(3)
        igualdad = 0
        familia = "Regresión lineal"
        eje = "Diferencia ajustada (unidades del tamaño promedio)"

    def pos(valor):
        proporcion = (np.log(valor / menor) / np.log(mayor / menor)
                      if conteo else (valor - menor) / (mayor - menor))
        return x0 + ancho * proporcion

    pdf.setTitle(f"{resultado.capitalize()} · Síntesis entre tareas")
    pdf.setFillColor(tinta)
    pdf.setFont("Helvetica-Bold", 23)
    pdf.drawString(40, 451, f"{resultado.capitalize()} · Asociaciones ajustadas por tarea")
    pdf.setFont("Helvetica", 15)
    pdf.drawString(40, 424, f"{familia} · IC robustos del 95 % · N = {n} por tarea")
    for (tarea, _, color, forma), x in zip(TAREAS, (51, 134, 218)):
        pdf.setFillColor(color)
        marcar(pdf, x, 393, forma)
        pdf.drawString(x + 11, 388, tarea)

    pdf.setFont("Helvetica", 14)
    for valor in marcas:
        x = pos(valor)
        pdf.setStrokeColor("#66756C" if valor == igualdad else "#DCE4DF")
        pdf.setLineWidth(1.5 if valor == igualdad else .7)
        pdf.line(x, 98, x, 367)
        pdf.setFillColor(tinta)
        etiqueta = f"{valor:.1f}" if conteo else f"{valor:.3f}".rstrip("0").rstrip(".")
        pdf.drawCentredString(x, 77, etiqueta.replace(".", ","))
    for i, etiqueta in enumerate(COMPARACIONES):
        centro = 337 - 67 * i
        pdf.setFillColor(tinta)
        pdf.drawString(40, centro - 5, etiqueta)
        for (_, _, color, forma), estimaciones in zip(TAREAS, datos):
            media, bajo, alto = estimaciones[i]
            if bajo < menor or alto > mayor:
                raise ValueError("Un intervalo excede el eje de la figura.")
            y = centro + (1 - forma) * 15
            pdf.setStrokeColor(color)
            pdf.setFillColor(color)
            pdf.setLineWidth(1.8)
            pdf.line(pos(bajo), y, pos(alto), y)
            marcar(pdf, pos(media), y, forma)

    pdf.setFillColor(tinta)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(x0 + ancho / 2, 49, eje)
    pdf.setFont("Helvetica", 13)
    pdf.drawString(40, 26, f"La línea vertical en {igualdad} representa igualdad de promedios entre categorías.")
    pdf.save()


def generar_sintesis(destino):
    """Reúne los contrastes ajustados de las tres tareas en figuras."""
    with (destino / "01_base_maestra_fluidez.xlsx").open("rb") as fuente:
        libro = load_workbook(fuente, read_only=True, data_only=True)
        encabezados, *filas = libro["Muestra elegible"].values
        libro.close()
    registros = [dict(zip(encabezados, fila)) for fila in filas
                 if fila[encabezados.index("id")] is not None]
    x = np.array([[1, r["sexo"], 40 <= r["edad"] < 60, r["edad"] >= 60,
                   r["escolaridad"] > 12] for r in registros], float)
    carpeta = destino / "Sintesis"
    carpeta.mkdir(parents=True, exist_ok=True)
    for resultado, campo in (("clusteres", "cluster"), ("switches", "switching"),
                             ("tamano_promedio", "prom_cluster")):
        conteo = campo != "prom_cluster"
        datos = []
        for tarea, sufijo, _, _ in TAREAS:
            y = np.array([r[f"{campo}_{sufijo}"] for r in registros], float)
            if not np.isfinite(y).all() or np.any(y < 0) or (conteo and np.any(y != np.floor(y))):
                raise ValueError(f"Valores inválidos en {tarea}: {campo}")
            beta, error, _, _ = ajustar(x, y, conteo)
            intervalos = beta[1:, None] + error[1:, None] * [0, -1.96, 1.96]
            datos.append(np.exp(intervalos) if conteo else intervalos)
        titulo = "clústeres" if campo == "cluster" else resultado
        if not conteo:
            titulo = "tamaño promedio"
        figura(carpeta / f"Sintesis_{resultado}_tareas.pdf", titulo, datos, len(x), conteo)
