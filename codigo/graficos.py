"""Dibuja series, intervalos de confianza y conteos observados en PDF."""

import numpy as np



def predicciones(z, beta, cov):
    z = np.asarray(z, dtype=float)
    eta = z @ beta
    error = np.sqrt(np.maximum(0, np.einsum("ij,jk,ik->i", z, cov, z)))
    return np.exp(eta), np.exp(eta - 1.96 * error), np.exp(eta + 1.96 * error)


def dibujar(pdf, rect, series, etiquetas, titulo, eje_x, puntos=False,
            eje_y="Clusters esperados en P", observados=None, colores_discontinuos=(),
            presentacion=False, rellenos=None):
    x0, y0, ancho, alto = rect
    xmax = max(float(s[0].max()) for s in series)
    xmin = min(float(s[0].min()) for s in series)
    if puntos:
        margen = max((xmax - xmin) * 0.12, 0.1)
        xmin, xmax = xmin - margen, xmax + margen
    ymax = max(float(s[3].max()) for s in series) * 1.08
    if observados is not None:
        obs_x, obs_y = observados
        xmin = min(xmin, float(np.min(obs_x)))
        xmax = max(xmax, float(np.max(obs_x)))
        ymax = max(ymax, float(np.max(obs_y)) * 1.08)
    def xy(x, y):
        return x0 + (x - xmin) / max(xmax - xmin, 1) * ancho, y0 + y / ymax * alto
    pdf.setFillColor("#000000")
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(x0, y0 + alto + 18, titulo)
    pdf.setFont("Helvetica", 16 if presentacion else 8)
    pdf.setLineWidth(0.8 if presentacion else 1)
    for i in range(5):
        y = i * ymax / 4
        _, py = xy(xmin, y)
        pdf.setStrokeColor("#E0E5E1")
        pdf.line(x0, py, x0 + ancho, py)
        pdf.drawRightString(x0 - 9 if presentacion else x0 - 5, py - 4, f"{y:.1f}")
    if presentacion:
        pdf.setStrokeColor("#4E5553")
        pdf.line(x0, y0, x0 + ancho, y0)
        pdf.line(x0, y0, x0, y0 + alto)
    for x, etiqueta in etiquetas:
        px, _ = xy(x, 0)
        pdf.drawCentredString(px, y0 - (22 if presentacion else 15), etiqueta)
    if presentacion:
        pdf.setFont("Helvetica-Bold", 17)
    pdf.drawCentredString(x0 + ancho / 2, y0 - (46 if presentacion else 31), eje_x)
    pdf.saveState()
    pdf.translate(x0 - (58 if presentacion else 30), y0 + alto / 2)
    pdf.rotate(90)
    pdf.drawCentredString(0, 0, eje_y)
    pdf.restoreState()
    if rellenos and not puntos:
        for xs, _, lo, hi, color in reversed(series):
            if color not in rellenos or np.array_equal(lo, hi):
                continue
            pdf.setFillColor(rellenos[color])
            banda = pdf.beginPath()
            banda.moveTo(*xy(xs[0], lo[0]))
            for x, y in zip(xs[1:], lo[1:]):
                banda.lineTo(*xy(x, y))
            for x, y in zip(xs[::-1], hi[::-1]):
                banda.lineTo(*xy(x, y))
            banda.close()
            pdf.drawPath(banda, fill=1, stroke=0)
    if observados is not None:
        pdf.saveState()
        pdf.setFillColor("#555F61")
        pdf.setFillAlpha(0.42 if presentacion else 0.28)
        for x, y in zip(obs_x, obs_y):
            pdf.circle(*xy(x, y), 2.8 if presentacion else 1.9, fill=1, stroke=0)
        pdf.restoreState()
    for xs, mu, lo, hi, color in series:
        pdf.setStrokeColor(color)
        pdf.setFillColor(color)
        if puntos:
            radio = 6 if presentacion else 3.5
            tope = 7 if presentacion else 4
            if presentacion:
                pdf.setLineWidth(2.2)
            for x, m, a, b in zip(xs, mu, lo, hi):
                px, py = xy(x, m)
                pdf.line(px, xy(x, a)[1], px, xy(x, b)[1])
                pdf.line(px - tope, xy(x, a)[1], px + tope, xy(x, a)[1])
                pdf.line(px - tope, xy(x, b)[1], px + tope, xy(x, b)[1])
                pdf.circle(px, py, radio, fill=1, stroke=0)
        else:
            if not rellenos:
                pdf.saveState()
                pdf.setFillAlpha(0.13)
                path = pdf.beginPath()
                coords = [xy(x, y) for x, y in zip(xs, lo)]
                coords += [xy(x, y) for x, y in zip(xs[::-1], hi[::-1])]
                path.moveTo(*coords[0])
                for par in coords[1:]:
                    path.lineTo(*par)
                path.close()
                pdf.drawPath(path, fill=1, stroke=0)
                pdf.restoreState()
            elif len(series) > 1 and not np.array_equal(lo, hi):
                pdf.setLineWidth(1)
                pdf.setDash(5, 3) if color in colores_discontinuos else pdf.setDash()
                for limite in (lo, hi):
                    borde = pdf.beginPath()
                    borde.moveTo(*xy(xs[0], limite[0]))
                    for x, y in zip(xs[1:], limite[1:]):
                        borde.lineTo(*xy(x, y))
                    pdf.drawPath(borde)
                pdf.setDash()
            pdf.setStrokeColor(color)
            path = pdf.beginPath()
            path.moveTo(*xy(xs[0], mu[0]))
            for x, y in zip(xs[1:], mu[1:]):
                path.lineTo(*xy(x, y))
            pdf.setLineWidth(2.8 if presentacion else 2)
            if color in colores_discontinuos:
                pdf.setDash(5, 3)
            pdf.drawPath(path)
            pdf.setDash()
