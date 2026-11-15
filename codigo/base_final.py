"""Lee la estructura integrada y documenta la muestra que entra a los modelos."""

from collections import Counter
from math import isfinite
from zipfile import BadZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill

from descriptivos import ESTADISTICAS, resumir
from salida import GUIA, tabla


# Los sufijos corresponden a los encabezados originales del archivo integrado.
TAREAS = {"P": "p", "R": "r", "Supermercado": "SEM"}
CONTEOS = tuple(f"{campo}_{sufijo}" for sufijo in TAREAS.values()
                for campo in ("cluster", "switching"))
REQUERIDOS = ("id", "cohorte", "sexo", "edad", "escolaridad", "cumple_criterios",
              "ant_psiq", "ant_neuro", "puntaje_mmse", *CONTEOS,
              *(f"prom_cluster_{s}" for s in TAREAS.values()))


def grupo_edad(edad):
    """Devuelve la categoría acordada para el modelo principal."""
    return "18–39" if edad < 40 else "40–59" if edad < 60 else "60 o más"


def grupo_escolaridad(anios):
    """Incluye exactamente 12 años en la primera categoría."""
    return "Hasta 12 años" if anios <= 12 else "Más de 12 años"


def leer_integrada(ruta):
    """Conserva el orden y los campos de Sheet1 y valida los datos analíticos."""
    try:
        libro = load_workbook(ruta, read_only=True, data_only=True)
    except BadZipFile as error:
        raise ValueError("El archivo de entrada no es un Excel válido.") from error
    try:
        if "Sheet1" not in libro:
            raise ValueError("Falta la hoja Sheet1 de la base integrada.")
        valores = libro["Sheet1"].values
        campos = tuple(next(valores, ()))
        if (len(set(campos)) != len(campos) or not all(isinstance(c, str) and c.strip() for c in campos)
                or set(campos) & {"grupo_edad", "grupo_escolaridad"}):
            raise ValueError("La hoja contiene encabezados vacíos, duplicados o reservados.")
        faltan = set(REQUERIDOS) - set(campos)
        if faltan:
            raise ValueError("Faltan columnas: " + ", ".join(sorted(faltan)))

        filas = []
        folios = set()
        for numero, valores_fila in enumerate(valores, start=2):
            if all(valor is None for valor in valores_fila):
                continue
            fila = dict(zip(campos, valores_fila))
            identificador = fila["id"]
            folio = str(identificador).strip().casefold() if identificador is not None else ""
            if not folio or folio in folios:
                raise ValueError(f"Fila {numero}: folio vacío o duplicado.")
            folios.add(folio)
            if fila["cumple_criterios"] not in (0, 1):
                raise ValueError(f"Fila {numero}: cumple_criterios debe valer 0 o 1.")

            if fila["cumple_criterios"] == 1:
                for campo, minimo, maximo in (
                    ("sexo", 0, 1), ("edad", 18, None), ("escolaridad", 0, None),
                    *((campo, 0, None) for campo in CONTEOS),
                ):
                    valor = fila[campo]
                    if (not isinstance(valor, (int, float)) or not isfinite(valor)
                            or valor != int(valor) or valor < minimo
                            or (maximo is not None and valor > maximo)):
                        raise ValueError(f"Fila {numero}: valor inválido en {campo}.")
                for sufijo in TAREAS.values():
                    campo = f"prom_cluster_{sufijo}"
                    valor = fila[campo]
                    if (not isinstance(valor, (int, float)) or not isfinite(valor)
                            or valor < 0 or (fila[f"cluster_{sufijo}"] == 0 and valor != 0)):
                        raise ValueError(f"Fila {numero}: valor inválido en {campo}.")
            filas.append(fila)
        if not any(fila["cumple_criterios"] == 1 for fila in filas):
            raise ValueError("La base no contiene participantes elegibles.")
        return campos, filas
    finally:
        libro.close()


def guardar_maestra(destino, campos, filas, elegibles):
    """Exporta la base completa, la muestra elegible y sus descriptivos."""
    libro = Workbook()
    completa = libro.active
    completa.title = "Todos los participantes"
    muestra = libro.create_sheet("Muestra elegible")
    completa.append(campos)
    muestra.append((*campos, "grupo_edad", "grupo_escolaridad"))
    exclusion = PatternFill("solid", fgColor="F8CCCC")
    for fila in filas:
        completa.append([fila[campo] for campo in campos])
        if fila["cumple_criterios"] == 0:
            for celda in completa[completa.max_row]:
                celda.fill = exclusion
    for fila in elegibles:
        muestra.append([*(fila[campo] for campo in campos),
                        grupo_edad(fila["edad"]), grupo_escolaridad(fila["escolaridad"])])
    for hoja in (completa, muestra):
        hoja.freeze_panes = "B2"
        hoja.auto_filter.ref = hoja.dimensions
        # Escribe como texto los campos que Excel interpretaría como fórmulas.
        for fila in hoja.iter_rows():
            for celda in fila:
                if celda.data_type == "f":
                    celda.data_type = "s"

    resumen = [("Participantes", "Edad", *resumir(elegibles, "edad")),
               ("Participantes", "Escolaridad", *resumir(elegibles, "escolaridad"))]
    for tarea, sufijo in TAREAS.items():
        for campo, nombre in (("cluster", "Clústeres"), ("switching", "Switches"),
                              ("prom_cluster", "Tamaño promedio (todos)")):
            resumen.append((tarea, nombre, *resumir(elegibles, f"{campo}_{sufijo}")))
        con_cluster = [f for f in elegibles if f[f"cluster_{sufijo}"] > 0]
        resumen.append((tarea, "Tamaño promedio (con clúster)",
                        *resumir(con_cluster, f"prom_cluster_{sufijo}")))
    tabla(libro, "Descriptivos", "Muestra elegible", ("Tarea", "Medida", *ESTADISTICAS),
          resumen, GUIA)

    # Cada distribución usa el mismo denominador de la muestra elegible.
    grupos = (
        ("Sexo", lambda f: "Mujeres" if f["sexo"] == 1 else "Hombres"),
        ("Edad", lambda f: grupo_edad(f["edad"])),
        ("Escolaridad", lambda f: grupo_escolaridad(f["escolaridad"])),
    )
    distribucion = [(variable, categoria, n, 100 * n / len(elegibles))
                    for variable, clasificar in grupos
                    for categoria, n in sorted(Counter(map(clasificar, elegibles)).items())]
    tabla(libro, "Grupos", "Composición de la muestra elegible",
          ("Variable", "Categoría", "Personas", "Porcentaje"), distribucion)

    # El MMSE se cruza con la marca recibida para auditarla, sin redefinir el filtro.
    cruce = Counter((f["cumple_criterios"],
                     "Sin dato" if not isinstance(f["puntaje_mmse"], (int, float))
                     else "Menor de 24" if f["puntaje_mmse"] < 24 else "24 o más")
                    for f in filas)
    tabla(libro, "Elegibilidad y MMSE", "Comprobación de la marca de elegibilidad",
          ("Cumple criterios", "MMSE", "Personas"),
          [(marca, mmse, n) for (marca, mmse), n in sorted(cruce.items())],
          "La muestra se selecciona con cumple_criterios = 1.")
    libro.save(destino / "01_base_maestra_fluidez.xlsx")
