"""Exporta los ajustes principales y los análisis de sensibilidad de las tres tareas."""

from math import lgamma

import numpy as np
from openpyxl import Workbook

from base_final import TAREAS
from modelos import ajustar
from modelos_conteo import MODELOS, PARAMETROS, binomial_negativa, ecuacion, indicadores
from salida import tabla
from tamano_cluster import analizar_tamano


def guardar_resultados(destino, filas):
    """Calcula las regresiones y guarda parámetros, contrastes y diagnósticos."""
    # El perfil de referencia tiene ceros en todos los indicadores.
    x = np.array([[1, f["sexo"], 40 <= f["edad"] < 60, f["edad"] >= 60,
                   f["escolaridad"] > 12] for f in filas], dtype=float)
    asociaciones, coeficientes, ecuaciones, diagnosticos = [], [], [], []
    for tarea, sufijo in TAREAS.items():
        for nombre, campo in (("Clústeres", "cluster"), ("Switches", "switching")):
            # Cada respuesta se ajusta por separado sobre la misma muestra.
            y = np.array([f[f"{campo}_{sufijo}"] for f in filas], dtype=float)
            # lgamma(y + 1) calcula log(y!) sin construir el factorial.
            factorial = np.array([lgamma(valor + 1) for valor in y])
            ajustes = []
            for modelo, columnas in MODELOS:
                # El modelo simple toma las columnas de un solo predictor.
                diseno = x[:, columnas]
                beta, error, _, _ = ajustar(diseno, y, True)
                eta = diseno @ beta
                # El enlace logarítmico devuelve medias positivas al exponenciar.
                mu = np.exp(eta)
                log_verosimilitud = float(np.sum(y * eta - mu - factorial))
                metricas = indicadores(y, mu, len(columnas), log_verosimilitud)
                ajustes.append((modelo, "Poisson", columnas, beta, error, metricas))

            # NB2 usa el mismo diseño que Poisson para comparar ajuste y asociaciones.
            modelo, _, columnas, beta, _, metricas = ajustes[-1]
            if nombre == "Switches" and metricas[5] > 1:
                beta_nb, cov, log_verosimilitud, alfa = binomial_negativa(x, y, beta)
                mu = np.exp(x @ beta_nb)
                metricas_nb = indicadores(y, mu, x.shape[1] + 1, log_verosimilitud, alfa)
                ajustes.append((modelo, "NB2", columnas, beta_nb, np.sqrt(np.diag(cov)), metricas_nb))

            for modelo, familia, columnas, beta, errores, metricas in ajustes:
                clave = (tarea, nombre, modelo, familia)
                diagnosticos.append((*clave, *metricas))
                ecuaciones.append((*clave, ecuacion(beta, columnas)))
                for columna, valor, error in zip(columnas, beta, errores):
                    parametro = PARAMETROS[columna]
                    coeficientes.append((*clave, parametro, float(valor), float(error)))
                    if columna != 0:
                        # Se transforma la escala logarítmica en razones de conteos.
                        razon, inferior, superior = np.exp(valor + np.array([0, -1.96, 1.96]) * error)
                        asociaciones.append((*clave, parametro, float(razon),
                                              float(inferior), float(superior)))

    libro = Workbook()
    libro.remove(libro.active)
    claves = ("Tarea", "Conteo", "Modelo", "Familia")
    tabla(libro, "Asociaciones", "Razones de conteos esperados",
          (*claves, "Comparación", "Razón", "IC 95 % inferior", "IC 95 % superior"),
          asociaciones, "Una razón de 1 indica igualdad. Los intervalos usan errores estándar robustos.")
    tabla(libro, "Evaluación del modelo", "Diagnósticos de regresión",
          (*claves, "N", "Parámetros", "Grados de libertad", "Log verosimilitud", "AIC",
           "Dispersión de Pearson", "Ceros observados", "Ceros esperados", "RMSE", "Alfa"),
          diagnosticos, "Compare el AIC entre modelos ajustados al mismo conteo y la misma muestra.")
    tabla(libro, "Coeficientes", "Coeficientes en escala logarítmica",
          (*claves, "Parámetro", "Coeficiente", "Error estándar robusto"), coeficientes)
    tabla(libro, "Ecuaciones", "Ecuaciones del promedio esperado",
          (*claves, "Ecuación"), ecuaciones,
          "M: mujer. E40: 40–59 años. E60: 60 o más años. S: más de 12 años de escolaridad.")
    analizar_tamano(libro, destino, filas)
    for hoja in libro:
        for fila in hoja.iter_rows(min_row=3):
            for celda in fila:
                if isinstance(celda.value, float):
                    celda.number_format = "0.0000"
    libro.save(destino / "02_resultados_regresiones.xlsx")
