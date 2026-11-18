"""Three-view Streamlit demo: raw files, quality audit, and executive dashboard."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.cleaner_pipeline import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, run_pipeline
from src.generate_messy_excels import generate_files

st.set_page_config(
    page_title="Spreadsheet Chaos to Executive Visibility",
    page_icon="📊",
    layout="wide",
)


def _highlight_raw_rows(frame: pd.DataFrame) -> Any:
    styles = pd.DataFrame("", index=frame.index, columns=frame.columns)
    styles.loc[frame.duplicated(keep=False), :] = "background-color: #fff1f0"
    styles[frame.isna()] = "background-color: #fff3cd; color: #7a4f01"
    return frame.style.apply(lambda _: styles, axis=None)


def _load_saved_result() -> dict:
    clean_path = DEFAULT_OUTPUT_DIR / "reporte_gerencial_limpio.xlsx"
    audit_path = DEFAULT_OUTPUT_DIR / "auditoria_calidad.xlsx"
    if not clean_path.exists() or not audit_path.exists():
        if not list(DEFAULT_INPUT_DIR.glob("*.xlsx")):
            generate_files()
        return run_pipeline()

    with pd.ExcelFile(clean_path) as workbook:
        sales = pd.read_excel(workbook, sheet_name="ventas_limpias")
        kpis = {
            sheet: pd.read_excel(workbook, sheet_name=sheet)
            for sheet in ("sucursal", "vendedor", "mensual", "producto")
        }
    with pd.ExcelFile(audit_path) as workbook:
        anomalies = pd.read_excel(workbook, sheet_name="anomalias")
        metric_rows = pd.read_excel(workbook, sheet_name="metricas")
    metrics = dict(zip(metric_rows["metrica"], metric_rows["valor"]))
    return {
        "sales": sales,
        "anomalies": anomalies,
        "metrics": metrics,
        "kpis": kpis,
        "clean_path": clean_path,
        "audit_path": audit_path,
    }


def _run_pipeline(uploaded_files) -> None:
    try:
        if uploaded_files:
            uploads = [(file.name, file.getvalue()) for file in uploaded_files]
            result = run_pipeline(uploaded_files=uploads)
        else:
            generate_files()
            result = run_pipeline()
    except (OSError, ValueError, FileNotFoundError) as error:
        st.sidebar.error(f"No se pudo completar el pipeline: {error}")
        return
    st.session_state["pipeline_result"] = result
    st.sidebar.success("Pipeline ejecutado correctamente.")


if "pipeline_result" not in st.session_state:
    st.session_state["pipeline_result"] = _load_saved_result()

st.title("From Spreadsheet Chaos to Executive Visibility")
st.caption(
    "A live operations and finance demo: validate, reconcile, and report on "
    "spreadsheet sales data."
)

with st.sidebar:
    st.header("Demo controls")
    uploads = st.file_uploader(
        "Upload sales and/or cost Excel workbooks",
        type=["xlsx"],
        accept_multiple_files=True,
        help="If no cost catalog is uploaded, the demo catalog is used.",
    )
    if st.button("Run data pipeline", type="primary", use_container_width=True):
        _run_pipeline(uploads)
    st.caption("Upload new workbooks or rerun the included demo data.")

result = st.session_state["pipeline_result"]
raw_files = sorted(DEFAULT_INPUT_DIR.glob("*.xlsx"))
problem_tab, audit_tab, dashboard_tab = st.tabs(
    ["1 · The problem", "2 · Quality audit", "3 · Executive dashboard"]
)

with problem_tab:
    st.subheader("The problem: spreadsheets do not agree")
    st.write(
        "Inspect the original workbooks before standardization. Highlighted rows "
        "indicate exact duplicates; highlighted cells are blank."
    )
    if not raw_files:
        st.info("No demo workbooks found. Run the pipeline to generate the samples.")
    for path in raw_files:
        with st.expander(path.name, expanded=False):
            raw = pd.read_excel(path, engine="openpyxl")
            st.dataframe(
                _highlight_raw_rows(raw),
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                f"{len(raw):,} rows · {raw.isna().sum().sum():,} blank cells · "
                f"{int(raw.duplicated().sum()):,} exact duplicate rows"
            )

with audit_tab:
    st.subheader("The quality audit: what the pipeline caught")
    metrics = result["metrics"]
    metric_columns = st.columns(4)
    for column, label, key in zip(
        metric_columns,
        ("Rows processed", "Duplicates removed", "IDs normalized", "Quarantined"),
        (
            "filas_procesadas",
            "duplicados_eliminados",
            "ids_normalizados",
            "filas_en_cuarentena",
        ),
    ):
        column.metric(label, int(metrics.get(key, 0)))

    anomalies = result["anomalies"]
    st.dataframe(anomalies, use_container_width=True, hide_index=True)
    csv = anomalies.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Download anomaly audit (CSV)",
        data=csv,
        file_name="auditoria_anomalias.csv",
        mime="text/csv",
    )
    st.download_button(
        "Download complete audit (Excel)",
        data=Path(result["audit_path"]).read_bytes(),
        file_name="auditoria_calidad.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

with dashboard_tab:
    st.subheader("The clean view: a reliable management dashboard")
    sales = result["sales"]
    if sales.empty:
        st.warning("No valid sales rows are available for the dashboard.")
    else:
        sales_total = float(sales["ventas_netas"].sum())
        margin_total = float(sales["margen_bruto"].sum())
        margin_rate = margin_total / sales_total if sales_total else 0
        summary_columns = st.columns(3)
        summary_columns[0].metric("Net sales", f"${sales_total:,.0f}")
        summary_columns[1].metric("Gross margin", f"${margin_total:,.0f}")
        summary_columns[2].metric("Gross margin rate", f"{margin_rate:.1%}")

        left, right = st.columns(2)
        branch = result["kpis"]["sucursal"]
        left.plotly_chart(
            px.bar(
                branch,
                x="sucursal",
                y=["ventas_netas", "margen_bruto"],
                barmode="group",
                title="Net sales and gross margin by branch",
                labels={
                    "sucursal": "Branch",
                    "value": "Amount",
                    "variable": "Metric",
                },
            ),
            use_container_width=True,
        )
        monthly = result["kpis"]["mensual"]
        right.plotly_chart(
            px.line(
                monthly,
                x="mes",
                y=["ventas_netas", "margen_bruto"],
                markers=True,
                title="Monthly sales and gross margin",
                labels={"mes": "Month", "value": "Amount", "variable": "Metric"},
            ),
            use_container_width=True,
        )
        st.plotly_chart(
            px.bar(
                result["kpis"]["producto"].head(10),
                x="sku",
                y="ventas_netas",
                title="Top products by net sales",
                labels={"sku": "Product SKU", "ventas_netas": "Net sales"},
            ),
            use_container_width=True,
        )
        st.download_button(
            "Download clean management workbook",
            data=Path(result["clean_path"]).read_bytes(),
            file_name="reporte_gerencial_limpio.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )
        with st.expander("Inspect validated sales"):
            st.dataframe(sales, use_container_width=True, hide_index=True)
