# Product Radar App - Instrucciones para Cursor

## Objetivo

Crear un **agente Python** que descubra productos populares a nivel global (especialmente de China), analice su viabilidad para reventa en Espana (foco: Bilbao), y genere un informe diario automatizado.

---

## 1. Arquitectura del Proyecto

```
product-radar-app/
  src/
    __init__.py
    main.py                 # Entry point - orquesta el pipeline completo
    config.py               # Carga config.yaml con Pydantic Settings
    models.py               # Modelos Pydantic: Product, Analysis, Report
    scrapers/
      __init__.py
      aliexpress.py         # Scraper AliExpress (httpx + BeautifulSoup)
      amazon_es.py          # Scraper Amazon.es para precios competencia
      google_trends.py      # Google Trends API / pytrends para demanda
      temu.py               # Scraper Temu (opcional)
    analyzers/
      __init__.py
      margin.py             # Calculo de margen: (precio_venta - precio_origen) / precio_venta
      competition.py        # Analisis de competidores en Amazon.es / Google Shopping
      demand.py             # Puntuacion de demanda local (Bilbao/Espana)
      viability.py          # Combina margin + competition + demand -> viability score
    reporters/
      __init__.py
      daily_report.py       # Genera informe Markdown diario en reports/
      csv_export.py         # Exporta productos viables a CSV
      console.py            # Output bonito con Rich
    storage/
      __init__.py
      database.py           # SQLite con SQLAlchemy - persistencia de productos
      memory.py             # Lee/escribe memory.json (historial ligero)
    git_ops.py              # Auto-commit y push con GitPython
    scheduler.py            # APScheduler para ejecucion diaria
  config.yaml               # Configuracion principal
  memory.json               # Estado ligero entre ejecuciones
  reports/                   # Informes diarios generados (Markdown)
  tests/
    test_margin.py
    test_viability.py
  pyproject.toml             # Dependencias (usar uv o pip)
  .gitignore
  README.md
```

---

## 2. Modelos de Datos (models.py)

```python
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class ViabilityStatus(str, Enum):
    VIABLE = "viable"
    MARGINAL = "marginal"
    NOT_VIABLE = "not_viable"

class Product(BaseModel):
    name: str
    source: str                    # "aliexpress", "temu", etc.
    source_url: str
    source_price_eur: float        # Precio de origen en EUR
    category: str
    image_url: str | None = None
    discovered_at: datetime = datetime.now()

class CompetitorData(BaseModel):
    platform: str                  # "amazon.es", "pccomponentes", etc.
    price_eur: float
    seller_name: str
    url: str
    num_reviews: int = 0
    rating: float = 0.0

class ProductAnalysis(BaseModel):
    product: Product
    competitors: list[CompetitorData]
    avg_competitor_price: float
    estimated_margin: float        # 0.0 - 1.0
    demand_score: int              # 1-10 (basado en Google Trends)
    competition_level: str         # "low", "medium", "high"
    viability: ViabilityStatus
    recommended_sale_price: float
    estimated_monthly_units: int
    notes: str = ""
    analyzed_at: datetime = datetime.now()
```

---

## 3. Pipeline Principal (main.py)

El flujo debe ser:

```
1. Cargar config.yaml
2. Cargar memoria (memory.json / SQLite)
3. FASE 1 - DESCUBRIMIENTO:
   - Scrape AliExpress: productos trending, categorias populares
   - Scrape Temu: productos mas vendidos
   - Filtrar: precio_origen <= 100 EUR
   - Deduplicar contra productos ya analizados (memoria)

4. FASE 2 - ANALISIS (por cada producto nuevo):
   a) Buscar precio en Amazon.es -> avg_competitor_price
   b) Buscar Google Trends para "producto + Espana" -> demand_score
   c) Calcular margen: (avg_competitor_price - source_price) / avg_competitor_price
   d) Si margen >= 0.50 Y demand_score >= 5 -> VIABLE
   e) Analizar nivel de competencia (num vendedores, reviews)

5. FASE 3 - REPORTE:
   - Generar reports/YYYY-MM-DD.md con tabla de productos viables
   - Exportar a CSV
   - Mostrar resumen en consola con Rich
   - Guardar en SQLite y memory.json

6. FASE 4 - GIT:
   - git add reports/ memory.json
   - git commit -m "Daily radar: [fecha] - [N] productos viables"
   - git push (si remote configurado)
```

---

## 4. Configuracion (config.yaml)

