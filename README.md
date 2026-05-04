# Evaluación de Integridad Técnica en Datos de Entrenamiento de LLMs

Pipeline modular para auditar la calidad de corpus web (Common Crawl) antes
del entrenamiento de Modelos de Lenguaje de Gran Escala (LLMs). Diseñado
para funcionar en hardware local con recursos limitados (CPU estándar, 8-24 GB
de RAM, GPU con 6-8 GB de VRAM).

**Institución:** Colegio Mayor del Cauca – Ingeniería Informática  
**Año:** 2026  
**Autores:** Yeison Muñoz (PM), Fabian Hoyos (NLP), Andrés Torres (DE),
Alex Santacruz (QA/TW)  
**SCRUM-ID del proyecto:** EP-1 a EP-5, Sprints 1–9


## Tabla de contenidos

- [Descripción general](#descripción-general)
- [Arquitectura del pipeline](#arquitectura-del-pipeline)
- [Estructura de directorios](#estructura-de-directorios)
- [Requisitos del sistema](#requisitos-del-sistema)
- [Instalación](#instalación)
- [Uso rápido](#uso-rápido)
- [Módulos del pipeline](#módulos-del-pipeline)
- [Métricas de integridad (Scorecard)](#métricas-de-integridad-scorecard)
- [Dataset de prueba](#dataset-de-prueba)
- [Notas de diseño](#notas-de-diseño)
- [Estado del proyecto](#estado-del-proyecto)
- [Licencia](#licencia)


## Descripción general

Los Modelos de Lenguaje de Gran Escala (LLMs) se entrenan con datos masivos
extraídos de la web. Estos datos contienen vulnerabilidades críticas:
* **Redundancia extrema:** Hasta el 50 % de los documentos pueden ser duplicados.
* **Información personal (PII):** Correos, teléfonos, cédulas expuestas.
* **Contenido tóxico:** Lenguaje ofensivo o discurso de odio.
* **Ruido estructural:** Fragmentos HTML, registros incompletos, código basura.

Este proyecto ofrece un **pipeline heurístico ligero** que evalúa la integridad
técnica de un corpus **antes** de entrenar un modelo, permitiendo a
investigadores con hardware limitado tomar decisiones informadas sobre la
calidad de sus datos.

### ¿Por qué un MVP con 1-5 GB de muestra?

El proyecto académico completo requeriría procesar **terabytes** de Common Crawl.
En un entorno universitario con una GPU de 8 GB de VRAM y un cronograma de
16 semanas, eso es inviable. **Delimitar el alcance a una muestra representativa
de 1-5 GB fue una decisión estratégica de adaptación (tailoring)** para hacer el
proyecto alcanzable y demostrable.


## Arquitectura del pipeline
┌─────────────────────────────────────────────────────┐
│ DOCKER (opcional)                                   │
│ ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌───────┐   │
│ │ INGESTA  │→│DEPURACIÓN│→│ SEMÁNTICA │→│REPORTE│   │
│ │          │ │          │ │           │ │       │   │
│ │ JSONL →  │ │ MinHash  │ │ Toxicidad │ │  JSON │   │
│ │ Parquet  │ │ + LSH    │ │ PII regex │ │ Score-│   │
│ │          │ │  Filtros │ │           │ │  card │   │
│ └──────────┘ └──────────┘ └───────────┘ └───────┘   │
└─────────────────────────────────────────────────────┘

1. **Ingesta:** Lee archivos JSONL por chunks. Limpia HTML residual, valida
   esquema y convierte a formato columnar Apache Parquet.
2. **Depuración:** Aplica filtros heurísticos (ratio HTML, longitud mínima) y
   deduplicación difusa con MinHash + Locality-Sensitive Hashing.
3. **Semántica:** Calcula score de toxicidad con diccionario ponderado
   (200+ términos). Detecta PII con 5 patrones regex.
4. **Reporte:** Consolida todo en un Scorecard JSON con 4 métricas clave.


## Estructura de directorios
codigo/
├── data/ ← Datasets generados (no versionar)
│ ├── muestra.jsonl ← Dataset de prueba (52 registros)
│ ├── muestra.parquet ← Tras ingesta
│ ├── muestra_depurada.parquet ← Tras filtros heurísticos
│ ├── muestra_con_toxicidad.parquet ← Tras análisis de toxicidad
│ ├── muestra_con_pii.parquet ← Tras detección de PII
│ ├── duplicados_encontrados.json← Pares duplicados
│ └── metadatos_ingesta.json ← Procedencia de la muestra
├── toxicidad_dic.json ← Diccionario de toxicidad (200+ términos)
├── requirements_llm_data.txt ← Dependencias Python
├── pipeline_ingesta.py ← Módulo 1
├── limpieza_heuristica.py ← Módulo 2
├── minhash_dedup.py ← Módulo 3
├── toxicidad.py ← Módulo 4
├── deteccion_pii.py ← Módulo 5
├── scorecard.py ← Módulo 6
├── pipeline.py ← Script maestro
├── scorecard_*.json ← Scorecard generado
└── README.md ← Este archivo



## Requisitos del sistema

| Componente          | Mínimo                       | Recomendado           |
|---------------------|------------------------------|-----------------------|
| Sistema operativo   | Windows 10/11, Ubuntu 22.04+ | Ubuntu 24.04 LTS      |
| RAM                 | 8 GB                         | 16-32 GB              |
| Disco               | 2 GB libres                  | SSD NVMe              |
| Python              | 3.10+                        | 3.11                  |
| GPU (opcional)      | No requerida para MVP        | NVIDIA con CUDA 12.6+ |


## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/usuario/llm-data-integrity.git
cd llm-data-integrity/codigo
```

### 2. Crear entorno virtual (recomendado)

```bash
python -m venv venv
```

#### En Windows

```powershell
venv\Scripts\activate
```

#### En Linux/Mac

```bash
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements_llm_data.txt
```

### 4. Verificar instalación

```bash
python -c "import pandas, pyarrow, datasketch; print('OK')"
```


## Uso rápido

### Ejecutar el pipeline completo

```bash
python pipeline.py
```

Esto ejecutará secuencialmente los 6 módulos y generará:

- Archivos Parquet intermedios en `data/`
- Un Scorecard JSON (`scorecard_YYYYMMDD_HHMMSS.json`)

### Ejecutar un módulo específico

```bash
python pipeline_ingesta.py       # Solo ingesta
python limpieza_heuristica.py    # Solo filtros
python minhash_dedup.py          # Solo deduplicación
python toxicidad.py              # Solo toxicidad
python deteccion_pii.py          # Solo PII
python scorecard.py              # Solo scorecard
```

### Ver ayuda

```bash
python pipeline.py --help
python minhash_dedup.py --help
```


## Módulos del pipeline

1. `pipeline_ingesta.py` (SCRUM-19)
   - Lee `data/muestra.jsonl`, limpia HTML básico y genera `data/muestra.parquet` en formato columnar.

2. `limpieza_heuristica.py` (SCRUM-21)
   - Aplica tres filtros de calidad:
     - Ratio HTML/texto > 0.3 → descartar
     - Longitud de texto < 100 caracteres → descartar
     - Campo de texto ausente o vacío → descartar

3. `minhash_dedup.py` (SCRUM-20)
   - Detecta documentos cuasi-duplicados usando:
     - Shingling de 5 caracteres
     - 128 funciones hash MinHash
     - LSH con umbral Jaccard ≥ 0.8
     - 16 bandas × 8 filas

4. `toxicidad.py` (SCRUM-22)
   - Calcula score de toxicidad para cada documento usando un diccionario ponderado con 200+ términos en español e inglés.
   - Score normalizado por longitud.

5. `deteccion_pii.py` (SCRUM-23)
   - Aplica 5 patrones regex para detectar:
     - Correos electrónicos
     - Teléfonos colombianos
     - Direcciones IPv4
     - Cédulas de ciudadanía
     - Credenciales en URLs

6. `scorecard.py` (SCRUM-24)
   - Genera un JSON consolidado con las 4 métricas de integridad y recomendaciones automáticas basadas en umbrales configurables.


## Métricas de integridad (Scorecard)

| ID     | Métrica                       | Método             | Umbral de alerta                    |
|--------|-------------------------------|--------------------|-------------------------------------|
| MI-01  | Ratio de duplicados           | MinHash + LSH      | > 10%                               |
| MI-02  | % documentos con PII          | Regex (5 patrones) | > 2%                                |
| MI-03  | Toxicidad                     | Diccionario        | > 5% docs con score > 0.5           |
| MI-04  | % registros limpios           | Filtros heurísticos | < 80%                             |

El Scorecard incluye recomendaciones automáticas para cada métrica según si
supera o no los umbrales.


## Dataset de prueba

El archivo `data/muestra.jsonl` contiene 52 registros de ejemplo con diferentes características:

- Textos normales de varias temáticas
- Documentos con HTML residual
- Documentos cuasi-duplicados
- Correos electrónicos y teléfonos colombianos
- Textos con distintos niveles de toxicidad

Puedes reemplazarlo con cualquier archivo JSONL que tenga al menos un campo
`texto` con el contenido del documento.


## Notas de diseño

### ¿Por qué MinHash y no embeddings semánticos?

Los embeddings (BERT, Sentence-Transformers) producen resultados más precisos, pero:

- Requieren cargar modelos de cientos de MB en RAM/VRAM.
- Procesar millones de documentos con embeddings es inviable en una GPU de 8 GB.

MinHash + LSH ofrece un balance excelente entre precisión y eficiencia.

### ¿Por qué regex y no modelos NER para PII?

Las expresiones regulares son inmediatas, no requieren GPU y son transparentes (se puede auditar cada patrón).

Los falsos positivos están documentados como hallazgo técnico.

La evolución planificada del proyecto es integrar Microsoft Presidio con modelos NER ligeros.


## Gestión de memoria

Todos los módulos procesan por chunks (lotes) para mantener la RAM plana (~1.5-2.5 GB).

El formato Parquet permite mapeo de memoria (`memory_map`) y evita cargar todo el dataset simultáneamente.


## Estado del proyecto

| Sprint | Épica                                          | Estado                    |
|--------|------------------------------------------------|---------------------------|
| 1-2    | EP-1: Planificación y Cimientos                | ✅ Completado             |
| 3      | EP-2: Diseño de Arquitectura                   | ✅ Completado             |
| 4      | EP-3: Pipeline (Ingesta)                       | ✅ Completado             |
| 5      | EP-3: Pipeline (Depuración)                    | ✅ Completado             |
| 6      | EP-3: Pipeline (Semántica)                     | 🔄 En progreso           |
| 7      | EP-3: Pipeline (Integración E2E + Reportes)    | ⬜ Pendiente             |
| 8      | EP-4: Validación y Pruebas                     | ⬜ Pendiente             |
| 9      | EP-5: Cierre y Transferencia                   | ⬜ Pendiente             |

Cierre proyectado: Mayo 24, 2026


## Licencia

Este proyecto es de uso académico. Consulte con los autores antes de
redistribuir o modificar.

