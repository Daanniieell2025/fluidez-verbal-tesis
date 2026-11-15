"""Genera los PDF de clústeres y switches para cada tarea."""

import numpy as np
from openpyxl import load_workbook
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import simpleSplit

from graficos import dibujar, predicciones
from modelos import ajustar
from modelos_conteo import binomial_negativa, frecuencias_esperadas


VERDE = "#176542"
NARANJA = "#AE480A"
GRIS = "#4E5553"
MORADO = "#683C72"
RELLENOS = {VERDE: "#A7DFC0", NARANJA: "#FFD0A1"}


def figura(carpeta_pdf, nombre, titulo, subtitulo, series, etiquetas, eje_x, eje_y,
           nota, puntos=False, observados=None):
    pdf = Canvas(str(carpeta_pdf / f"{nombre}.pdf"), pagesize=(790, 495))
    pdf.setTitle(titulo)
    pdf.setFillColor(VERDE)
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(40, 454, titulo)
    pdf.setFillColor(GRIS)
    pdf.setFont("Helvetica", 14)
    pdf.drawString(40, 428, subtitulo)
    dibujar(pdf, (105, 119, 640, 277), series, etiquetas, "", eje_x,
            puntos, eje_y, observados, colores_discontinuos=(NARANJA,),
            presentacion=True, rellenos=RELLENOS)
    pdf.setFont("Helvetica", 13)
    pdf.setFillColor(GRIS)
    for i, linea in enumerate(simpleSplit(nota, "Helvetica", 13, 710)):
        pdf.drawString(40, 52 - 16 * i, linea)
    pdf.save()


def promedios_ajustados(x, columna, valores, beta, cov):
    """Predice para la misma distribución de los otros predictores en cada valor."""
    resultados = []
    for valor in valores:
        diseno = x.copy()
        diseno[:, columna] = valor
        esperados = np.exp(diseno @ beta)
        media = esperados.mean()
        gradiente = (diseno * esperados[:, None]).mean(axis=0) / media
        error_log = np.sqrt(max(0, gradiente @ cov @ gradiente))
        resultados.append((media, media * np.exp(-1.96 * error_log), media * np.exp(1.96 * error_log)))
    return np.array(resultados).T


def intervalos_individuales(x, columna, valores, beta, alfa):
    """Cuantiles predictivos de la mezcla de perfiles, con parámetros estimados fijos."""
    intervalos = []
    for valor in valores:
        perfiles = x.copy()
        perfiles[:, columna] = valor
        mu = np.exp(perfiles @ beta)
        limite = int(np.ceil(max(mu + 12 * np.sqrt(mu + alfa * mu**2))))
        cdf = np.cumsum(frecuencias_esperadas(mu, limite, alfa)) / len(mu)
        intervalos.append(np.searchsorted(cdf, [0.025, 0.975]))
    return np.array(intervalos).T


