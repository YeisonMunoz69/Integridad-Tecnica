"""
SCRUM-21: Filtros Heurísticos para Mitigar Ruido HTML y Registros Incompletos
=============================================================================
Aplica tres reglas de limpieza sobre el dataset en Parquet:
  1. Ratio HTML/texto > 0.3 → descartar
  2. Longitud de texto < 100 caracteres → descartar
  3. Ausencia del campo 'texto_limpio' → descartar

Genera un nuevo archivo Parquet con los registros que superan todos los filtros
y muestra un resumen con los porcentajes de descarte por regla.

Uso:
    python limpieza_heuristica.py

Entrada:
    data/muestra.parquet

Salida:
    data/muestra_depurada.parquet
"""

import re
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


# ============================================================
# CONFIGURACIÓN
# ============================================================
RUTA_ENTRADA = Path("data/muestra.parquet")
RUTA_SALIDA = Path("data/muestra_depurada.parquet")

UMBRAL_RATIO_HTML = 0.3
LONGITUD_MINIMA_TEXTO = 100


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def calcular_ratio_html(texto: str) -> float:
    """
    Estima la proporción de caracteres que pertenecen a etiquetas HTML.
    Se basa en contar caracteres dentro de <...> frente al total.
    """
    if not isinstance(texto, str) or len(texto) == 0:
        return 0.0
    etiquetas = re.findall(r"<[^>]*>", texto)
    len_etiquetas = sum(len(t) for t in etiquetas)
    return len_etiquetas / len(texto)


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def ejecutar_limpieza():
    """Aplica los filtros heurísticos y guarda el dataset depurado."""

    print("=" * 70)
    print("FILTROS HEURÍSTICOS - SCRUM-21")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Cargar el dataset
    # ------------------------------------------------------------------
    print("[INFO] Cargando dataset desde Parquet...")
    if not RUTA_ENTRADA.exists():
        raise FileNotFoundError(f"No se encontró {RUTA_ENTRADA}")
    df = pq.read_table(RUTA_ENTRADA).to_pandas()
    total_inicial = len(df)
    print(f"       Registros cargados: {total_inicial}")

    # ------------------------------------------------------------------
    # 2. Aplicar filtros uno a uno
    # ------------------------------------------------------------------

    # -- Filtro 1: Ratio HTML -------------------------------------------------
    print("\n[INFO] Aplicando Filtro 1: Ratio HTML/texto > 0.3 ...")
    mask_html = df["texto_limpio"].apply(calcular_ratio_html) > UMBRAL_RATIO_HTML
    descartados_html = mask_html.sum()
    df_filtrado = df[~mask_html].copy()
    print(f"       Registros descartados por HTML excesivo: {descartados_html} "
          f"({100 * descartados_html / total_inicial:.2f}%)")

    # -- Filtro 2: Longitud mínima --------------------------------------------
    print("[INFO] Aplicando Filtro 2: Longitud < 100 caracteres ...")
    mask_cortos = df_filtrado["texto_limpio"].str.len() < LONGITUD_MINIMA_TEXTO
    descartados_cortos = mask_cortos.sum()
    df_filtrado = df_filtrado[~mask_cortos].copy()
    print(f"       Registros descartados por cortos: {descartados_cortos} "
          f"({100 * descartados_cortos / total_inicial:.2f}%)")

    # -- Filtro 3: Texto ausente ----------------------------------------------
    print("[INFO] Aplicando Filtro 3: Campo 'texto_limpio' vacío o nulo ...")
    mask_vacios = df_filtrado["texto_limpio"].isna() | (
        df_filtrado["texto_limpio"].str.strip() == ""
    )
    descartados_vacios = mask_vacios.sum()
    df_filtrado = df_filtrado[~mask_vacios].copy()
    print(f"       Registros descartados por texto vacío: {descartados_vacios} "
          f"({100 * descartados_vacios / total_inicial:.2f}%)")

    # ------------------------------------------------------------------
    # 3. Guardar dataset depurado
    # ------------------------------------------------------------------
    print(f"\n[INFO] Guardando dataset depurado en {RUTA_SALIDA}...")
    RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    df_filtrado.to_parquet(RUTA_SALIDA, index=False)

    # ------------------------------------------------------------------
    # 4. Mostrar tabla resumen
    # ------------------------------------------------------------------
    total_final = len(df_filtrado)
    total_descartado = total_inicial - total_final

    print("\n" + "=" * 70)
    print("RESUMEN DE FILTROS HEURÍSTICOS")
    print("=" * 70)
    print(f"{'Regla aplicada':<40} {'Descartados':>12} {'%':>8}")
    print("-" * 62)
    print(f"{'Ratio HTML/texto > 0.3':<40} {descartados_html:>12} "
          f"{100 * descartados_html / total_inicial:>7.2f}%")
    print(f"{'Longitud < 100 caracteres':<40} {descartados_cortos:>12} "
          f"{100 * descartados_cortos / total_inicial:>7.2f}%")
    print(f"{'Sin campo texto_limpio':<40} {descartados_vacios:>12} "
          f"{100 * descartados_vacios / total_inicial:>7.2f}%")
    print("-" * 62)
    print(f"{'TOTAL DESCARTADO':<40} {total_descartado:>12} "
          f"{100 * total_descartado / total_inicial:>7.2f}%")
    print(f"{'TOTAL REGISTROS LIMPIOS':<40} {total_final:>12} "
          f"{100 * total_final / total_inicial:>7.2f}%")
    print("=" * 70)
    print(f"[INFO] Dataset depurado guardado en: {RUTA_SALIDA}")


# ============================================================
# PUNTO DE ENTRADA
# ============================================================
if __name__ == "__main__":
    ejecutar_limpieza()