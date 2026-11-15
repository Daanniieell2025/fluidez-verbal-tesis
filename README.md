# Análisis de fluidez verbal

Código del análisis estadístico que acompaña la tesis sobre asociaciones
entre sexo, edad, escolaridad y fluidez verbal. El flujo analiza las tareas
fonológicas P y R y la tarea semántica Supermercado.

**Autor del código:** Daniel González Iturra.

## Qué calcula

- Descriptivos de la muestra y del rendimiento por tarea.
- Regresión de Poisson simple y ajustada para el número de clústeres y de
  switches. Para switches en P y R, incluye el análisis de sensibilidad
  con binomial negativa.
- Regresión lineal con errores estándar robustos HC3 para el tamaño promedio
  de clúster, incluidos los ceros registrados por ausencia de clústeres.
- Gráficos por tarea y figuras de síntesis.

## Instalación y ejecución

Se requiere Python 3.10 o posterior. Desde la raíz del repositorio, crea un entorno:

```sh
python -m venv .venv
```

En Windows, desde CMD:

```cmd
.\.venv\Scripts\python.exe -m pip install -r codigo/requirements.txt
.\.venv\Scripts\python.exe codigo/main.py --entrada "datos/base_integrada.xlsx" --salida resultados
```

En macOS o Linux:

```sh
.venv/bin/python -m pip install -r codigo/requirements.txt
.venv/bin/python codigo/main.py --entrada "datos/base_integrada.xlsx" --salida resultados
```

El argumento `--entrada` debe apuntar a tu copia autorizada de la base integrada,
con las correcciones de origen ya aplicadas. Usa una carpeta nueva en `--salida`
para cada corrida.

## Estructura de la entrada

El archivo Excel debe contener una hoja `Sheet1` con encabezados en la primera
fila y un registro por participante. Estas son las columnas requeridas:

| Contenido | Columnas |
| --- | --- |
| Identificación y selección | `id` único, `cohorte`, `cumple_criterios` (1 = incluida, 0 = excluida) |
| Características sociodemográficas | `sexo` (0 = hombre, 1 = mujer), `edad`, `escolaridad` en años |
| Antecedentes y Mini-Mental | `ant_psiq`, `ant_neuro`, `puntaje_mmse` |
| Número de clústeres | `cluster_p`, `cluster_r`, `cluster_SEM` |
| Número de switches | `switching_p`, `switching_r`, `switching_SEM` |
| Tamaño promedio de clúster | `prom_cluster_p`, `prom_cluster_r`, `prom_cluster_SEM` |

La elegibilidad se toma de la marca de la base. El programa agrupa la edad en
18–39, 40–59 y 60 años o más, y la escolaridad en hasta 12 años y más de 12 años.
Para reproducir las cifras de la tesis se requiere la base final autorizada.
La carpeta pública contiene el código. Los registros individuales y los archivos
generados a partir de ellos se manejan por separado.

## Archivos generados

La carpeta predeterminada es `resultados/`.

| Salida | Contenido |
| --- | --- |
| `01_base_maestra_fluidez.xlsx` | Registros completos, muestra elegible, descriptivos y cruce con Mini-Mental |
| `02_resultados_regresiones.xlsx` | Comparaciones, coeficientes, ecuaciones y diagnósticos |
| `P/`, `R/`, `Supermercado/` | PDF de conteos y tamaño promedio, en subcarpetas separadas |
| `Sintesis/` | PDF comparativos de las tres tareas |

El flujo parte en `codigo/main.py`. La lectura y validación están en
`base_final.py`. Los modelos y su exportación se organizan en
`modelos.py`, `modelos_conteo.py`, `resultados_finales.py` y
`tamano_cluster.py`. Los PDF de conteos y de síntesis se generan desde
`graficos_conteo.py` y `sintesis_graficos.py`.

Las tablas principales usan grupos de edad y escolaridad. Las curvas
exploratorias usan edad y escolaridad en años. La dispersión de Pearson
y la comparación con binomial negativa se evalúan para cada modelo.