def generar_graficos_conteo(tarea, destino):
    """Genera las figuras de una tarea en la carpeta de la corrida."""
    carpeta_pdf = destino / tarea / "Conteos"
    carpeta_pdf.mkdir(parents=True, exist_ok=True)
    with (destino / "01_base_maestra_fluidez.xlsx").open("rb") as fuente:
        libro = load_workbook(fuente, read_only=True, data_only=True)
        encabezados, *filas = libro["Muestra elegible"].values
        libro.close()
    registros = [dict(zip(encabezados, fila)) for fila in filas
                 if fila[encabezados.index("id")] is not None]
    sufijo = "SEM" if tarea == "Supermercado" else tarea.lower()
    campos = ("sexo", "edad", "escolaridad", f"cluster_{sufijo}", f"switching_{sufijo}")
    sexo, edad, escolaridad, clusters, switches = np.array(
        [[r[campo] for campo in campos] for r in registros], dtype=float).T
    if not np.isfinite([sexo, edad, escolaridad, clusters, switches]).all():
        raise ValueError("La muestra elegible contiene valores ausentes o no numéricos.")
    if not np.isin(sexo, [0, 1]).all() or np.any(edad < 18):
        raise ValueError("La muestra contiene códigos de sexo o edades fuera del diseño.")
    n = len(sexo)
    # Los modelos exploratorios usan años centrados y reescalados.
    unos = np.ones(n)
    x = np.column_stack((unos, sexo, (edad - 40) / 10, (escolaridad - 12) / 5))
    grupos_edad = np.digitize(edad, [40, 60])
    grupo_escolaridad = (escolaridad > 12).astype(int)
    grupos = (
        ("sexo", "Sexo", sexo, ("Hombres", "Mujeres")),
        ("edad", "Grupo de edad", grupos_edad, ("18–39", "40–59", "60 o más")),
        ("escolaridad", "Escolaridad", grupo_escolaridad, ("Hasta 12 años", "Más de 12 años")),
    )
    categoricas = np.column_stack((unos, sexo, grupos_edad == 1, grupos_edad == 2, grupo_escolaridad))
    continuas = (
        ("edad", "Edad", edad, 2, 40, 10),
        ("escolaridad", "Escolaridad", escolaridad, 3, 12, 5),
    )
    rng = np.random.default_rng(2026)
    for nombre, y in (("clusters", clusters), ("switches", switches)):
        if np.any(y < 0) or np.any(y != y.astype(int)):
            raise ValueError(f"El resultado {nombre} debe contener conteos enteros no negativos.")
        beta, _, _, cov = ajustar(x, y, True)
        beta_cat, _, _, cov_cat = ajustar(categoricas, y, True)
        mu = np.exp(x @ beta)
        residual = (y - mu) / np.sqrt(mu)
        dispersion = np.sum(residual**2) / (n - x.shape[1])
        comparar_nb = nombre == "switches" and dispersion > 1
        if comparar_nb:
            beta_nb, cov_nb, _, alfa = binomial_negativa(x, y, beta)
        conteos = np.arange(int(y.max()) + 2, dtype=float)
        frecuencias = np.bincount(y.astype(int), minlength=len(conteos))
        esperado = np.array(frecuencias_esperadas(mu, len(conteos) - 2))
        serie_observada = (conteos, frecuencias, frecuencias, frecuencias, GRIS)
        ticks = [(k, str(int(k))) for k in conteos[::4]]
        ticks = [t for t in ticks if t[0] <= conteos[-1] - 2] + [(conteos[-1], f"{int(conteos[-1])}+")]
        figura(carpeta_pdf, f"{tarea}_{nombre}_frecuencias", f"{tarea} · Distribución de {nombre}",
               f"Conteos observados · N = {n}", [serie_observada], ticks, "Conteo por persona",
               "Número de personas", "Cada punto de la línea representa la frecuencia observada de un conteo.")
        for clave, rotulo, grupo, nombres in grupos:
            niveles = np.arange(len(nombres))
            simple = np.column_stack((unos, *[grupo == k for k in niveles[1:]]))
            b_simple, _, _, c_simple = ajustar(simple, y, True)
            medias = []
            for k in niveles:
                # Se asigna el grupo a toda la muestra y se conservan los otros predictores.
                perfil = categoricas.copy()
                if clave == "sexo":
                    perfil[:, 1] = k
                elif clave == "edad":
                    perfil[:, 2:4] = (k == 1, k == 2)
                else:
                    perfil[:, 4] = k
                media = np.exp(perfil @ beta_cat)
                # El método delta aproxima el error estándar del logaritmo de la media.
                gradiente = (perfil * media[:, None]).mean(axis=0) / media.mean()
                error = np.sqrt(max(0, gradiente @ cov_cat @ gradiente))
                medias.append(media.mean() * np.exp(np.array([0, -1.96, 1.96]) * error))
            ajustadas = np.array(medias).T
            diseno = np.column_stack((np.ones(len(niveles)), np.eye(len(niveles))[:, 1:]))
            sin_ajuste = predicciones(diseno, b_simple, c_simple)
            figura(carpeta_pdf, f"{tarea}_{nombre}_por_{clave}",
                   f"{tarea} · {nombre.capitalize()} por {rotulo.lower()}",
                   f"Poisson simple y ajustado · N = {n}",
                   [(niveles - .10, *sin_ajuste, MORADO), (niveles + .10, *ajustadas, VERDE)],
                   list(zip(niveles, nombres)), rotulo, f"{nombre.capitalize()} por persona",
                   "Morado: modelo simple. Verde: ajustado por los otros factores. Barras: IC del 95 % de la media.",
                   puntos=True, observados=(grupo + rng.uniform(-.23, .23, n), y))
        for clave, rotulo, observado, columna, centro, escala in continuas:
            valores = np.linspace(observado.min(), observado.max(), 120)
            valores_modelo = (valores - centro) / escala
            curva = promedios_ajustados(x, columna, valores_modelo, beta, cov)
            ticks_x = [(k, str(int(k))) for k in np.unique(np.linspace(valores[0], valores[-1], 6).round())]
            nube = (observado + rng.uniform(-.18, .18, n), y)
            figura(carpeta_pdf, f"{tarea}_{nombre}_curva_{clave}",
                   f"{tarea} · {nombre.capitalize()} a lo largo de la {rotulo.lower()}",
                   f"Poisson ajustado con predictores en años · N = {n}",
                   [(valores, *curva, VERDE)], ticks_x, f"{rotulo} (años)", f"{nombre.capitalize()} por persona",
                   "Puntos: personas, con leve desplazamiento horizontal. Banda: IC del 95 % de la media.", observados=nube)
            if comparar_nb:
                curva_nb = promedios_ajustados(x, columna, valores_modelo, beta_nb, cov_nb)
                for tipo, titulo, limites, nota in (
                    ("medias", "Medias estimadas", (curva[1:], curva_nb[1:]),
                     "Bandas: IC del 95 % de la media. Puntos grises: observaciones."),
                    ("prediccion_individual", "Predicción individual",
                     (intervalos_individuales(x, columna, valores_modelo, beta, 0),
                      intervalos_individuales(x, columna, valores_modelo, beta_nb, alfa)),
                     "Bandas: cuantiles predictivos del 95 %, con parámetros estimados fijos. Puntos: observaciones."),
                ):
                    figura(carpeta_pdf, f"{tarea}_switches_{clave}_{tipo}",
                           f"{tarea} · Switches por {rotulo.lower()} · {titulo}",
                           f"Verde continuo: Poisson   |   Naranjo discontinuo: binomial negativa   |   N = {n}",
                           [(valores, curva[0], *limites[0], VERDE),
                            (valores, curva_nb[0], *limites[1], NARANJA)],
                           ticks_x, f"{rotulo} (años)", "Switches por persona", nota, observados=nube)
        series = [serie_observada, (conteos, esperado, esperado, esperado, VERDE)]
        subtitulo = f"Gris: observado   |   Verde: Poisson   |   N = {n}"
        if comparar_nb:
            esperado_nb = np.array(frecuencias_esperadas(np.exp(x @ beta_nb), len(conteos) - 2, alfa))
            series.append((conteos, esperado_nb, esperado_nb, esperado_nb, NARANJA))
            subtitulo += "   |   Naranjo discontinuo: binomial negativa"
        figura(carpeta_pdf, f"{tarea}_{nombre}_frecuencia_observada_esperada",
               f"{tarea} · {nombre.capitalize()} observados y esperados", subtitulo, series, ticks,
               "Conteo por persona", "Número de personas",
               "Las frecuencias esperadas suman las probabilidades estimadas para los perfiles de la muestra.")
        amplitud = max(1, int(np.ceil(np.max(np.abs(residual)))))
        pdf = Canvas(str(carpeta_pdf / f"{tarea}_{nombre}_residuos_Poisson.pdf"), pagesize=(790, 495))
        pdf.setTitle(f"{tarea} · Residuos de Pearson para {nombre}")
        pdf.setFillColor(VERDE)
        pdf.setFont("Helvetica-Bold", 24)
        pdf.drawString(40, 454, f"{tarea} · Residuos de Pearson para {nombre}")
        pdf.setFont("Helvetica", 14)
        pdf.drawString(40, 428, f"Poisson ajustado · N = {n} · Dispersión de Pearson = {np.sum(residual**2)/(n-x.shape[1]):.2f}")
        xmin, xmax = mu.min(), mu.max()
        px = lambda v: 105 + 640 * (v - xmin) / (xmax - xmin)
        py = lambda v: 257 + 138 * v / amplitud
        pdf.setFillColor(GRIS)
        for v in np.linspace(-amplitud, amplitud, 5):
            pdf.setStrokeColor(VERDE if v == 0 else "#DDE4DE")
            pdf.line(105, py(v), 745, py(v))
            pdf.drawRightString(96, py(v) - 4, f"{v:g}")
        pdf.setStrokeColor(GRIS)
        pdf.line(105, 119, 105, 395)
        pdf.line(105, 119, 745, 119)
        for v in np.linspace(xmin, xmax, 5):
            pdf.drawCentredString(px(v), 97, f"{v:.1f}")
        pdf.setFillAlpha(.42)
        for m, r in zip(mu, residual):
            pdf.circle(px(m), py(r), 2.8, fill=1, stroke=0)
        pdf.setFillAlpha(1)
        pdf.setFont("Helvetica-Bold", 17)
        pdf.drawCentredString(425, 73, "Conteo medio ajustado")
        pdf.saveState()
        pdf.translate(47, 257)
        pdf.rotate(90)
        pdf.drawCentredString(0, 0, "Residuo de Pearson")
        pdf.restoreState()
        pdf.setFont("Helvetica", 13)
        pdf.drawString(40, 48, "Cada punto es una persona. La línea verde marca un residuo igual a cero.")
        pdf.save()
