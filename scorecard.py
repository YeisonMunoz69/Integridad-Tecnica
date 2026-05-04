"""
SCRUM-24: Módulo Scorecard - Consolidación de hallazgos y métricas
==================================================================
Lee los datasets generados por los módulos anteriores y consolida
las 4 métricas de integridad en un archivo JSON estructurado.

Métricas:
  MI-01: Ratio de duplicados (desde duplicados_encontrados.json)
  MI-02: % de documentos con PII (desde muestra_con_pii.parquet)
  MI-03: Score de toxicidad promedio (desde muestra_con_pii.parquet)
  MI-04: % de registros limpios (calculado desde los datos)

Uso:
    python scorecard.py

Entrada:
    data/duplicados_encontrados.json
    data/muestra_con_pii.parquet
    data/metadatos_ingesta.json (para metadatos del pipeline)

Salida:
    scorecard_{fecha}.json
"""

import json
import time
from pathlib import Path
from datetime import datetime

import pandas as pd
import pyarrow.parquet as pq


# ============================================================
# CONFIGURACIÓN
# ============================================================
RUTA_DUPLICADOS = Path("data/duplicados_encontrados.json")
RUTA_DATASET_FINAL = Path("data/muestra_con_pii.parquet")
RUTA_METADATOS = Path("data/metadatos_ingesta.json")

UMBRAL_ALERTA_DUPLICADOS = 10.0      # % máximo recomendado
UMBRAL_ALERTA_PII = 2.0              # % máximo recomendado
UMBRAL_ALERTA_TOXICIDAD = 5.0        # % máximo recomendado
UMBRAL_ALERTA_LIMPIEZA = 80.0        # % mínimo recomendado


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def cargar_json(ruta: Path) -> dict:
    """Carga un archivo JSON y devuelve su contenido."""
    with open(ruta, 'r', encoding='utf-8') as f:
        return json.load(f)


