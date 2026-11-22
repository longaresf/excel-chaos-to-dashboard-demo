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

from app.i18n import (
    DEFAULT_LANGUAGE,
    LABEL_TO_LANGUAGE,
    SUPPORTED_LANGUAGES,
    get_audit_metric_cards,
    localize_dataframe,
    t,
)
from src.cleaner_pipeline import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, run_pipeline
from src.generate_messy_excels import generate_files

# Determine active language before rendering any widgets
selected_label = st.session_state.get("lang_choice")
if selected_label and selected_label in LABEL_TO_LANGUAGE:
    active_lang = LABEL_TO_LANGUAGE[selected_label]
else:
    active_lang = st.session_state.get("language", DEFAULT_LANGUAGE)
if active_lang not in SUPPORTED_LANGUAGES:
    active_lang = DEFAULT_LANGUAGE
st.session_state["language"] = active_lang

st.set_page_config(
    page_title=t("page_title", active_lang),
    page_icon="📊",
    layout="wide",
)


def _highlight_raw_rows(frame: pd.DataFrame) -> Any:
    styles = pd.DataFrame("", index=frame.index, columns=frame.columns)
    styles.loc[frame.duplicated(keep=False), :] = (
        "background-color: rgba(239, 68, 68, 0.25); color: #fca5a5;"
    )
    styles[frame.isna()] = (
        "background-color: rgba(245, 158, 11, 0.25); color: #fcd34d;"
    )
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
    metrics = dict(zip(metric_rows["metrica"], metric_rows["valor"], strict=False))
    return {
        "sales": sales,
        "anomalies": anomalies,
        "metrics": metrics,
        "kpis": kpis,
        "clean_path": clean_path,
        "audit_path": audit_path,
    }


def _run_pipeline(uploaded_files, lang: str = DEFAULT_LANGUAGE) -> None:
    try:
        if uploaded_files:
            uploads = [(file.name, file.getvalue()) for file in uploaded_files]
            result = run_pipeline(uploaded_files=uploads)
        else:
            generate_files()
            result = run_pipeline()
    except (OSError, ValueError, FileNotFoundError) as error:
        st.sidebar.error(t("pipeline_error", lang, error=error))
        return
    st.session_state["pipeline_result"] = result
    st.sidebar.success(t("pipeline_success", lang))


if "pipeline_result" not in st.session_state:
    st.session_state["pipeline_result"] = _load_saved_result()

st.title(t("app_title", active_lang))
st.caption(t("app_caption", active_lang))

with st.sidebar:
    st.selectbox(
        t("language_selector_label", active_lang),
        options=["Español", "English"],
        index=0 if active_lang == "es" else 1,
        key="lang_choice",
    )
    st.header(t("sidebar_header", active_lang))
    uploads = st.file_uploader(
        t("uploader_label", active_lang),
        type=["xlsx"],
        accept_multiple_files=True,
        help=t("uploader_help", active_lang),
    )
    if st.button(
        t("run_pipeline_button", active_lang),
        type="primary",
        use_container_width=True,
    ):
        _run_pipeline(uploads, active_lang)
    st.caption(t("sidebar_caption", active_lang))

result = st.session_state["pipeline_result"]
raw_files = sorted(DEFAULT_INPUT_DIR.glob("*.xlsx"))
problem_tab, audit_tab, dashboard_tab = st.tabs(
    [
        t("tab_problem", active_lang),
        t("tab_audit", active_lang),
        t("tab_dashboard", active_lang),
    ]
)

with problem_tab:
    st.subheader(t("problem_subheader", active_lang))
    st.write(t("problem_description", active_lang))
    if not raw_files:
        st.info(t("problem_no_files", active_lang))
    for path in raw_files:
        with st.expander(path.name, expanded=False):
            raw = pd.read_excel(path, engine="openpyxl")
            st.dataframe(
                _highlight_raw_rows(raw),
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                t(
                    "raw_file_caption",
                    active_lang,
                    rows=len(raw),
                    blanks=int(raw.isna().sum().sum()),
                    duplicates=int(raw.duplicated().sum()),
                )
            )

