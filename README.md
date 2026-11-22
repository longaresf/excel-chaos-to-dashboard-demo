# From Spreadsheet Chaos to Automated Executive Visibility

Turn scattered sales spreadsheets into one consistent view of revenue, gross
margin, and data quality. This runnable demo shows an operations or finance
team how repeatable validation can replace manual spreadsheet cleanup with a
traceable management report.

## Run the live demo

With Docker and Docker Compose installed, run:

```bash
docker compose up --build
```

Open [http://localhost:8501](http://localhost:8501). The container creates the
three sample Excel workbooks when they are missing, runs the initial cleaning
pipeline, and starts the dashboard. Generated input and output workbooks are
persisted in `data/`.

To run locally with Python 3.11 or newer:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.generate_messy_excels
python -m src.cleaner_pipeline
streamlit run app/dashboard.py
```

Run the automated checks with `pytest -q`.

## The three-minute walkthrough

1. **The problem:** inspect the original branch workbooks and spot inconsistent
   dates, currency formats, identifiers, missing values, and duplicate rows.
2. **The quality audit:** run the pipeline, review row counts and exact anomaly
   reasons, and download the audit as CSV or Excel.
3. **Executive visibility:** explore net sales and gross margin by branch,
   month, and product, then download the consolidated workbook.

Use the sidebar to rerun the included inputs or upload one or more `.xlsx`
workbooks. Upload sales sheets using the demonstrated columns and aliases; a
cost catalog must contain `SKU` and `Costo Unitario`. When uploading sales
without a catalog, the generated demo catalog is used.

## Data flow

```text
Messy Excel workbooks / uploads
              |
              v
Column mapping -> parsing -> strict Pydantic row validation
              |                         |
              |                         +--> critical row quarantine
              v
Exact deduplication -> RUT/SKU normalization -> cost enrichment
              |                         |
              +--> anomaly audit <-----+
              |
              v
Clean management workbook -> KPI tables -> Streamlit + Plotly dashboard
```

The pipeline records every exact duplicate, normalized tax ID, negative-margin
sale, and quarantined critical row. It does not silently drop invalid sales:
quarantined records include the source workbook, row number, and reason.

## Project layout

```text
.github/workflows/ci.yml       CI checks on pushes and pull requests
data/dirty_input/              Generated source workbooks
data/clean_output/             Consolidated report and quality audit
src/generate_messy_excels.py   Deterministic Excel demo-data generator
src/cleaner_pipeline.py        Parsing, validation, cleaning, and reporting
src/kpi_engine.py              Branch, seller, month, and product metrics
app/dashboard.py               Three-view Streamlit and Plotly application
tests/test_cleaner.py          Focused cleaning and regression tests
```

## Outputs

- `data/clean_output/reporte_gerencial_limpio.xlsx`: validated sales and KPI
  worksheets.
- `data/clean_output/auditoria_calidad.xlsx`: anomaly details and quality
  metrics.
- The dashboard also offers a CSV download of the anomaly list.