def generar_recomendaciones(metricas: dict) -> list:
    """
    Genera recomendaciones automáticas basadas en los umbrales
    definidos para cada métrica.
    """
    recomendaciones = []

    if metricas['ratio_duplicados'] > UMBRAL_ALERTA_DUPLICADOS:
        recomendaciones.append(
            f"ALTA DUPLICACIÓN: El {metricas['ratio_duplicados']:.1f}% de los "
            f"documentos son cuasi-duplicados. Se recomienda aplicar una "
            f"deduplicación más agresiva (umbral Jaccard ≥ 0.7) antes del "
            f"entrenamiento."
        )
    else:
        recomendaciones.append(
            "DUPLICACIÓN CONTROLADA: El nivel de duplicados está dentro "
            "de los límites aceptables para entrenamiento."
        )

    if metricas['pct_documentos_con_pii'] > UMBRAL_ALERTA_PII:
        recomendaciones.append(
            f"PII DETECTADA: El {metricas['pct_documentos_con_pii']:.1f}% de "
            f"los documentos contiene posibles datos personales. Se recomienda "
            f"aplicar ofuscación automática o revisión manual antes del uso."
        )
    else:
        recomendaciones.append(
            "PII CONTROLADA: La presencia de información personal está "
            "por debajo del umbral de riesgo."
        )

    if metricas['pct_documentos_toxicos'] > UMBRAL_ALERTA_TOXICIDAD:
        recomendaciones.append(
            f"TOXICIDAD ELEVADA: El {metricas['pct_documentos_toxicos']:.1f}% "
            f"de los documentos supera el umbral de toxicidad. Se recomienda "
            f"filtrar estos registros antes del entrenamiento."
        )
    else:
        recomendaciones.append(
            "TOXICIDAD CONTROLADA: El nivel de contenido tóxico está dentro "
            "de los límites aceptables."
        )

    if metricas['pct_registros_limpios'] < UMBRAL_ALERTA_LIMPIEZA:
        recomendaciones.append(
            f"BAJA CALIDAD ESTRUCTURAL: Solo el "
            f"{metricas['pct_registros_limpios']:.1f}% de los registros "
            f"superaron los filtros de calidad. Se recomienda revisar la "
            f"fuente de datos o ajustar los criterios de filtrado."
        )
    else:
        recomendaciones.append(
            "CALIDAD ESTRUCTURAL ADECUADA: El porcentaje de registros "
            "limpios supera el umbral mínimo recomendado."
        )

    return recomendaciones


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def generar_scorecard():
    """Consolida todas las métricas y genera el Scorecard JSON."""

    print("=" * 70)
    print("GENERACIÓN DE SCORECARD DE INTEGRIDAD TÉCNICA - SCRUM-24")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Cargar datos de duplicados
    # ------------------------------------------------------------------
    print("[INFO] Cargando resultados de deduplicación...")
    if RUTA_DUPLICADOS.exists():
        datos_dup = cargar_json(RUTA_DUPLICADOS)
        ratio_duplicados = datos_dup.get('porcentaje_duplicados', 0.0)
        total_duplicados = datos_dup.get('total_duplicados', 0)
        print(f"       Ratio duplicados: {ratio_duplicados:.2f}%")
    else:
        print("       ADVERTENCIA: No se encontró duplicados_encontrados.json")
        ratio_duplicados = 0.0
        total_duplicados = 0

    # ------------------------------------------------------------------
    # 2. Cargar dataset final (con PII y toxicidad)
    # ------------------------------------------------------------------
    print("[INFO] Cargando dataset con métricas de PII y toxicidad...")
    if RUTA_DATASET_FINAL.exists():
        df = pq.read_table(RUTA_DATASET_FINAL).to_pandas()
        total_docs = len(df)
        print(f"       Total documentos: {total_docs}")

        # Métrica PII
        if 'pii_detectada' in df.columns:
            docs_con_pii = df['pii_detectada'].sum()
            pct_pii = 100 * docs_con_pii / total_docs if total_docs else 0
        else:
            docs_con_pii = 0
            pct_pii = 0.0
        print(f"       Documentos con PII: {docs_con_pii} ({pct_pii:.2f}%)")

        # Métrica Toxicidad
        if 'score_toxicidad' in df.columns:
            score_promedio = df['score_toxicidad'].mean()
            docs_toxicos = (df['score_toxicidad'] > 0.5).sum()
            pct_toxicos = 100 * docs_toxicos / total_docs if total_docs else 0
        else:
            score_promedio = 0.0
            docs_toxicos = 0
            pct_toxicos = 0.0
        print(f"       Score toxicidad promedio: {score_promedio:.4f}")
        print(f"       Documentos tóxicos: {docs_toxicos} ({pct_toxicos:.2f}%)")
    else:
        print("       ADVERTENCIA: No se encontró muestra_con_pii.parquet")
        total_docs = 0
        docs_con_pii = 0
        pct_pii = 0.0
        score_promedio = 0.0
        docs_toxicos = 0
        pct_toxicos = 0.0

    # ------------------------------------------------------------------
    # 3. Calcular porcentaje de registros limpios
    # ------------------------------------------------------------------
    print("[INFO] Calculando porcentaje de registros limpios...")
    # Tomamos como referencia los metadatos de ingesta (total original)
    if RUTA_METADATOS.exists():
        metadatos = cargar_json(RUTA_METADATOS)
        total_original = metadatos.get('total_registros', total_docs)
    else:
        total_original = total_docs

    pct_registros_limpios = (
        100 * total_docs / total_original if total_original else 0
    )
    print(f"       Registros originales: {total_original}")
    print(f"       Registros tras filtros: {total_docs}")
    print(f"       % limpios: {pct_registros_limpios:.2f}%")

    # ------------------------------------------------------------------
    # 4. Construir Scorecard
    # ------------------------------------------------------------------
    scorecard = {
        "scorecard_id": datetime.now().strftime("SC-%Y%m%d-%H%M%S"),
        "fecha_generacion": datetime.now().isoformat(),
        "proyecto": "Evaluación de Integridad Técnica en Datos de Entrenamiento de LLMs",
        "institucion": "Colegio Mayor del Cauca - Ingeniería Informática",
        "sprint_actual": 6,
        "metricas": {
            "MI-01_ratio_duplicados": {
                "valor": round(ratio_duplicados, 2),
                "unidad": "%",
                "metodo": "MinHash + LSH (Jaccard ≥ 0.8)",
                "umbral_alerta": f">{UMBRAL_ALERTA_DUPLICADOS}%",
                "pares_duplicados_detectados": total_duplicados
            },
            "MI-02_pct_pii": {
                "valor": round(pct_pii, 2),
                "unidad": "%",
                "metodo": "Regex (email, teléfono, IPv4, cédula, credenciales)",
                "umbral_alerta": f">{UMBRAL_ALERTA_PII}%",
                "documentos_con_pii": int(docs_con_pii)
            },
            "MI-03_toxicidad": {
                "score_promedio": round(score_promedio, 4),
                "pct_documentos_toxicos": round(pct_toxicos, 2),
                "metodo": "Diccionario ponderado (200+ términos, normalizado por longitud)",
                "umbral_alerta": f">{UMBRAL_ALERTA_TOXICIDAD}% de docs con score > 0.5",
                "documentos_toxicos": int(docs_toxicos)
            },
            "MI-04_registros_limpios": {
                "valor": round(pct_registros_limpios, 2),
                "unidad": "%",
                "metodo": "Filtros heurísticos (HTML, longitud, completitud)",
                "umbral_alerta": f"<{UMBRAL_ALERTA_LIMPIEZA}%",
                "registros_originales": total_original,
                "registros_finales": total_docs
            }
        },
        "recomendaciones": []
    }

    # Generar recomendaciones automáticas
    scorecard["recomendaciones"] = generar_recomendaciones({
        'ratio_duplicados': ratio_duplicados,
        'pct_documentos_con_pii': pct_pii,
        'pct_documentos_toxicos': pct_toxicos,
        'pct_registros_limpios': pct_registros_limpios
    })

    # ------------------------------------------------------------------
    # 5. Guardar Scorecard
    # ------------------------------------------------------------------
    nombre_archivo = f"scorecard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    ruta_scorecard = Path(nombre_archivo)

    with open(ruta_scorecard, 'w', encoding='utf-8') as f:
        json.dump(scorecard, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # 6. Mostrar resumen en consola
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("SCORECARD DE INTEGRIDAD TÉCNICA GENERADO")
    print("=" * 70)
    print(f"Archivo: {ruta_scorecard}")
    print()
    print("MÉTRICAS:")
    print(f"  MI-01 - Ratio duplicados : {ratio_duplicados:.2f}%")
    print(f"  MI-02 - % docs con PII   : {pct_pii:.2f}%")
    print(f"  MI-03 - Score toxicidad  : {score_promedio:.4f} "
          f"({pct_toxicos:.2f}% docs tóxicos)")
    print(f"  MI-04 - % limpios        : {pct_registros_limpios:.2f}%")
    print()
    print("RECOMENDACIONES:")
    for i, rec in enumerate(scorecard["recomendaciones"], 1):
        print(f"  {i}. {rec}")

    print("=" * 70)
    print("[INFO] Scorecard generado exitosamente.")


# ============================================================
# PUNTO DE ENTRADA
# ============================================================
if __name__ == "__main__":
    generar_scorecard()