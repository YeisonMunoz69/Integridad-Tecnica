"""
Generador de reporte HTML para el pipeline de integridad tecnica.
Lee outputs existentes y construye un informe en una pagina.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from datetime import datetime

import pandas as pd
import pyarrow.parquet as pq


DATA_DIR = Path("data")
SCORECARD_GLOB = "scorecard_*.json"
SALIDA_DIR = Path("reportes")

RUTA_METADATOS = DATA_DIR / "metadatos_ingesta.json"
RUTA_DUPLICADOS = DATA_DIR / "duplicados_encontrados.json"
RUTA_DATASET_FINAL = DATA_DIR / "muestra_con_pii.parquet"


def leer_json(ruta: Path) -> dict | None:
    if not ruta.exists():
        return None
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def obtener_ultimo_scorecard() -> Path | None:
    candidatos = sorted(Path(".").glob(SCORECARD_GLOB))
    if not candidatos:
        return None
    return candidatos[-1]


def formatear_pct(valor: float | None) -> str:
    if valor is None:
        return "N/A"
    return f"{valor:.2f}%"


def formatear_float(valor: float | None, decimales: int = 4) -> str:
    if valor is None:
        return "N/A"
    return f"{valor:.{decimales}f}"


def extraer_metricas_scorecard(scorecard: dict | None) -> dict:
    if not scorecard:
        return {
            "ratio_duplicados": None,
            "pct_pii": None,
            "score_toxicidad_promedio": None,
            "pct_toxicos": None,
            "pct_limpios": None,
            "recomendaciones": [],
        }

    metricas = scorecard.get("metricas", {})
    return {
        "ratio_duplicados": metricas.get("MI-01_ratio_duplicados", {}).get("valor"),
        "pct_pii": metricas.get("MI-02_pct_pii", {}).get("valor"),
        "score_toxicidad_promedio": metricas.get("MI-03_toxicidad", {}).get("score_promedio"),
        "pct_toxicos": metricas.get("MI-03_toxicidad", {}).get("pct_documentos_toxicos"),
        "pct_limpios": metricas.get("MI-04_registros_limpios", {}).get("valor"),
        "recomendaciones": scorecard.get("recomendaciones", []),
    }


def cargar_stats_dataset() -> dict:
    if not RUTA_DATASET_FINAL.exists():
        return {
            "total_docs": None,
            "docs_con_pii": None,
            "pct_pii": None,
            "score_toxicidad_promedio": None,
            "pct_toxicos": None,
        }

    df = pq.read_table(RUTA_DATASET_FINAL).to_pandas()
    total_docs = len(df)

    if "pii_detectada" in df.columns:
        docs_con_pii = int(df["pii_detectada"].sum())
        pct_pii = 100 * docs_con_pii / total_docs if total_docs else 0
    else:
        docs_con_pii = None
        pct_pii = None

    if "score_toxicidad" in df.columns:
        score_prom = float(df["score_toxicidad"].mean())
        docs_tox = int((df["score_toxicidad"] > 0.5).sum())
        pct_tox = 100 * docs_tox / total_docs if total_docs else 0
    else:
        score_prom = None
        pct_tox = None

    return {
        "total_docs": total_docs,
        "docs_con_pii": docs_con_pii,
        "pct_pii": pct_pii,
        "score_toxicidad_promedio": score_prom,
        "pct_toxicos": pct_tox,
    }


def construir_html(contexto: dict) -> str:
    titulo = "Reporte de Integridad Tecnica"
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    resumen = contexto["resumen"]
    metadatos = contexto["metadatos"]
    duplicados = contexto["duplicados"]
    metricas = contexto["metricas"]

    recomendaciones_html = "".join(
        f"<li>{rec}</li>" for rec in metricas["recomendaciones"]
    ) or "<li>No hay recomendaciones disponibles.</li>"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{titulo}</title>
  <style>
    :root {{
      --ink: #0b1020;
      --muted: #42526e;
      --accent: #0b3b5b;
      --accent-2: #d97706;
      --accent-3: #0f766e;
      --bg: #f4f6fb;
      --card: #ffffff;
      --border: #d9e2ef;
      --shadow: 0 18px 40px rgba(10, 24, 40, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Garamond", "Georgia", "Times New Roman", serif;
      color: var(--ink);
      background: radial-gradient(circle at top, #e8edf7 0%, var(--bg) 45%, #ffffff 100%);
    }}
    .hero {{
      padding: 56px 6vw 36px;
      border-bottom: 4px solid var(--accent-2);
      background: linear-gradient(115deg, #0b3b5b 0%, #0b1020 65%);
      color: #fff;
      position: relative;
      overflow: hidden;
    }}
    .hero::after {{
      content: "";
      position: absolute;
      top: -120px;
      right: -120px;
      width: 320px;
      height: 320px;
      background: radial-gradient(circle, rgba(217,119,6,0.25), transparent 70%);
      animation: float 10s ease-in-out infinite;
    }}
    .hero h1 {{
      margin: 0 0 10px;
      font-size: 36px;
      letter-spacing: 0.8px;
    }}
    .hero p {{
      margin: 0;
      font-size: 15px;
      opacity: 0.9;
    }}
    .hero-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.12);
      border: 1px solid rgba(255, 255, 255, 0.2);
      font-size: 12px;
      letter-spacing: 0.6px;
      text-transform: uppercase;
    }}
    main {{
      padding: 28px 6vw 64px;
      max-width: 1200px;
      margin: 0 auto;
    }}
    .section-title {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }}
    .grid {{
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      margin: 18px 0 28px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      padding: 18px 20px;
      border-radius: 14px;
      box-shadow: var(--shadow);
      position: relative;
      overflow: hidden;
    }}
    .card::after {{
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(120deg, rgba(15,118,110,0.05), transparent 60%);
      opacity: 0;
      transition: opacity 0.4s ease;
    }}
    .card:hover::after {{
      opacity: 1;
    }}
    .card h3 {{
      margin: 0 0 6px;
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--muted);
    }}
    .card .value {{
      font-size: 24px;
      font-weight: 700;
    }}
    .card .subvalue {{
      font-size: 13px;
      color: var(--muted);
    }}
    section {{
      margin: 28px 0;
      animation: fadeUp 0.8s ease both;
    }}
    section h2 {{
      font-size: 22px;
      margin-bottom: 10px;
      color: var(--accent);
    }}
    .two-col {{
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 20px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--card);
      border-radius: 12px;
      overflow: hidden;
      border: 1px solid var(--border);
    }}
    th, td {{
      padding: 12px 14px;
      text-align: left;
      border-bottom: 1px solid var(--border);
      font-size: 14px;
    }}
    th {{
      background: #f1f5f9;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.6px;
      font-size: 12px;
    }}
    .tag {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      background: #e6f0f7;
      color: #0b3b5b;
      font-size: 12px;
      font-weight: 600;
    }}
    .bar {{
      height: 10px;
      border-radius: 999px;
      background: #e1e7f0;
      overflow: hidden;
    }}
    .bar span {{
      display: block;
      height: 100%;
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
    }}
    details {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px 16px;
      box-shadow: var(--shadow);
    }}
    details + details {{
      margin-top: 12px;
    }}
    summary {{
      cursor: pointer;
      font-weight: 700;
      color: var(--accent);
      list-style: none;
    }}
    summary::-webkit-details-marker {{
      display: none;
    }}
    summary::after {{
      content: "+";
      float: right;
      color: var(--accent-2);
    }}
    details[open] summary::after {{
      content: "-";
    }}
    footer {{
      margin-top: 40px;
      font-size: 12px;
      color: var(--muted);
    }}
    ul {{
      margin: 10px 0 0 20px;
    }}
    .muted {{
      color: var(--muted);
      font-size: 14px;
    }}
    .callout {{
      background: linear-gradient(120deg, rgba(11,59,91,0.08), rgba(217,119,6,0.08));
      padding: 16px 18px;
      border-radius: 12px;
      border: 1px solid rgba(11,59,91,0.2);
    }}
    @keyframes fadeUp {{
      from {{ opacity: 0; transform: translateY(16px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes float {{
      0%, 100% {{ transform: translateY(0); }}
      50% {{ transform: translateY(18px); }}
    }}
    @media (max-width: 720px) {{
      .hero h1 {{ font-size: 26px; }}
      .two-col {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header class="hero">
    <h1>{titulo}</h1>
    <p>Pipeline de evaluacion para datos de entrenamiento de LLMs</p>
    <div class="hero-meta">
      <span class="pill">Generado: {fecha}</span>
      <span class="pill">Scorecard: {contexto["scorecard_path"]}</span>
      <span class="pill">Version del informe: 1.1</span>
    </div>
  </header>
  <main>
    <section>
      <div class="section-title">
        <h2>Resumen ejecutivo</h2>
        <span class="tag">Lectura rapida</span>
      </div>
      <div class="two-col">
        <div>
          <p>{resumen}</p>
          <div class="callout">
            <strong>Lectura en una frase:</strong> el pipeline identifica duplicacion,
            PII, toxicidad y calidad estructural antes del entrenamiento, con un
            nivel de detalle suficiente para tomar decisiones rapidas.
          </div>
        </div>
        <div class="card">
          <h3>Contexto operativo</h3>
          <p class="muted">Archivo analizado: {metadatos.get("archivo_origen", "N/A")}</p>
          <p class="muted">Registros procesados: {contexto["stats_dataset"].get("total_docs", "N/A")}</p>
          <p class="muted">Trazabilidad: metadatos SHA256 y scorecard versionado.</p>
        </div>
      </div>
      <div class="grid">
        <div class="card">
          <h3>Duplicados</h3>
          <div class="value">{formatear_pct(metricas["ratio_duplicados"])}</div>
          <div class="subvalue">Pares detectados por similitud Jaccard.</div>
          <div class="bar"><span style="width:{metricas["ratio_duplicados"] or 0}%;"></span></div>
        </div>
        <div class="card">
          <h3>PII detectada</h3>
          <div class="value">{formatear_pct(metricas["pct_pii"])}</div>
          <div class="subvalue">Emails, telefonos, IPv4, cedulas, credenciales URL.</div>
          <div class="bar"><span style="width:{metricas["pct_pii"] or 0}%;"></span></div>
        </div>
        <div class="card">
          <h3>Toxicidad</h3>
          <div class="value">{formatear_pct(metricas["pct_toxicos"])}</div>
          <div class="subvalue">Score medio: {formatear_float(metricas["score_toxicidad_promedio"])}</div>
          <div class="bar"><span style="width:{metricas["pct_toxicos"] or 0}%;"></span></div>
        </div>
        <div class="card">
          <h3>Registros limpios</h3>
          <div class="value">{formatear_pct(metricas["pct_limpios"])}</div>
          <div class="subvalue">Filtros HTML, longitud y completitud.</div>
          <div class="bar"><span style="width:{metricas["pct_limpios"] or 0}%;"></span></div>
        </div>
      </div>
    </section>

    <section>
      <div class="section-title">
        <h2>Resultados clave</h2>
        <span class="tag">Sintesis</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>Metrica</th>
            <th>Valor</th>
            <th>Comentario</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Ratio de duplicados</td>
            <td>{formatear_pct(metricas["ratio_duplicados"])}</td>
            <td>{duplicados.get("comentario", "LSH + MinHash sobre dataset depurado.")}</td>
          </tr>
          <tr>
            <td>PII detectada</td>
            <td>{formatear_pct(metricas["pct_pii"])}</td>
            <td>Regex sobre texto limpio (email, telefono, IPv4, cedula, credenciales URL).</td>
          </tr>
          <tr>
            <td>Toxicidad</td>
            <td>{formatear_pct(metricas["pct_toxicos"])}</td>
            <td>Diccionario ponderado, score normalizado por longitud.</td>
          </tr>
          <tr>
            <td>Registros limpios</td>
            <td>{formatear_pct(metricas["pct_limpios"])}</td>
            <td>Filtro por HTML, longitud minima y completitud.</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section>
      <div class="section-title">
        <h2>Que se hizo</h2>
        <span class="tag">Pipeline</span>
      </div>
      <ul>
        <li>Ingesta del JSONL y normalizacion basica del texto.</li>
        <li>Filtrado heuristico para remover ruido estructural.</li>
        <li>Deduplicacion difusa con MinHash + LSH.</li>
        <li>Analisis de toxicidad con diccionario ponderado.</li>
        <li>Deteccion de PII con 5 patrones regex.</li>
        <li>Consolidacion de metricas en un scorecard.</li>
      </ul>
    </section>

    <section>
      <div class="section-title">
        <h2>Metricas a detalle</h2>
        <span class="tag">Desglose</span>
      </div>
      <div class="grid">
        <div class="card">
          <h3>Metadatos de ingesta</h3>
          <p><span class="tag">Archivo</span> {metadatos.get("archivo_origen", "N/A")}</p>
          <p><span class="tag">Tamano MB</span> {metadatos.get("tamano_mb", "N/A")}</p>
          <p><span class="tag">SHA256</span> {metadatos.get("hash_sha256", "N/A")}</p>
        </div>
        <div class="card">
          <h3>Deduplicacion</h3>
          <p><span class="tag">N-gramas</span> {duplicados.get("n_gramas", "N/A")}</p>
          <p><span class="tag">Num. perm</span> {duplicados.get("num_perm", "N/A")}</p>
          <p><span class="tag">Umbral Jaccard</span> {duplicados.get("umbral_jaccard", "N/A")}</p>
        </div>
        <div class="card">
          <h3>Dataset final</h3>
          <p><span class="tag">Total docs</span> {contexto["stats_dataset"].get("total_docs", "N/A")}</p>
          <p><span class="tag">PII docs</span> {contexto["stats_dataset"].get("docs_con_pii", "N/A")}</p>
          <p><span class="tag">Score tox prom</span> {formatear_float(contexto["stats_dataset"].get("score_toxicidad_promedio"))}</p>
        </div>
      </div>
      <details>
        <summary>Detalle de PII</summary>
        <p class="muted">Incluye detecciones por patrones: email, telefono, IPv4, cedula y credenciales URL.</p>
      </details>
      <details>
        <summary>Detalle de toxicidad</summary>
        <p class="muted">Score promedio: {formatear_float(metricas["score_toxicidad_promedio"])},
          documentos toxicos: {formatear_pct(metricas["pct_toxicos"])}</p>
      </details>
      <details>
        <summary>Detalle de limpieza estructural</summary>
        <p class="muted">Filtra HTML excesivo, texto corto y campos vacios. Resultado: {formatear_pct(metricas["pct_limpios"])}</p>
      </details>
    </section>

    <section>
      <div class="section-title">
        <h2>Limitaciones y consideraciones</h2>
        <span class="tag">Criterios</span>
      </div>
      <ul>
        <li>Heuristicas de limpieza pueden descartar texto valido o dejar ruido residual.</li>
        <li>Regex de PII prioriza velocidad sobre precision; hay falsos positivos.</li>
        <li>Diccionario de toxicidad no reemplaza un modelo semantico completo.</li>
        <li>El pipeline asume que el campo principal es "texto".</li>
      </ul>
    </section>

    <section>
      <div class="section-title">
        <h2>Recomendaciones automaticas</h2>
        <span class="tag">Accion</span>
      </div>
      <ul>
        {recomendaciones_html}
      </ul>
    </section>

    <footer>
      <p>Reporte generado a partir de outputs existentes del pipeline.</p>
    </footer>
  </main>
</body>
</html>
"""
    return html


