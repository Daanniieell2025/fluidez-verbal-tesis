"""Genera los Excel de auditoría, descriptivos y datos para modelar."""

from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


GUIA = ("Válidos indica cuántos registros aportaron un dato. Ceros cuenta valores registrados como 0. "
        "Q1 y Q3 son los percentiles 25 y 75. Entre ambos se sitúa el 50 % central de los datos.")


def tabla(libro, nombre, titulo, encabezados, filas, guia=None):
    hoja = libro.create_sheet(nombre)
    ultima = len(encabezados)
    hoja.sheet_view.showGridLines = False
    hoja.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ultima)
    hoja["A1"] = titulo
    hoja["A1"].font = Font(size=16, bold=True, color="17324D")
    hoja.row_dimensions[1].height = 28
    hoja.append(encabezados)
    for celda in hoja[2]:
        celda.fill = PatternFill("solid", fgColor="17324D")
        celda.font = Font(color="FFFFFF", bold=True)
    colores = {"P": "EBF3F8", "R": "FAEFE7", "Supermercado": "EAF4EF"}
    for fila in filas:
        hoja.append(fila)
        color = colores.get(fila[0], "F0F5F8" if hoja.max_row % 2 else "FFFFFF")
        for celda in hoja[hoja.max_row]:
            celda.fill = PatternFill("solid", fgColor=color)
            if isinstance(celda.value, float):
                celda.number_format = "0.00"
            elif isinstance(celda.value, str) and celda.data_type == "f":
                celda.data_type = "s"
    hoja.auto_filter.ref = f"A2:{get_column_letter(ultima)}{hoja.max_row}"
    hoja.freeze_panes = "B3"
    for i, celdas in enumerate(hoja.iter_cols(min_row=2), 1):
        ancho = max(len(str(c.value)) if c.value is not None and c.data_type != "n" else 8 for c in celdas)
        hoja.column_dimensions[get_column_letter(i)].width = min(80, max(11, ancho + 4))
        if ancho > 76:
            for celda in celdas:
                if isinstance(celda.value, str) and len(celda.value) > 76:
                    celda.alignment = Alignment(wrap_text=True)
                    hoja.row_dimensions[celda.row].height = 32
    if guia:
        fila = hoja.max_row + 2
        hoja.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=ultima)
        nota = hoja.cell(fila, 1, "Cómo leer esta tabla\n" + guia)
        nota.fill = PatternFill("solid", fgColor="EBF3F8")
        nota.alignment = Alignment(wrap_text=True, vertical="center")
        hoja.row_dimensions[fila].height = 95
