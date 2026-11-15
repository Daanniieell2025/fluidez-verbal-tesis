"""Regresiones iniciales por tarea y muestra."""

import numpy as np



def ajustar(x, y, conteo):
    """Estima coeficientes, diagnósticos y covarianza robusta."""
    # Una columna por coeficiente y una fila por participante.
    n, k = x.shape
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("El modelo requiere predictores y respuestas finitos")
    if n <= k or np.linalg.matrix_rank(x) < k or np.ptp(y) == 0:
        raise ValueError("Muestra insuficiente, respuesta constante o predictores colineales")
    if conteo:
        if np.any(y < 0) or np.any(y != np.floor(y)):
            raise ValueError("El resultado contiene valores que no son conteos")
        beta = np.zeros(k)
        # Con solo el intercepto, el promedio inicial coincide con la media observada.
        beta[0] = np.log(y.mean())
        for _ in range(100):
            # Newton actualiza beta con el gradiente y la información de Poisson.
            mu = np.exp(x @ beta)
            paso = np.linalg.solve(x.T @ (mu[:, None] * x), x.T @ (y - mu))
            beta += paso
            if np.max(np.abs(paso)) < 1e-9:
                break
        else:
            raise ValueError("Poisson no convergió")
        mu = np.exp(x @ beta)
        # Pearson divide cada residuo al cuadrado por la varianza prevista.
        residuos = y - mu
        inversa = np.linalg.inv(x.T @ (mu[:, None] * x))
        errores = residuos
        diagnostico = (float(np.sum(residuos**2 / mu) / (n - k)),
                       float(np.exp(-mu).sum()), None, None)
    else:
        beta = np.linalg.lstsq(x, y, rcond=None)[0]
        mu = x @ beta
        residuos = y - mu
        inversa = np.linalg.inv(x.T @ x)
        palanca = np.sum((x @ inversa) * x, axis=1)
        if np.any(palanca >= 1 - 1e-10):
            raise ValueError("No se pueden estimar intervalos HC3 por palanca unitaria")
        errores = residuos / (1 - palanca)
        diagnostico = (None, None,
                       float(1 - np.sum(residuos**2) / np.sum((y - y.mean())**2)),
                       float(np.sqrt(np.mean(residuos**2))))
    # La covarianza robusta combina las contribuciones de cada observación.
    influencia = (x @ inversa) * errores[:, None]
    cov = influencia.T @ influencia
    se = np.sqrt(np.diag(cov))
    return beta, se, diagnostico, cov