def construir_contexto() -> dict:
    ruta_scorecard = obtener_ultimo_scorecard()
    scorecard = leer_json(ruta_scorecard) if ruta_scorecard else None

    metadatos = leer_json(RUTA_METADATOS) or {}
    duplicados_raw = leer_json(RUTA_DUPLICADOS) or {}

    duplicados = {
        "n_gramas": duplicados_raw.get("parametros", {}).get("n_gramas"),
        "num_perm": duplicados_raw.get("parametros", {}).get("num_perm"),
        "umbral_jaccard": duplicados_raw.get("parametros", {}).get("umbral_jaccard"),
        "comentario": "Pares cuasi-duplicados detectados por similitud Jaccard.",
    }

    metricas = extraer_metricas_scorecard(scorecard)
    stats_dataset = cargar_stats_dataset()

    resumen = (
        "Este informe consolida las metricas de calidad tecnica del corpus, "
        "mostrando duplicacion, PII, toxicidad y limpieza estructural. "
        "El objetivo es evidenciar riesgos antes del entrenamiento de LLMs "
        "y demostrar el valor del pipeline en contextos reales."
    )

    return {
        "scorecard_path": str(ruta_scorecard) if ruta_scorecard else "N/A",
        "metadatos": metadatos,
        "duplicados": duplicados,
        "metricas": metricas,
        "stats_dataset": stats_dataset,
        "resumen": resumen,
    }


def main() -> int:
    inicio = time.time()

    SALIDA_DIR.mkdir(parents=True, exist_ok=True)
    contexto = construir_contexto()

    nombre = f"reporte_integridad_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    ruta_salida = SALIDA_DIR / nombre

    html = construir_html(contexto)
    ruta_salida.write_text(html, encoding="utf-8")

    print("=" * 70)
    print("REPORTE HTML GENERADO")
    print("=" * 70)
    print(f"Archivo: {ruta_salida}")
    print(f"Scorecard usado: {contexto['scorecard_path']}")
    print(f"Tiempo total: {time.time() - inicio:.2f} s")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