with audit_tab:
    st.subheader(t("audit_subheader", active_lang))
    metrics = result["metrics"]
    metric_columns = st.columns(4)
    for column, (label, key) in zip(
        metric_columns,
        get_audit_metric_cards(active_lang),
        strict=False,
    ):
        column.metric(label, int(metrics.get(key, 0)))

    anomalies = result["anomalies"]
    st.dataframe(
        localize_dataframe(anomalies, active_lang),
        use_container_width=True,
        hide_index=True,
    )
    csv = anomalies.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        t("download_anomaly_csv", active_lang),
        data=csv,
        file_name="auditoria_anomalias.csv",
        mime="text/csv",
    )
    st.download_button(
        t("download_complete_audit_excel", active_lang),
        data=Path(result["audit_path"]).read_bytes(),
        file_name="auditoria_calidad.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

with dashboard_tab:
    st.subheader(t("dashboard_subheader", active_lang))
    sales = result["sales"]
    if sales.empty:
        st.warning(t("no_sales_warning", active_lang))
    else:
        sales_total = float(sales["ventas_netas"].sum())
        margin_total = float(sales["margen_bruto"].sum())
        margin_rate = margin_total / sales_total if sales_total else 0
        summary_columns = st.columns(3)
        summary_columns[0].metric(
            t("metric_net_sales", active_lang), f"${sales_total:,.0f}"
        )
        summary_columns[1].metric(
            t("metric_gross_margin", active_lang), f"${margin_total:,.0f}"
        )
        summary_columns[2].metric(
            t("metric_margin_rate", active_lang), f"{margin_rate:.1%}"
        )

        trace_labels = {
            "ventas_netas": t("label_net_sales", active_lang),
            "margen_bruto": t("label_gross_margin", active_lang),
        }

        left, right = st.columns(2)
        branch = result["kpis"]["sucursal"]
        fig_branch = px.bar(
            branch,
            x="sucursal",
            y=["ventas_netas", "margen_bruto"],
            barmode="group",
            title=t("chart_branch_title", active_lang),
            labels={
                "sucursal": t("label_branch", active_lang),
                "value": t("label_amount", active_lang),
                "variable": t("label_metric", active_lang),
                "ventas_netas": t("label_net_sales", active_lang),
                "margen_bruto": t("label_gross_margin", active_lang),
            },
        )
        fig_branch.for_each_trace(
            lambda tr: tr.update(name=trace_labels.get(tr.name, tr.name))
        )
        left.plotly_chart(
            fig_branch,
            use_container_width=True,
        )

        monthly = result["kpis"]["mensual"]
        fig_monthly = px.line(
            monthly,
            x="mes",
            y=["ventas_netas", "margen_bruto"],
            markers=True,
            title=t("chart_monthly_title", active_lang),
            labels={
                "mes": t("label_month", active_lang),
                "value": t("label_amount", active_lang),
                "variable": t("label_metric", active_lang),
                "ventas_netas": t("label_net_sales", active_lang),
                "margen_bruto": t("label_gross_margin", active_lang),
            },
        )
        fig_monthly.for_each_trace(
            lambda tr: tr.update(name=trace_labels.get(tr.name, tr.name))
        )
        right.plotly_chart(
            fig_monthly,
            use_container_width=True,
        )

        fig_product = px.bar(
            result["kpis"]["producto"].head(10),
            x="sku",
            y="ventas_netas",
            title=t("chart_product_title", active_lang),
            labels={
                "sku": t("label_sku", active_lang),
                "ventas_netas": t("label_net_sales", active_lang),
            },
        )
        st.plotly_chart(
            fig_product,
            use_container_width=True,
        )

        st.download_button(
            t("download_clean_excel", active_lang),
            data=Path(result["clean_path"]).read_bytes(),
            file_name="reporte_gerencial_limpio.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )
        with st.expander(t("expander_inspect_sales", active_lang)):
            st.dataframe(
                localize_dataframe(sales, active_lang),
                use_container_width=True,
                hide_index=True,
            )
