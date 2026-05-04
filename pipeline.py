"""
PIPELINE MAESTRO - Evaluación de Integridad Técnica en Datos de LLMs
====================================================================
Orquesta la ejecución secuencial de todos los módulos del proyecto:
  1. pipeline_ingesta.py        -> data/muestra.parquet
  2. limpieza_heuristica.py     -> data/muestra_depurada.parquet
  3. minhash_dedup.py           -> data/duplicados_encontrados.json
  4. toxicidad.py               -> data/muestra_con_toxicidad.parquet
  5. deteccion_pii.py           -> data/muestra_con_pii.parquet
  6. scorecard.py               -> scorecard_*.json

Uso:
    python pipeline.py           (ejecuta todo)
    python pipeline.py --help    (muestra opciones)

Entrada:
    data/muestra.jsonl
    toxicidad_dic.json

Salida:
    data/*.parquet
    data/duplicados_encontrados.json
    data/metadatos_ingesta.json
    scorecard_*.json
"""

import sys
import subprocess
from pathlib import Path


# ============================================================
# CONFIGURACIÓN
# ============================================================
MODULOS = [
    {
        "nombre": "Ingesta (JSONL → Parquet)",
        "script": "pipeline_ingesta.py",
        "scrum": "SCRUM-19",
        "entrada": "data/muestra.jsonl",
        "salida": "data/muestra.parquet"
    },
    {
        "nombre": "Filtros Heurísticos",
        "script": "limpieza_heuristica.py",
        "scrum": "SCRUM-21",
        "entrada": "data/muestra.parquet",
        "salida": "data/muestra_depurada.parquet"
    },
    {
        "nombre": "Deduplicación (MinHash + LSH)",
        "script": "minhash_dedup.py",
        "scrum": "SCRUM-20",
        "entrada": "data/muestra_depurada.parquet",
        "salida": "data/duplicados_encontrados.json"
    },
    {
        "nombre": "Análisis de Toxicidad",
        "script": "toxicidad.py",
        "scrum": "SCRUM-22",
        "entrada": "data/muestra_depurada.parquet",
        "salida": "data/muestra_con_toxicidad.parquet"
    },
    {
        "nombre": "Detección de PII (Regex)",
        "script": "deteccion_pii.py",
        "scrum": "SCRUM-23",
        "entrada": "data/muestra_con_toxicidad.parquet",
        "salida": "data/muestra_con_pii.parquet"
    },
    {
        "nombre": "Scorecard de Integridad",
        "script": "scorecard.py",
        "scrum": "SCRUM-24",
        "entrada": "data/duplicados_encontrados.json + "
                   "data/muestra_con_pii.parquet",
        "salida": "scorecard_*.json"
    }
]


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def verificar_entorno():
    """Comprueba que los archivos necesarios existen."""
    print("[INFO] Verificando entorno...")

    # Verificar que existe el directorio data
    Path("data").mkdir(parents=True, exist_ok=True)

    # Verificar muestra de entrada
    if not Path("data/muestra.jsonl").exists():
        print("       ADVERTENCIA: data/muestra.jsonl no encontrado.")
        print("       El pipeline de ingesta fallará si no existe.")
    else:
        print("       ✓ data/muestra.jsonl encontrado")

    # Verificar diccionario de toxicidad
    if not Path("toxicidad_dic.json").exists():
        print("       ADVERTENCIA: toxicidad_dic.json no encontrado.")
        print("       El módulo de toxicidad fallará si no existe.")
    else:
        print("       ✓ toxicidad_dic.json encontrado")

    print()


def ejecutar_modulo(modulo: dict) -> bool:
    """Ejecuta un módulo del pipeline y devuelve True si tuvo éxito."""
    print("-" * 70)
    print(f"MÓDULO: {modulo['nombre']} ({modulo['scrum']})")
    print(f"  Script  : {modulo['script']}")
    print(f"  Entrada : {modulo['entrada']}")
    print(f"  Salida  : {modulo['salida']}")
    print("-" * 70)

    resultado = subprocess.run(
        [sys.executable, modulo['script']],
        capture_output=False,
        text=True
    )

    print()
    if resultado.returncode == 0:
        print(f"[OK] {modulo['nombre']} completado exitosamente.")
    else:
        print(f"[ERROR] {modulo['nombre']} falló (código {resultado.returncode}).")
        print("        Revisa la salida anterior para diagnosticar el error.")

    return resultado.returncode == 0


def mostrar_resumen():
    """Muestra un resumen de los archivos generados."""
    print("=" * 70)
    print("ARCHIVOS GENERADOS POR EL PIPELINE")
    print("=" * 70)
    archivos = [
        ("data/muestra.parquet", "Dataset original en formato columnar"),
        ("data/metadatos_ingesta.json", "Metadatos de procedencia (SCRUM-19)"),
        ("data/muestra_depurada.parquet", "Dataset tras filtros heurísticos (SCRUM-21)"),
        ("data/duplicados_encontrados.json", "Pares duplicados detectados (SCRUM-20)"),
        ("data/muestra_con_toxicidad.parquet", "Dataset con scores de toxicidad (SCRUM-22)"),
        ("data/muestra_con_pii.parquet", "Dataset con detección de PII (SCRUM-23)"),
        ("scorecard_*.json", "Scorecard de Integridad Técnica (SCRUM-24)")
    ]
    for ruta, descripcion in archivos:
        if '*' in ruta:
            # Buscar archivos que coincidan con el patrón
            matches = list(Path('.').glob(ruta))
            if matches:
                for m in matches:
                    print(f"  ✓ {m}  ← {descripcion}")
            else:
                print(f"  ✗ {ruta}  ← {descripcion}")
        else:
            if Path(ruta).exists():
                print(f"  ✓ {ruta}  ← {descripcion}")
            else:
                print(f"  ✗ {ruta}  ← {descripcion}")
    print("=" * 70)


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def ejecutar_pipeline():
    """Ejecuta todos los módulos del pipeline en orden."""

    print("=" * 70)
    print("PIPELINE DE EVALUACIÓN DE INTEGRIDAD TÉCNICA")
    print("Proyecto: LLM Data Integrity")
    print("Institución: Colegio Mayor del Cauca")
    print("=" * 70)
    print()

    # Verificar entorno
    verificar_entorno()

    # Ejecutar módulos secuencialmente
    modulos_exitosos = 0
    modulos_fallidos = 0

    for modulo in MODULOS:
        exito = ejecutar_modulo(modulo)
        if exito:
            modulos_exitosos += 1
        else:
            modulos_fallidos += 1
            print("[INFO] Deteniendo el pipeline debido a un error.")
            print("       Corrige el problema y vuelve a ejecutar.")
            break

    # Resumen final
    print("\n" + "=" * 70)
    print("RESUMEN DE EJECUCIÓN")
    print("=" * 70)
    print(f"  Módulos completados : {modulos_exitosos}/{len(MODULOS)}")
    if modulos_fallidos > 0:
        print(f"  Módulos fallidos   : {modulos_fallidos}")
    print()

    if modulos_fallidos == 0:
        print("[INFO] Pipeline completado exitosamente.")
        mostrar_resumen()
    else:
        print("[WARN] El pipeline no se completó en su totalidad.")


# ============================================================
# PUNTO DE ENTRADA
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print(__doc__)
    else:
        ejecutar_pipeline()