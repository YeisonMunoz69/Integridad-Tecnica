"""
SCRUM-20: Implementación parcial MinHash para evaluación de redundancias
========================================================================
Aplica deduplicación difusa sobre el dataset depurado (Parquet) usando:
  - Shingling de caracteres (n=5)
  - Firmas MinHash (128 funciones hash)
  - Locality-Sensitive Hashing (LSH) con umbral Jaccard >= 0.8

Detecta pares de documentos cuasi-duplicados y genera:
  - Lista de pares duplicados (duplicados_encontrados.json)
  - Métricas de rendimiento (tiempo, RAM) en consola

Uso:
    python minhash_dedup.py

Entrada:
    data/muestra_depurada.parquet

Salida:
    data/duplicados_encontrados.json
"""

import json
import time
import os
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
from datasketch import MinHash, MinHashLSH

# ============================================================
# CONFIGURACIÓN
# ============================================================
RUTA_ENTRADA = Path("data/muestra_depurada.parquet")
RUTA_DUPLICADOS = Path("data/duplicados_encontrados.json")

# Parámetros de MinHash y LSH
N_GRAMAS = 5                # Tamaño de los shingles (caracteres)
NUM_PERM = 128              # Número de funciones hash (firma MinHash)
UMBRAL_JACCARD = 0.8        # Umbral de similitud para considerar duplicado
BANDAS = 16                 # Número de bandas para LSH (ajusta la sensibilidad)
FILAS_POR_BANDA = NUM_PERM // BANDAS  # Debe ser entero (128/16 = 8)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def generar_shingles(texto: str, n: int = N_GRAMAS) -> set:
    """
    Convierte un texto en un conjunto de n-gramas de caracteres.
    Se normaliza a minúsculas y se eliminan espacios múltiples.
    """
    if not isinstance(texto, str):
        return set()
    texto = texto.lower()
    # Solo caracteres alfanuméricos y espacios para reducir ruido
    texto = ''.join(c for c in texto if c.isalnum() or c.isspace())
    texto = ' '.join(texto.split())  # colapsar espacios
    if len(texto) < n:
        return {texto}  # documento muy corto: un solo shingle
    return {texto[i:i+n] for i in range(len(texto) - n + 1)}


def firma_minhash(shingles: set) -> MinHash:
    """Crea una firma MinHash a partir de un conjunto de shingles."""
    m = MinHash(num_perm=NUM_PERM)
    for shingle in shingles:
        m.update(shingle.encode('utf-8'))
    return m


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def ejecutar_deduplicacion():
    """Ejecuta el pipeline de deduplicación difusa."""
    print("=" * 70)
    print("DEDUPLICACIÓN DIFUSA (MinHash + LSH) - SCRUM-20")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Cargar dataset depurado
    # ------------------------------------------------------------------
    print("[INFO] Cargando dataset depurado...")
    if not RUTA_ENTRADA.exists():
        raise FileNotFoundError(
            f"No se encontró {RUTA_ENTRADA}. Ejecuta primero limpieza_heuristica.py"
        )
    df = pq.read_table(RUTA_ENTRADA).to_pandas()
    total_docs = len(df)
    print(f"       Documentos cargados: {total_docs}")

    # ------------------------------------------------------------------
    # 2. Generar firmas MinHash e indexar en LSH
    # ------------------------------------------------------------------
    print(f"[INFO] Generando firmas MinHash ({NUM_PERM} permutaciones, "
          f"{N_GRAMAS}-gramas)...")
    inicio = time.time()

    # Crear índice LSH con umbral definido por bandas y filas
    lsh = MinHashLSH(
        threshold=UMBRAL_JACCARD,
        num_perm=NUM_PERM,
        params=(BANDAS, FILAS_POR_BANDA)
    )

    firmas = {}          # id_documento -> objeto MinHash
    ids_documentos = []  # para conservar el orden

    for idx, row in df.iterrows():
        doc_id = idx  # usamos el índice del DataFrame como ID
        texto = row.get('texto_limpio', '')
        shingles = generar_shingles(texto)
        m = firma_minhash(shingles)
        firmas[doc_id] = m
        lsh.insert(doc_id, m)
        ids_documentos.append(doc_id)

    tiempo_firmas = time.time() - inicio
    print(f"       Firmas generadas en {tiempo_firmas:.2f} segundos")
    print(f"       Índice LSH construido con {BANDAS} bandas x "
          f"{FILAS_POR_BANDA} filas")

    # ------------------------------------------------------------------
    # 3. Consultar pares candidatos y filtrar por Jaccard real
    # ------------------------------------------------------------------
    print(f"[INFO] Buscando pares candidatos (umbral Jaccard >= "
          f"{UMBRAL_JACCARD})...")
    duplicados = []
    revisados = set()

    for doc_id in ids_documentos:
        candidatos = lsh.query(firmas[doc_id])
        for candidato in candidatos:
            if candidato <= doc_id:
                continue  # evitar comparar dos veces y auto-comparaciones
            par = (doc_id, candidato)
            if par in revisados:
                continue
            revisados.add(par)

            jaccard = firmas[doc_id].jaccard(firmas[candidato])
            if jaccard >= UMBRAL_JACCARD:
                duplicados.append({
                    "doc_a": int(doc_id),
                    "doc_b": int(candidato),
                    "jaccard": round(jaccard, 4)
                })

    tiempo_consulta = time.time() - inicio - tiempo_firmas
    print(f"       Pares duplicados encontrados: {len(duplicados)}")
    print(f"       Tiempo de consulta LSH: {tiempo_consulta:.2f} segundos")

    # ------------------------------------------------------------------
    # 4. Guardar resultados en JSON
    # ------------------------------------------------------------------
    resultado = {
        "parametros": {
            "n_gramas": N_GRAMAS,
            "num_perm": NUM_PERM,
            "umbral_jaccard": UMBRAL_JACCARD,
            "bandas": BANDAS,
            "filas_por_banda": FILAS_POR_BANDA
        },
        "total_documentos": total_docs,
        "total_duplicados": len(duplicados),
        "porcentaje_duplicados": round(100 * len(duplicados) / total_docs, 2),
        "duplicados": duplicados
    }

    with open(RUTA_DUPLICADOS, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # 5. Mostrar resumen
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("RESULTADOS DE DEDUPLICACIÓN")
    print("=" * 70)
    print(f"Documentos analizados        : {total_docs}")
    print(f"Pares duplicados detectados  : {len(duplicados)}")
    print(f"Porcentaje de duplicados     : "
          f"{100 * len(duplicados) / total_docs:.2f}%")
    print(f"Tiempo total                 : {time.time() - inicio:.2f} s")
    print(f"Resultados guardados en      : {RUTA_DUPLICADOS}")

    # Mostrar algunos ejemplos de duplicados
    if duplicados:
        print("\nEjemplos de pares duplicados:")
        for d in duplicados[:5]:
            print(f"  Doc {d['doc_a']} <-> Doc {d['doc_b']} "
                  f"(Jaccard: {d['jaccard']:.3f})")

    print("=" * 70)


# ============================================================
# PUNTO DE ENTRADA
# ============================================================
if __name__ == "__main__":
    ejecutar_deduplicacion()