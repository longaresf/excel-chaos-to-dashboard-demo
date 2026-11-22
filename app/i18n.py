"""Internationalization (i18n) module for the Streamlit dashboard."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

DEFAULT_LANGUAGE = "es"
SUPPORTED_LANGUAGES: tuple[str, ...] = ("es", "en")

LANGUAGE_NAMES: dict[str, str] = {
    "es": "Español",
    "en": "English",
}

LABEL_TO_LANGUAGE: dict[str, str] = {
    "Español": "es",
    "English": "en",
}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "es": {
        # Configuración de página y títulos principales
        "page_title": "Del Caos de Planillas a la Visibilidad Ejecutiva",
        "app_title": "Del caos de hojas de cálculo a la visibilidad ejecutiva",
        "app_caption": (
            "Demostración operativa y financiera en vivo: valida, concilia "
            "y reporta datos de ventas en hojas de cálculo."
        ),
        # Panel lateral
        "sidebar_header": "Controles de la demo",
        "language_selector_label": "Idioma / Language",
        "uploader_label": "Subir libros de ventas y/o costos en Excel",
        "uploader_help": (
            "Si no se sube un catálogo de costos, se utiliza el catálogo de la demo."
        ),
        "run_pipeline_button": "Ejecutar pipeline de datos",
        "sidebar_caption": (
            "Sube nuevos libros o vuelve a ejecutar los datos de demostración incluidos."
        ),
        "pipeline_error": "No se pudo completar el pipeline: {error}",
        "pipeline_success": "Pipeline ejecutado correctamente.",
        # Pestañas
        "tab_problem": "1 · El problema",
        "tab_audit": "2 · Auditoría de calidad",
        "tab_dashboard": "3 · Panel ejecutivo",
        # Pestaña 1: El problema
        "problem_subheader": "El problema: las hojas de cálculo no coinciden",
        "problem_description": (
            "Inspecciona los libros originales antes de la estandarización. "
            "Las filas resaltadas indican duplicados exactos; las celdas resaltadas están vacías."
        ),
        "problem_no_files": (
            "No se encontraron libros de demostración. Ejecuta el pipeline para generar las muestras."
        ),
        "raw_file_caption": (
            "{rows:,} filas · {blanks:,} celdas en blanco · {duplicates:,} filas duplicadas exactas"
        ),
        # Pestaña 2: Auditoría de calidad
        "audit_subheader": "La auditoría de calidad: lo que detectó el pipeline",
        "metric_rows_processed": "Filas procesadas",
        "metric_duplicates_removed": "Duplicados eliminados",
        "metric_ids_normalized": "IDs normalizados",
        "metric_quarantined": "En cuarentena",
        "download_anomaly_csv": "Descargar auditoría de anomalías (CSV)",
        "download_complete_audit_excel": "Descargar auditoría completa (Excel)",
        # Pestaña 3: Panel ejecutivo
        "dashboard_subheader": "La vista limpia: un panel gerencial confiable",
        "no_sales_warning": "No hay filas de ventas válidas disponibles para el panel.",
        "metric_net_sales": "Ventas netas",
        "metric_gross_margin": "Margen bruto",
        "metric_margin_rate": "Tasa de margen bruto",
        "chart_branch_title": "Ventas netas y margen bruto por sucursal",
        "chart_monthly_title": "Ventas netas y margen bruto mensual",
        "chart_product_title": "Top productos por ventas netas",
        "label_branch": "Sucursal",
        "label_month": "Mes",
        "label_amount": "Monto",
        "label_metric": "Métrica",
        "label_sku": "SKU del producto",
        "label_net_sales": "Ventas netas",
        "label_gross_margin": "Margen bruto",
        "download_clean_excel": "Descargar libro gerencial limpio",
        "expander_inspect_sales": "Inspeccionar ventas validadas",
    },
    "en": {
        # Page config and main titles
        "page_title": "Spreadsheet Chaos to Executive Visibility",
        "app_title": "From Spreadsheet Chaos to Executive Visibility",
        "app_caption": (
            "A live operations and finance demo: validate, reconcile, "
            "and report on spreadsheet sales data."
        ),
        # Sidebar
        "sidebar_header": "Demo controls",
        "language_selector_label": "Language / Idioma",
        "uploader_label": "Upload sales and/or cost Excel workbooks",
        "uploader_help": (
            "If no cost catalog is uploaded, the demo catalog is used."
        ),
        "run_pipeline_button": "Run data pipeline",
        "sidebar_caption": (
            "Upload new workbooks or rerun the included demo data."
        ),
        "pipeline_error": "Could not complete pipeline: {error}",
        "pipeline_success": "Pipeline executed successfully.",
        # Tabs
        "tab_problem": "1 · The problem",
        "tab_audit": "2 · Quality audit",
        "tab_dashboard": "3 · Executive dashboard",
        # Tab 1: The problem
        "problem_subheader": "The problem: spreadsheets do not agree",
        "problem_description": (
            "Inspect the original workbooks before standardization. "
            "Highlighted rows indicate exact duplicates; highlighted cells are blank."
        ),
        "problem_no_files": (
            "No demo workbooks found. Run the pipeline to generate the samples."
        ),
        "raw_file_caption": (
            "{rows:,} rows · {blanks:,} blank cells · {duplicates:,} exact duplicate rows"
        ),
        # Tab 2: Quality audit
        "audit_subheader": "The quality audit: what the pipeline caught",
        "metric_rows_processed": "Rows processed",
        "metric_duplicates_removed": "Duplicates removed",
        "metric_ids_normalized": "IDs normalized",
        "metric_quarantined": "Quarantined",
        "download_anomaly_csv": "Download anomaly audit (CSV)",
        "download_complete_audit_excel": "Download complete audit (Excel)",
        # Tab 3: Executive dashboard
        "dashboard_subheader": "The clean view: a reliable management dashboard",
        "no_sales_warning": "No valid sales rows are available for the dashboard.",
        "metric_net_sales": "Net sales",
        "metric_gross_margin": "Gross margin",
        "metric_margin_rate": "Gross margin rate",
        "chart_branch_title": "Net sales and gross margin by branch",
        "chart_monthly_title": "Monthly sales and gross margin",
        "chart_product_title": "Top products by net sales",
        "label_branch": "Branch",
        "label_month": "Month",
        "label_amount": "Amount",
        "label_metric": "Metric",
        "label_sku": "Product SKU",
        "label_net_sales": "Net sales",
        "label_gross_margin": "Gross margin",
        "download_clean_excel": "Download clean management workbook",
        "expander_inspect_sales": "Inspect validated sales",
    },
}

COLUMN_TRANSLATIONS: dict[str, dict[str, str]] = {
    "es": {
        "fecha": "Fecha",
        "sucursal": "Sucursal",
        "cliente": "Cliente",
        "id_tributario": "ID Tributario",
        "sku": "SKU",
        "unidades": "Unidades",
        "precio_unitario": "Precio Unitario",
        "costo_unitario": "Costo Unitario",
        "ventas_netas": "Ventas Netas",
        "costo_total": "Costo Total",
        "margen_bruto": "Margen Bruto",
        "vendedor": "Vendedor",
        "archivo_origen": "Archivo Origen",
        "tipo": "Tipo",
        "severidad": "Severidad",
        "archivo": "Archivo",
        "fila": "Fila",
        "motivo": "Motivo",
        "mes": "Mes",
    },
    "en": {
        "fecha": "Date",
        "sucursal": "Branch",
        "cliente": "Customer",
        "id_tributario": "Tax ID",
        "sku": "SKU",
        "unidades": "Units",
        "precio_unitario": "Unit Price",
        "costo_unitario": "Unit Cost",
        "ventas_netas": "Net Sales",
        "costo_total": "Total Cost",
        "margen_bruto": "Gross Margin",
        "vendedor": "Salesperson",
        "archivo_origen": "Source File",
        "tipo": "Type",
        "severidad": "Severity",
        "archivo": "File",
        "fila": "Row",
        "motivo": "Reason",
        "mes": "Month",
    },
}


def t(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs: Any) -> str:
    """Retrieve translated string by key and format with kwargs.

    Falls back to Spanish if key is missing in target language, or returns key itself.
    """
    target_lang = lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    template = TRANSLATIONS.get(target_lang, {}).get(key)
    if template is None:
        template = TRANSLATIONS.get(DEFAULT_LANGUAGE, {}).get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return template
    return template


def localize_dataframe(
    frame: pd.DataFrame, lang: str = DEFAULT_LANGUAGE
) -> pd.DataFrame:
    """Return a display-friendly copy of frame with localized column headers."""
    target_lang = lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    col_map = COLUMN_TRANSLATIONS.get(target_lang, {})
    return frame.rename(columns=lambda col: col_map.get(str(col), str(col)))


def get_audit_metric_cards(
    lang: str = DEFAULT_LANGUAGE,
) -> list[tuple[str, str]]:
    """Return ordered list of (display_label, metric_key) for quality audit metrics."""
    return [
        (t("metric_rows_processed", lang), "filas_procesadas"),
        (t("metric_duplicates_removed", lang), "duplicados_eliminados"),
        (t("metric_ids_normalized", lang), "ids_normalizados"),
        (t("metric_quarantined", lang), "filas_en_cuarentena"),
    ]


def extract_format_placeholders(text: str) -> set[str]:
    """Extract format placeholder names like {rows} or {error} from a template string."""
    return set(re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)(?::[^}]*)?\}", text))
