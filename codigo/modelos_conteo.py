"""Modelos de conteo, diagnósticos y codificación de las comparaciones."""

from math import lgamma

import numpy as np


PARAMETROS = ("Intercepto", "Mujer frente a hombre", "40–59 frente a 18–39",
              "60 o más frente a 18–39", "Más de 12 frente a hasta 12 años")
CODIGOS = ("1", "M", "E40", "E60", "S")
MODELOS = (("Simple · Sexo", (0, 1)), ("Simple · Edad", (0, 2, 3)),
           ("Simple · Escolaridad", (0, 4)), ("Ajustado", (0, 1, 2, 3, 4)))


def binomial_negativa(x, y, beta_poisson):
    """Maximiza la verosimilitud NB2 perfilando la dispersión alfa."""
    factorial = np.array([lgamma(v + 1) for v in y])

    def perfil(log_alfa):
        # Para cada alfa fijo se estima beta maximizando la verosimilitud NB2.
        alfa = np.exp(log_alfa)
        r = 1 / alfa
        constante = np.array([lgamma(v + r) - lgamma(r) for v in y]) - factorial

        def logver(beta):
            eta = x @ beta
            return float(np.sum(constante + y * (log_alfa + eta)
                                - (y + r) * np.logaddexp(0, log_alfa + eta)))

        beta = beta_poisson.copy()
        ll = logver(beta)
        for _ in range(100):
            mu = np.exp(x @ beta)
            pesos = mu / (1 + alfa * mu)
            paso = np.linalg.solve(x.T @ (pesos[:, None] * x),
                                   x.T @ ((y - mu) / (1 + alfa * mu)))
            if np.max(np.abs(paso)) < 1e-8:
                return ll, beta
            for reduccion in range(20):
                candidato = beta + paso / 2**reduccion
                nuevo = logver(candidato)
                if nuevo >= ll - 1e-10:
                    beta, ll = candidato, nuevo
                    break
            else:
                break
        raise ValueError("Binomial negativa no convergió")

    # La grilla acota la búsqueda del máximo en la escala logarítmica de alfa.
    grilla = np.linspace(-10, 3, 27)
    mejor = int(np.argmax([perfil(a)[0] for a in grilla]))
    inferior, superior = grilla[max(0, mejor - 1)], grilla[min(len(grilla) - 1, mejor + 1)]
    for _ in range(32):
        a = inferior + (superior - inferior) / 3
        b = superior - (superior - inferior) / 3
        if perfil(a)[0] < perfil(b)[0]:
            inferior = a
        else:
            superior = b
    log_alfa = (inferior + superior) / 2
    ll, beta = perfil(log_alfa)
    alfa = float(np.exp(log_alfa))
    mu = np.exp(x @ beta)
    # La covarianza robusta de beta se calcula con el alfa estimado fijo.
    pesos = mu / (1 + alfa * mu)
    inversa = np.linalg.inv(x.T @ (pesos[:, None] * x))
    influencia = (x @ inversa) * ((y - mu) / (1 + alfa * mu))[:, None]
    cov = influencia.T @ influencia
    return beta, cov, ll, alfa


def frecuencias_esperadas(mu, limite, alfa=0):
    """Suma probabilidades individuales; la última categoría recoge la cola."""
    if alfa:
        p = np.exp(-np.log1p(alfa * mu) / alfa)
    else:
        p = np.exp(-mu)
    frecuencias = [float(p.sum())]
    for k in range(1, limite + 1):
        p = p * (mu * (1 + alfa * (k - 1))) / (k * (1 + alfa * mu))
        frecuencias.append(float(p.sum()))
    frecuencias.append(max(0.0, len(mu) - sum(frecuencias)))
    return frecuencias


def indicadores(y, mu, k, ll, alfa=0):
    n = len(y)
    gl = n - k
    varianza = mu + alfa * mu**2
    dispersion = float(np.sum((y - mu)**2 / varianza) / gl)
    ceros = frecuencias_esperadas(mu, 0, alfa)[0]
    return [n, k, gl, ll, 2 * (k - ll), dispersion, int(np.sum(y == 0)), ceros,
            float(np.sqrt(np.mean((y - mu)**2))), alfa if alfa else None]


def ecuacion(beta, columnas):
    terminos = "".join(f" {valor:+.8f}·{CODIGOS[j]}" for j, valor in zip(columnas[1:], beta[1:]))
    return f"μ = exp({beta[0]:.8f}{terminos})"