```yaml
radar:
  max_source_price_eur: 100.00
  min_profit_margin: 0.50
  min_demand_score: 5
  target_market: "Spain"
  target_city: "Bilbao"
  currency: "EUR"
  max_products_per_run: 50
  categories:
    - electronics
    - home_garden
    - kitchen
    - sports_outdoor
    - beauty_health
    - tools
    - pet_supplies

sources:
  aliexpress:
    enabled: true
    base_url: "https://www.aliexpress.com"
    sort_by: "orders"
  temu:
    enabled: false
    base_url: "https://www.temu.com"
  google_trends:
    enabled: true
    region: "ES"
    timeframe: "today 3-m"

competition:
  amazon_es:
    enabled: true
    base_url: "https://www.amazon.es"
  google_shopping:
    enabled: false

schedule:
  daily_run_time: "08:00"
  timezone: "Europe/Madrid"

git:
  auto_commit: true
  auto_push: false
  commit_prefix: "radar"

logging:
  level: "INFO"
  file: "logs/radar.log"
```

---

## 5. Scrapers - Notas de Implementacion

### aliexpress.py
- Usar `httpx` (async) con headers de navegador realista (User-Agent rotativo)
- Parsear con `BeautifulSoup` o `selectolax` (mas rapido)
- Buscar por categoria, ordenar por pedidos/popularidad
- Extraer: nombre, precio, URL, imagen, num_pedidos
- Rate limiting: 2-5 segundos entre requests
- Si AliExpress bloquea, usar la API de affiliados (requiere API key)

### amazon_es.py
- Buscar el nombre del producto en Amazon.es
- Extraer los 5 primeros resultados: precio, vendedor, reviews, rating
- Calcular precio medio de competencia
- Rate limiting: 3-8 segundos entre requests

### google_trends.py
- Usar libreria `pytrends`
- Buscar interes por region (Espana) y por ciudad si es posible
- Devolver un score normalizado de 1-10

---

## 6. Analyzers - Logica de Negocio

### margin.py
```python
def calculate_margin(source_price: float, sale_price: float) -> float:
    if sale_price <= 0:
        return 0.0
    return (sale_price - source_price) / sale_price

def calculate_recommended_price(source_price: float, min_margin: float = 0.50) -> float:
    return source_price / (1 - min_margin)
```

### viability.py
- VIABLE: margen >= 50% AND demanda >= 7 AND competencia != "high"
- MARGINAL: margen >= 50% AND (demanda >= 5 OR competencia == "medium")
- NOT_VIABLE: todo lo demas

---

## 7. Reporter - Formato del Informe Diario

El archivo `reports/YYYY-MM-DD.md` debe tener este formato:

```markdown
# Product Radar - Informe Diario [FECHA]

## Resumen
- Productos escaneados: XX
- Productos viables: XX
- Margen medio: XX%
- Top categoria: [categoria]

## Productos Viables

| # | Producto | Precio Origen | Precio Venta Est. | Margen | Demanda | Competencia | Link |
|---|----------|---------------|---------------------|--------|---------|-------------|------|
| 1 | ...      | 25 EUR        | 55 EUR              | 55%    | 8/10    | Baja        | URL  |

## Productos Marginales
(misma tabla)

## Notas
- [observaciones automaticas del agente]
```

---

## 8. Dependencias (pyproject.toml)

```toml
[project]
name = "product-radar"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27",
    "beautifulsoup4>=4.12",
    "selectolax>=0.3",
    "pandas>=2.2",
    "pyyaml>=6.0",
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "sqlalchemy>=2.0",
    "gitpython>=3.1",
    "pytrends>=4.9",
    "rich>=13.7",
    "apscheduler>=3.10",
    "loguru>=0.7",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.3"]
```

---

## 9. Ejecucion Diaria

### Opcion A: Windows Task Scheduler
```powershell
schtasks /create /tn "ProductRadar" /tr "python C:\Users\a.acharya\Desktop\product-radar-app\src\main.py" /sc daily /st 08:00
```

### Opcion B: GitHub Actions
```yaml
name: Daily Product Radar
on:
  schedule:
    - cron: '0 6 * * *'
  workflow_dispatch:

jobs:
  radar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e .
      - run: python src/main.py
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "radar: daily run"
```

---

## 10. Reglas Importantes para Cursor

1. **NO hardcodear claves API** - usar variables de entorno o config.yaml (gitignored)
2. **Rate limiting obligatorio** - delays entre requests para no ser bloqueado
3. **Manejo de errores robusto** - un scraper fallando no debe parar todo el pipeline
4. **Logging con loguru** - todo debe quedar registrado
5. **Type hints en todo** - el codigo debe ser 100% tipado
6. **Tests** - al menos tests unitarios para margin.py y viability.py
7. **Respetar robots.txt** - si un sitio lo prohibe, buscar alternativa (API, etc.)
8. **User-Agent realista** - no usar el default de httpx/requests
9. **Datos en EUR** - convertir si la fuente esta en USD/CNY
10. **Informe legible** - el Markdown generado debe ser util para un humano, no solo datos crudos
