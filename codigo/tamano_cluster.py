"""Modela el tamaño registrado en toda la muestra elegible."""

import numpy as np

from base_final import TAREAS
from graficos_conteo import VERDE, figura
from modelos import ajustar
from modelos_conteo import MODELOS, PARAMETROS, CODIGOS
from salida import tabla


MEDIDA = "Tamaño promedio de clúster"


def analizar_tamano(libro, destino, filas):
    """Exporta efectos lineales HC3 y gráficos para cada tarea."""
    efectos, diagnosticos = [], []
    rng = np.random.default_rng(2026)
    for tarea, sufijo in TAREAS.items():
        # El cero registrado por ausencia de clúster también entra al modelo.
        sexo, edad, escolaridad, y = np.array([
            [f["sexo"], f["edad"], f["escolaridad"], f[f"prom_cluster_{sufijo}"]]
            for f in filas
        ], dtype=float).T
        n = len(y)
        sin_cluster = sum(f[f"cluster_{sufijo}"] == 0 for f in filas)
        unos = np.ones(n)
        edades = np.digitize(edad, [40, 60])
        estudios = (escolaridad > 12).astype(int)
        x = np.column_stack((unos, sexo, edades == 1, edades == 2, estudios))
        carpeta = destino / tarea / "Tamano_promedio"
        carpeta.mkdir(parents=True, exist_ok=True)

        for modelo, columnas in MODELOS:
            # Los coeficientes lineales son diferencias en la escala original.
            beta, error, diag, cov = ajustar(x[:, columnas], y, False)
            ecuacion = f"{beta[0]:.6f}" + "".join(
                f" {valor:+.6f}·{CODIGOS[j]}" for j, valor in zip(columnas[1:], beta[1:])
            )
            predichos = x[:, columnas] @ beta
            diagnosticos.append((tarea, modelo, n, sin_cluster, diag[2], diag[3],
                                 float(predichos.min()), float(predichos.max()), ecuacion))
            for j, valor, ee in zip(columnas, beta, error):
                efectos.append((tarea, modelo, n, PARAMETROS[j], float(valor), float(ee),
                                float(valor - 1.96 * ee), float(valor + 1.96 * ee)))

        # Se promedian los perfiles con los otros predictores conservados.
        for clave, etiqueta, grupo, nombres, columnas in (
            ("sexo", "Sexo", sexo, ("Hombres", "Mujeres"), (1,)),
            ("edad", "Grupo de edad", edades, ("18–39", "40–59", "60 o más"), (2, 3)),
            ("escolaridad", "Escolaridad", estudios, ("Hasta 12 años", "Más de 12 años"), (4,)),
        ):
            niveles = np.arange(len(nombres))
            perfiles = np.tile(x.mean(axis=0), (len(niveles), 1))
            perfiles[:, columnas] = np.eye(len(niveles))[:, 1:]
            graficar(carpeta, tarea, clave, etiqueta, perfiles, beta, cov, niveles,
                     list(zip(niveles, nombres)), (grupo + rng.uniform(-.18, .18, n), y), True)

        # Los gráficos continuos ilustran tendencias en años dentro del rango observado.
        continuo = np.column_stack((unos, sexo, edad, escolaridad))
        b, _, diag, c = ajustar(continuo, y, False)
        predichos = continuo @ b
        diagnosticos.append((tarea, "Exploratorio en años", n, sin_cluster, diag[2], diag[3],
                             float(predichos.min()), float(predichos.max()),
                             f"{b[0]:.6f} {b[1]:+.6f}·M {b[2]:+.6f}·Edad {b[3]:+.6f}·Escolaridad"))
        for clave, etiqueta, valores, columna in (
            ("edad", "Edad (años)", edad, 2),
            ("escolaridad", "Escolaridad (años)", escolaridad, 3),
        ):
            puntos = np.linspace(valores.min(), valores.max(), 120)
            perfiles = np.tile(continuo.mean(axis=0), (len(puntos), 1))
            perfiles[:, columna] = puntos
            marcas = np.unique(np.linspace(puntos[0], puntos[-1], 6).round()).astype(int)
            graficar(carpeta, tarea, f"curva_{clave}", etiqueta, perfiles, b, c, puntos,
                     [(v, str(v)) for v in marcas], (valores + rng.uniform(-.18, .18, n), y), False)

    tabla(libro, "Tamaño asociaciones", "Regresión lineal del tamaño promedio de clúster",
          ("Tarea", "Modelo", "N", "Comparación", "Coeficiente", "Error HC3", "IC 95 % inf.", "IC 95 % sup."),
          efectos, "Las diferencias se expresan en unidades de la medida registrada. Cero indica igualdad.")
    tabla(libro, "Tamaño diagnóstico", "Ajuste lineal del tamaño promedio de clúster",
          ("Tarea", "Modelo", "N", "Sin clúster", "R²", "RMSE", "Predicción mínima", "Predicción máxima", "Ecuación"),
          diagnosticos, "RMSE es el error dentro de la muestra. El modelo incluye los ceros registrados por ausencia de clúster.")


def graficar(carpeta, tarea, clave, etiqueta, perfiles, beta, cov, valores, marcas, nube, puntos):
    """Dibuja la media ajustada y su intervalo robusto sobre los valores observados."""
    media = perfiles @ beta
    error = np.sqrt(np.maximum(0, np.einsum("ij,jk,ik->i", perfiles, cov, perfiles)))
    figura(carpeta, f"{tarea}_tamano_promedio_{clave}", f"{tarea} · {MEDIDA}",
           f"Media ajustada · Muestra elegible, incluidos los ceros · N = {len(nube[1])}",
           [(valores, media, media - 1.96 * error, media + 1.96 * error, VERDE)],
           marcas, etiqueta, MEDIDA,
           "Gris: valores observados. Verde: media ajustada e IC robusto del 95 %.",
           puntos=puntos, observados=nube)
