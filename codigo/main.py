"""Ejecuta el análisis final de fluidez verbal desde el Excel integrado."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from base_final import TAREAS, guardar_maestra, leer_integrada
from resultados_finales import guardar_resultados
from graficos_conteo import generar_graficos_conteo
from sintesis_graficos import generar_sintesis


RAIZ = Path(__file__).resolve().parents[1]


def main():
    """Valida la entrada, genera las salidas y publica una corrida completa."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=RAIZ / "datos/bbdd_handroll_merge 2.xlsx")
    parser.add_argument("--salida", type=Path, default=RAIZ / "resultados",
                        help="Carpeta nueva donde se guardan los Excel y PDF.")
    opciones = parser.parse_args()
    salida = opciones.salida.resolve()

    try:
        # Cada corrida usa una carpeta nueva para preservar resultados anteriores.
        if salida.exists():
            raise ValueError(f"La carpeta ya existe: {salida}. Indica otra con --salida.")
        campos, filas = leer_integrada(opciones.entrada)
        elegibles = [fila for fila in filas if fila["cumple_criterios"] == 1]
        salida.parent.mkdir(parents=True, exist_ok=True)

        # Se publican los archivos juntos una vez que todas las etapas terminan.
        with TemporaryDirectory(dir=salida.parent, prefix=".run-") as temporal:
            corrida = Path(temporal) / "out"
            corrida.mkdir()
            guardar_maestra(corrida, campos, filas, elegibles)
            guardar_resultados(corrida, elegibles)
            for tarea in TAREAS:
                generar_graficos_conteo(tarea, corrida)
            generar_sintesis(destino=corrida)
            if salida.exists():
                raise ValueError(f"La carpeta de salida ya existe: {salida}")
            corrida.rename(salida)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Error: {error}\n")

    print(f"Participantes: {len(filas)} | Elegibles: {len(elegibles)}")
    print(f"Resultados: {salida}")


if __name__ == "__main__":
    main()
