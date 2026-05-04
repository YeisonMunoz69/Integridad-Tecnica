"""
SCRUM-22: Sustitución diagnóstica de toxicidad mediante diccionario ponderado
=============================================================================
Carga el dataset depurado, aplica un diccionario de toxicidad (JSON) con
términos ponderados (0-1) y calcula un score normalizado por longitud.

Genera:
  - data/muestra_con_toxicidad.parquet (dataset con columna 'score_toxicidad')
  - Estadísticas de distribución en consola

Uso:
    python toxicidad.py

Entrada:
    data/muestra_depurada.parquet
    toxicidad_dic.json

Salida:
    data/muestra_con_toxicidad.parquet
"""

import json
import re
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import numpy as np


# ============================================================
# CONFIGURACIÓN
# ============================================================
RUTA_ENTRADA = Path("data/muestra_depurada.parquet")
RUTA_DICCIONARIO = Path("toxicidad_dic.json")
RUTA_SALIDA = Path("data/muestra_con_toxicidad.parquet")

UMBRAL_TOXICIDAD = 0.5  # Por encima de este valor se considera tóxico


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def cargar_diccionario(ruta: Path) -> dict:
    """Carga el diccionario de toxicidad desde JSON."""
    with open(ruta, 'r', encoding='utf-8') as f:
        return json.load(f)


def tokenizar(texto: str) -> list:
    """
    Tokenización simple: minúsculas, eliminar puntuación, dividir por espacios.
    Alternativa ligera a spaCy para el MVP.
    """
    if not isinstance(texto, str):
        return []
    texto = texto.lower()
    # Eliminar puntuación y caracteres especiales, conservando letras y números
    texto = re.sub(r'[^a-záéíóúüñ0-9\s]', '', texto)
    return texto.split()


def calcular_score_toxicidad(texto: str, diccionario: dict) -> float:
    """
    Calcula el score de toxicidad como la suma de pesos de los términos
    del diccionario encontrados, dividida por el número total de tokens.
    """
    tokens = tokenizar(texto)
    if not tokens:
        return 0.0
    suma_pesos = sum(diccionario.get(token, 0.0) for token in tokens)
    return round(suma_pesos / len(tokens), 6)


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def ejecutar_analisis_toxicidad():
    """Orquesta la carga, análisis y guardado de resultados de toxicidad."""

    print("=" * 70)
    print("ANÁLISIS DE TOXICIDAD (DICCIONARIO PONDERADO) - SCRUM-22")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Cargar dataset y diccionario
    # ------------------------------------------------------------------
    print("[INFO] Cargando dataset depurado...")
    if not RUTA_ENTRADA.exists():
        raise FileNotFoundError(
            f"No se encontró {RUTA_ENTRADA}. Ejecuta primero limpieza_heuristica.py"
        )
    df = pq.read_table(RUTA_ENTRADA).to_pandas()
    total_docs = len(df)
    print(f"       Documentos cargados: {total_docs}")

    print(f"[INFO] Cargando diccionario de toxicidad desde {RUTA_DICCIONARIO}...")
    if not RUTA_DICCIONARIO.exists():
        raise FileNotFoundError(
            f"No se encontró {RUTA_DICCIONARIO}. Asegúrate de tener el archivo JSON."
        )
    diccionario = cargar_diccionario(RUTA_DICCIONARIO)
    print(f"       Términos en el diccionario: {len(diccionario)}")

    # ------------------------------------------------------------------
    # 2. Calcular score de toxicidad para cada documento
    # ------------------------------------------------------------------
    print("[INFO] Calculando scores de toxicidad...")
    df['score_toxicidad'] = df['texto_limpio'].apply(
        lambda texto: calcular_score_toxicidad(texto, diccionario)
    )

    # ------------------------------------------------------------------
    # 3. Guardar dataset con la nueva columna
    # ------------------------------------------------------------------
    print(f"[INFO] Guardando dataset con scores en {RUTA_SALIDA}...")
    df.to_parquet(RUTA_SALIDA, index=False)

    # ------------------------------------------------------------------
    # 4. Estadísticas de distribución
    # ------------------------------------------------------------------
    scores = df['score_toxicidad']
    print("\n" + "=" * 70)
    print("DISTRIBUCIÓN DE SCORES DE TOXICIDAD")
    print("=" * 70)
    print(f"  Mínimo      : {scores.min():.4f}")
    print(f"  Máximo      : {scores.max():.4f}")
    print(f"  Media       : {scores.mean():.4f}")
    print(f"  Mediana     : {scores.median():.4f}")
    print(f"  Desv. Est.  : {scores.std():.4f}")
    print(f"  Percentil 90: {scores.quantile(0.90):.4f}")
    print(f"  Percentil 95: {scores.quantile(0.95):.4f}")

    # Documentos por encima del umbral
    docs_toxicos = (scores > UMBRAL_TOXICIDAD).sum()
    print(f"\n  Documentos con score > {UMBRAL_TOXICIDAD}: {docs_toxicos} "
          f"({100 * docs_toxicos / total_docs:.2f}%)")

    # ------------------------------------------------------------------
    # 5. Ejemplos de documentos con mayor toxicidad
    # ------------------------------------------------------------------
    if docs_toxicos > 0:
        print(f"\n  Top-5 documentos más tóxicos:")
        top_toxicos = df.nlargest(5, 'score_toxicidad')
        for i, (idx, row) in enumerate(top_toxicos.iterrows(), 1):
            texto_corto = row['texto_limpio'][:100] + '...' if len(row['texto_limpio']) > 100 else row['texto_limpio']
            print(f"    {i}. Score: {row['score_toxicidad']:.4f} | {texto_corto}")

    print("=" * 70)
    print(f"[INFO] Resultado guardado en {RUTA_SALIDA}")


# ============================================================
# PUNTO DE ENTRADA
# ============================================================
if __name__ == "__main__":
    ejecutar_analisis_toxicidad()