"""
SCRUM-23: Exploración de expresiones regulares para identificación preliminar de PII
=====================================================================================
Aplica 5 patrones regex sobre el dataset para detectar:
  1. Correos electrónicos (RFC 5322 simplificado)
  2. Teléfonos colombianos (formato +57 y local)
  3. Direcciones IPv4 (validación de octetos)
  4. Cédulas de ciudadanía colombiana (8-10 dígitos)
  5. Credenciales expuestas en URLs (user:password@)

Genera:
  - data/muestra_con_pii.parquet (dataset con columnas de detección PII)
  - Estadísticas de detección y tasa estimada de falsos positivos

Uso:
    python deteccion_pii.py

Entrada:
    data/muestra_con_toxicidad.parquet

Salida:
    data/muestra_con_pii.parquet
"""

import re
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq


# ============================================================
# CONFIGURACIÓN
# ============================================================
RUTA_ENTRADA = Path("data/muestra_con_toxicidad.parquet")
RUTA_SALIDA = Path("data/muestra_con_pii.parquet")

# ============================================================
# PATRONES REGEX (según SCRUM-23)
# ============================================================

# 1. Email (RFC 5322 simplificado, eficiente para corpus masivos)
REGEX_EMAIL = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE
)

# 2. Teléfono colombiano (+57, 57, 3XX-XXX-XXXX, 60X-XXX-XXXX)
REGEX_TELEFONO = re.compile(
    r"(?:\+57|57)?\s*(?:3[0-9]{2}|60[1-8])\s*[0-9]{3}\s*[0-9]{4}"
)

# 3. Dirección IPv4 (con validación de octetos)
REGEX_IPV4 = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
)

# 4. Cédula colombiana (8-10 dígitos con o sin separadores)
REGEX_CEDULA = re.compile(
    r"\b[1-9][0-9]{2,3}(?:\.[0-9]{3}){2}\b"
    r"|\b[1-9][0-9]{7,9}\b"
)

# 5. Credenciales en URL (http://user:pass@host/)
REGEX_CREDENCIALES_URL = re.compile(
    r"https?://[^\s:@]+:[^\s:@]+@[^\s/]+"
)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def detectar_pii(texto: str, patron: re.Pattern) -> bool:
    """Indica si un texto contiene al menos una coincidencia del patrón."""
    if not isinstance(texto, str):
        return False
    return bool(patron.search(texto))


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def ejecutar_deteccion_pii():
    """Aplica los patrones regex y consolida las detecciones."""

    print("=" * 70)
    print("DETECCIÓN DE PII POR EXPRESIONES REGULARES - SCRUM-23")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Cargar dataset
    # ------------------------------------------------------------------
    print("[INFO] Cargando dataset...")
    if not RUTA_ENTRADA.exists():
        raise FileNotFoundError(
            f"No se encontró {RUTA_ENTRADA}. "
            f"Ejecuta primero limpieza_heuristica.py y toxicidad.py"
        )
    df = pq.read_table(RUTA_ENTRADA).to_pandas()
    total_docs = len(df)
    print(f"       Documentos cargados: {total_docs}")

    # ------------------------------------------------------------------
    # 2. Aplicar cada patrón y agregar columnas
    # ------------------------------------------------------------------
    print("[INFO] Aplicando patrones regex...")

    patrones = {
        'email': REGEX_EMAIL,
        'telefono': REGEX_TELEFONO,
        'ipv4': REGEX_IPV4,
        'cedula': REGEX_CEDULA,
        'credenciales_url': REGEX_CREDENCIALES_URL
    }

    resultados = {}
    for categoria, patron in patrones.items():
        columna = f'pii_{categoria}'
        df[columna] = df['texto_limpio'].apply(
            lambda t: detectar_pii(t, patron)
        )
        resultados[categoria] = df[columna].sum()

    # Columna resumen: ¿tiene al menos un tipo de PII?
    columnas_pii = [f'pii_{c}' for c in patrones.keys()]
    df['pii_detectada'] = df[columnas_pii].any(axis=1)
    total_con_pii = df['pii_detectada'].sum()

    # ------------------------------------------------------------------
    # 3. Guardar dataset
    # ------------------------------------------------------------------
    print(f"[INFO] Guardando dataset con detección PII en {RUTA_SALIDA}...")
    df.to_parquet(RUTA_SALIDA, index=False)

    # ------------------------------------------------------------------
    # 4. Mostrar estadísticas
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("RESULTADOS DE DETECCIÓN DE PII")
    print("=" * 70)
    print(f"{'Categoría':<25} {'Detecciones':>12} {'% del total':>12}")
    print("-" * 55)
    for categoria, cantidad in resultados.items():
        pct = 100 * cantidad / total_docs if total_docs else 0
        print(f"{categoria:<25} {cantidad:>12} {pct:>11.2f}%")
    print("-" * 55)
    print(f"{'TOTAL DOCUMENTOS CON PII':<25} {total_con_pii:>12} "
          f"{100 * total_con_pii / total_docs:>11.2f}%")

    # ------------------------------------------------------------------
    # 5. Estimación de falsos positivos (valores documentados en SCRUM-23)
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("ESTIMACIÓN DE FALSOS POSITIVOS (según análisis documentado)")
    print("=" * 70)
    fps = {
        'email': '< 3%',
        'telefono': '~18%',
        'ipv4': '~42%',
        'cedula': '> 65%',
        'credenciales_url': '~12%'
    }
    for categoria, tasa in fps.items():
        print(f"  {categoria:<25} {tasa}")

    print("=" * 70)
    print("[INFO] Detección de PII completada.")


# ============================================================
# PUNTO DE ENTRADA
# ============================================================
if __name__ == "__main__":
    ejecutar_deteccion_pii()