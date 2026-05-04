"""
SCRUM-19: Pipeline de Ingesta de Archivos Estáticos JSONL/Parquet
=================================================================
Lee una muestra JSONL (simulando Common Crawl), aplica limpieza
básica de HTML, la convierte a formato columnar Parquet y genera
un archivo de metadatos con hash SHA256 de la muestra original.

Uso:
    python pipeline_ingesta.py

Entrada:
    data/muestra.jsonl

Salidas:
    data/muestra.parquet           (dataset en formato columnar)
    data/metadatos_ingesta.json    (metadatos de procedencia)
"""

import json
import os
import hashlib
import time
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import re


# ============================================================
# CONFIGURACIÓN
# ============================================================
RUTA_ENTRADA = Path("data/muestra.jsonl")
RUTA_PARQUET = Path("data/muestra.parquet")
RUTA_METADATOS = Path("data/metadatos_ingesta.json")
CHUNK_SIZE = 100  # Número de filas por lote (para la demo)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def limpiar_html(texto: str) -> str:
    """
    Elimina etiquetas HTML residuales del texto.
    Para el MVP se usa una regex simple. En producción se podría
    usar BeautifulSoup, pero añadiría dependencias pesadas.
    """
    if not isinstance(texto, str):
        return ""
    # Eliminar etiquetas HTML
    limpio = re.sub(r"<[^>]*>", " ", texto)
    # Colapsar espacios múltiples
    limpio = re.sub(r"\s+", " ", limpio)
    return limpio.strip()


def calcular_hash_sha256(ruta_archivo: Path) -> str:
    """Calcula el hash SHA256 de un archivo sin cargarlo entero en RAM."""
    sha256 = hashlib.sha256()
    with open(ruta_archivo, "rb") as f:
        while True:
            bloque = f.read(8192)
            if not bloque:
                break
            sha256.update(bloque)
    return sha256.hexdigest()


def extraer_metadatos(ruta_entrada: Path) -> dict:
    """Genera los metadatos de procedencia de la muestra."""
    stat = ruta_entrada.stat()
    return {
        "archivo_origen": str(ruta_entrada.absolute()),
        "fecha_procesamiento": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tamano_bytes": stat.st_size,
        "tamano_mb": round(stat.st_size / (1024 * 1024), 2),
        "hash_sha256": calcular_hash_sha256(ruta_entrada)
    }


# ============================================================
# FUNCIÓN PRINCIPAL DE INGESTA
# ============================================================

def ejecutar_ingesta():
    """Orquesta la lectura, limpieza y escritura del pipeline de ingesta."""
    
    print("=" * 70)
    print("PIPELINE DE INGESTA - SCRUM-19")
    print("=" * 70)
    
    # ------------------------------------------------------------------
    # 1. Cálculo de metadatos de la muestra
    # ------------------------------------------------------------------
    print("[INFO] Calculando metadatos de la muestra...")
    if not RUTA_ENTRADA.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de entrada: {RUTA_ENTRADA}"
        )
    metadatos = extraer_metadatos(RUTA_ENTRADA)
    print(f"       Archivo        : {metadatos['archivo_origen']}")
    print(f"       Tamaño         : {metadatos['tamano_mb']} MB")
    print(f"       SHA256         : {metadatos['hash_sha256'][:16]}...")
    print()

    # ------------------------------------------------------------------
    # 2. Lectura y procesamiento por chunks
    # ------------------------------------------------------------------
    print(f"[INFO] Iniciando lectura por chunks (tamaño={CHUNK_SIZE})...")

    # PyArrow no dispone de un lector JSONL con chunks tan simple como
    # pandas.read_json(chunksize=...). Usaremos pandas para la lectura
    # por chunks y luego convertiremos cada chunk a tabla Arrow.
    lector = pd.read_json(
        RUTA_ENTRADA,
        lines=True,
        chunksize=CHUNK_SIZE
    )

    total_registros = 0
    primer_chunk = True

    for i, chunk in enumerate(lector, start=1):
        num_filas = len(chunk)
        total_registros += num_filas
        print(f"[INFO] Procesando chunk {i:02d} ({num_filas} registros)...", end=" ")

        # --------------------------------------------------------------
        # 2.1 Limpieza de HTML en el campo 'texto'
        # --------------------------------------------------------------
        if "texto" in chunk.columns:
            chunk["texto_limpio"] = chunk["texto"].apply(limpiar_html)
        else:
            print("X - Columna 'texto' no encontrada. Se omite limpieza.")
            chunk["texto_limpio"] = ""

        # --------------------------------------------------------------
        # 2.2 Seleccionar columnas para el Parquet
        # --------------------------------------------------------------
        columnas_finales = ["url", "texto", "texto_limpio"]
        chunk_export = chunk[columnas_finales].copy()

        # --------------------------------------------------------------
        # 2.3 Escribir a Parquet (append mode tras el primer chunk)
        # --------------------------------------------------------------
        tabla_arrow = pa.Table.from_pandas(chunk_export)
        if primer_chunk:
            pq.write_table(tabla_arrow, RUTA_PARQUET)
            primer_chunk = False
        else:
            # Leer tabla existente, concatenar y reescribir
            tabla_existente = pq.read_table(RUTA_PARQUET)
            tabla_combinada = pa.concat_tables([tabla_existente, tabla_arrow])
            pq.write_table(tabla_combinada, RUTA_PARQUET)

        print("OK")

    print(f"\n[INFO] Total registros procesados: {total_registros}")
    print(f"[INFO] Archivo Parquet generado: {RUTA_PARQUET}")

    # ------------------------------------------------------------------
    # 3. Validación de schema del Parquet resultante
    # ------------------------------------------------------------------
    print("\n[INFO] Validando schema del archivo Parquet...")
    esquema = pq.read_schema(RUTA_PARQUET)
    print(f"       Columnas: {list(esquema.names)}")
    print(f"       Tipos   : {dict(zip(esquema.names, esquema.types))}")
    print("       Schema validado correctamente.")

    # ------------------------------------------------------------------
    # 4. Guardar metadatos en JSON
    # ------------------------------------------------------------------
    print(f"\n[INFO] Guardando metadatos en {RUTA_METADATOS}...")
    metadatos["total_registros"] = total_registros
    metadatos["columnas"] = list(esquema.names)
    with open(RUTA_METADATOS, "w", encoding="utf-8") as f:
        json.dump(metadatos, f, indent=2, ensure_ascii=False)
    print("       Metadatos guardados.")

    # ------------------------------------------------------------------
    # 5. Resumen final
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("INGESTA COMPLETADA EXITOSAMENTE")
    print("=" * 70)
    print(f"Archivo de entrada : {RUTA_ENTRADA}")
    print(f"Archivo de salida  : {RUTA_PARQUET}")
    print(f"Metadatos          : {RUTA_METADATOS}")
    print(f"Registros          : {total_registros}")
    print(f"Tamaño Parquet     : {round(RUTA_PARQUET.stat().st_size / 1024, 2)} KB")


# ============================================================
# PUNTO DE ENTRADA
# ============================================================
if __name__ == "__main__":
    ejecutar_ingesta()