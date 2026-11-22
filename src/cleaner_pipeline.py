"""Validate, standardize, enrich, and report on incoming sales workbooks."""

from __future__ import annotations

import io
import math
import re
import unicodedata
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.kpi_engine import calculate_kpis

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = ROOT_DIR / "data" / "dirty_input"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data" / "clean_output"


class SalesRow(BaseModel):
    """Strict schema for a normalized, validated sale."""

    model_config = ConfigDict(strict=True, extra="forbid")

    fecha: date
    sucursal: str = Field(min_length=1)
    cliente: str = Field(min_length=1)
    id_tributario: str = Field(pattern=r"^\d{7,8}[0-9K]$")
    sku: str = Field(min_length=1)
    unidades: int = Field(gt=0)
    precio_unitario: float = Field(ge=0)
    vendedor: str = Field(min_length=1)


ALIASES = {
    "fecha": "fecha",
    "fecha_venta": "fecha",
    "date": "fecha",
    "cliente": "cliente",
    "nombre_cliente": "cliente",
    "customer": "cliente",
    "id_tributario": "id_tributario",
    "cliente_rut": "id_tributario",
    "rut": "id_tributario",
    "id_fiscal": "id_tributario",
    "producto": "sku",
    "sku": "sku",
    "codigo_producto": "sku",
    "unidades": "unidades",
    "cantidad": "unidades",
    "qty": "unidades",
    "precio_unitario": "precio_unitario",
    "monto_unitario": "precio_unitario",
    "vendedor": "vendedor",
    "ejecutivo": "vendedor",
    "salesperson": "vendedor",
    "sucursal": "sucursal",
    "costo_unitario": "costo_unitario",
    "costo": "costo_unitario",
    "unit_cost": "costo_unitario",
}

OUTPUT_COLUMNS = [
    "fecha",
    "sucursal",
    "cliente",
    "id_tributario",
    "sku",
    "unidades",
    "precio_unitario",
    "costo_unitario",
    "ventas_netas",
    "costo_total",
    "margen_bruto",
    "vendedor",
    "archivo_origen",
]
ANOMALY_COLUMNS = [
    "tipo",
    "severidad",
    "archivo",
    "fila",
    "id_tributario",
    "sku",
    "motivo",
]


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _normalized_column(column: Any) -> str:
    text = unicodedata.normalize("NFKD", str(column))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _canonical_record(record: dict[str, Any]) -> dict[str, Any]:
    canonical: dict[str, Any] = {}
    for key, value in record.items():
        target = ALIASES.get(_normalized_column(key))
        if target and (target not in canonical or _is_missing(canonical[target])):
            canonical[target] = value
    return canonical


def normalize_tax_id(value: Any) -> str:
    """Return a punctuation-free Chilean RUT and reject malformed IDs."""
    if _is_missing(value):
        raise ValueError("ID tributario nulo o vacío")
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    normalized = re.sub(r"[.\-\s]", "", str(value)).upper()
    if not re.fullmatch(r"\d{7,8}[0-9K]", normalized):
        raise ValueError(f"ID tributario inválido: {value!r}")
    return normalized


def normalize_sku(value: Any) -> str:
    if _is_missing(value):
        raise ValueError("SKU nulo o vacío")
    normalized = re.sub(r"[^A-Z0-9]", "", str(value).upper())
    if not normalized:
        raise ValueError("SKU nulo o vacío")
    return normalized


def parse_mixed_date(value: Any) -> date:
    """Parse common spreadsheet date formats, preferring day/month ordering."""
    if _is_missing(value):
        raise ValueError("fecha nula o vacía")
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        parsed = pd.to_datetime(text, dayfirst=True, errors="raise")
    except (TypeError, ValueError) as error:
        raise ValueError(f"fecha inválida: {value!r}") from error
    if pd.isna(parsed):
        raise ValueError(f"fecha inválida: {value!r}")
    return parsed.date()


def parse_amount(value: Any) -> float:
    """Parse common currency layouts such as 1.234,50 and 1,234.50."""
    if _is_missing(value):
        raise ValueError("precio unitario nulo o vacío")
    if isinstance(value, (int, float)):
        amount = float(value)
        if math.isfinite(amount):
            return amount
        raise ValueError(f"monto no finito: {value!r}")

    text = str(value).strip().upper()
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()").replace("CLP", "").replace("$", "").replace(" ", "")
    text = re.sub(r"[^0-9,.\-+]", "", text)
    if not text or not re.search(r"\d", text):
        raise ValueError(f"monto inválido: {value!r}")
    if "," in text and "." in text:
        decimal_separator = "," if text.rfind(",") > text.rfind(".") else "."
        grouping_separator = "." if decimal_separator == "," else ","
        text = text.replace(grouping_separator, "")
        text = text.replace(decimal_separator, ".")
    elif "," in text or "." in text:
        separator = "," if "," in text else "."
        pieces = text.split(separator)
        if len(pieces) > 2:
            is_decimal = len(pieces[-1]) in (1, 2)
            text = "".join(pieces[:-1]) + (
                "." + pieces[-1] if is_decimal else pieces[-1]
            )
        elif len(pieces[-1]) in (1, 2):
            text = pieces[0] + "." + pieces[1]
        else:
            text = "".join(pieces)
    try:
        amount = float(text)
    except ValueError as error:
        raise ValueError(f"monto inválido: {value!r}") from error
    if negative:
        amount = -abs(amount)
    if not math.isfinite(amount):
        raise ValueError(f"monto no finito: {value!r}")
    return amount


def _parse_units(value: Any) -> int:
    if _is_missing(value):
        raise ValueError("unidades nulas o vacías")
    try:
        numeric = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError) as error:
        raise ValueError(f"unidades inválidas: {value!r}") from error
    if not math.isfinite(numeric) or not numeric.is_integer():
        raise ValueError(f"unidades deben ser un entero: {value!r}")
    return int(numeric)


def _load_workbook(name: str, content: bytes | Path) -> pd.DataFrame:
    if isinstance(content, Path):
        return pd.read_excel(content, engine="openpyxl")
    return pd.read_excel(io.BytesIO(content), engine="openpyxl")


def _catalog_from_frame(frame: pd.DataFrame, name: str) -> dict[str, float] | None:
    record_columns = {_normalized_column(column) for column in frame.columns}
    mapped = {ALIASES.get(column) for column in record_columns}
    if "sku" not in mapped or "costo_unitario" not in mapped:
        return None

    costs: dict[str, float] = {}
    for row_number, row in enumerate(frame.to_dict(orient="records"), start=2):
        values = _canonical_record(row)
        try:
            sku = normalize_sku(values.get("sku"))
            cost = parse_amount(values.get("costo_unitario"))
        except ValueError as error:
            raise ValueError(
                f"Catálogo {name}, fila {row_number}: {error}"
            ) from error
        costs[sku] = cost
    return costs


def _error_text(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
        for item in error.errors()
    )


def run_pipeline(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    uploaded_files: Sequence[tuple[str, bytes]] | None = None,
) -> dict[str, Any]:
    """Run the full pipeline and persist the clean workbook and anomaly audit."""
    if uploaded_files is None:
        workbook_sources: list[tuple[str, bytes | Path]] = [
            (path.name, path)
            for path in sorted(input_dir.glob("*.xlsx"))
            if path.is_file()
        ]
    else:
        workbook_sources = [(name, content) for name, content in uploaded_files]

    if not workbook_sources:
        raise FileNotFoundError(f"No se encontraron archivos Excel en {input_dir}")

    loaded = [(name, _load_workbook(name, source)) for name, source in workbook_sources]
    cost_catalog: dict[str, float] | None = None
    sales_sources: list[tuple[str, pd.DataFrame]] = []
    for name, frame in loaded:
        catalog = _catalog_from_frame(frame, name)
        if catalog is not None:
            cost_catalog = catalog
        else:
            sales_sources.append((name, frame))

    if uploaded_files is not None and cost_catalog is None:
        fallback_catalog = input_dir / "catalogo_costos_maestro.xlsx"
        if fallback_catalog.exists():
            fallback_frame = _load_workbook(
                fallback_catalog.name, fallback_catalog
            )
            cost_catalog = _catalog_from_frame(fallback_frame, fallback_catalog.name)
    if cost_catalog is None:
        raise ValueError(
            "No se encontró un catálogo con columnas SKU y Costo Unitario."
        )
    if not sales_sources:
        raise ValueError("No se encontraron planillas de ventas para procesar.")

    anomalies: list[dict[str, Any]] = []
    clean_rows: list[dict[str, Any]] = []
    total_rows = 0
    duplicates = 0
    normalized_ids = 0
    quarantined = 0

    for filename, frame in sales_sources:
        total_rows += len(frame)
        duplicate_mask = frame.duplicated(keep="first")
        for index, row in frame.iterrows():
            row_number = int(index) + 2
            if bool(duplicate_mask.loc[index]):
                duplicates += 1
                anomalies.append(
                    {
                        "tipo": "duplicado",
                        "severidad": "advertencia",
                        "archivo": filename,
                        "fila": row_number,
                        "id_tributario": None,
                        "sku": None,
                        "motivo": "Fila exacta duplicada; se conserva la primera aparición.",
                    }
                )
                continue

            source = _canonical_record(row.to_dict())
            raw_id = source.get("id_tributario")
            rut: str | None = None
            sku: str | None = None
            try:
                rut = normalize_tax_id(raw_id)
                sku = normalize_sku(source.get("sku"))
                parsed_date = parse_mixed_date(source.get("fecha"))
                unit_price = parse_amount(source.get("precio_unitario"))
                units = _parse_units(source.get("unidades"))
                branch = source.get("sucursal")
                if _is_missing(branch):
                    branch = Path(filename).stem.replace("ventas_sucursal_", "")
                customer = source.get("cliente")
                seller = source.get("vendedor")
                normalized = SalesRow.model_validate(
                    {
                        "fecha": parsed_date,
                        "sucursal": str(branch).strip(),
                        "cliente": (
                            ""
                            if _is_missing(customer)
                            else re.sub(r"\s+", " ", str(customer)).strip().title()
                        ),
                        "id_tributario": rut,
                        "sku": sku,
                        "unidades": units,
                        "precio_unitario": unit_price,
                        "vendedor": "" if _is_missing(seller) else str(seller).strip(),
                    }
                )
                if sku not in cost_catalog:
                    raise ValueError(f"SKU {sku} no existe en el catálogo de costos")
            except ValidationError as error:
                quarantined += 1
                anomalies.append(
                    {
                        "tipo": "fila_en_cuarentena",
                        "severidad": "crítica",
                        "archivo": filename,
                        "fila": row_number,
                        "id_tributario": rut,
                        "sku": sku,
                        "motivo": _error_text(error),
                    }
                )
                continue
            except ValueError as error:
                quarantined += 1
                anomalies.append(
                    {
                        "tipo": "fila_en_cuarentena",
                        "severidad": "crítica",
                        "archivo": filename,
                        "fila": row_number,
                        "id_tributario": (
                            None if _is_missing(raw_id) else str(raw_id)
                        ),
                        "sku": (
                            None
                            if _is_missing(source.get("sku"))
                            else str(source.get("sku"))
                        ),
                        "motivo": str(error),
                    }
                )
                continue

            if str(raw_id).strip().upper() != normalized.id_tributario:
                normalized_ids += 1
                anomalies.append(
                    {
                        "tipo": "id_normalizado",
                        "severidad": "informativa",
                        "archivo": filename,
                        "fila": row_number,
                        "id_tributario": normalized.id_tributario,
                        "sku": normalized.sku,
                        "motivo": f"ID estandarizado de {raw_id!r} a {normalized.id_tributario}.",
                    }
                )

            cost = cost_catalog[normalized.sku]
            net_sales = normalized.precio_unitario * normalized.unidades
            total_cost = cost * normalized.unidades
            gross_margin = net_sales - total_cost
            if gross_margin < 0:
                anomalies.append(
                    {
                        "tipo": "margen_negativo",
                        "severidad": "advertencia",
                        "archivo": filename,
                        "fila": row_number,
                        "id_tributario": normalized.id_tributario,
                        "sku": normalized.sku,
                        "motivo": (
                            f"Margen bruto negativo: {gross_margin:,.2f}; "
                            "la venta se conserva para el análisis."
                        ),
                    }
                )
            clean_rows.append(
                {
                    **normalized.model_dump(),
                    "costo_unitario": cost,
                    "ventas_netas": net_sales,
                    "costo_total": total_cost,
                    "margen_bruto": gross_margin,
                    "archivo_origen": filename,
                }
            )

    sales = pd.DataFrame(clean_rows, columns=OUTPUT_COLUMNS)
    anomalies_frame = pd.DataFrame(anomalies, columns=ANOMALY_COLUMNS)
    metrics = {
        "filas_procesadas": total_rows,
        "duplicados_eliminados": duplicates,
        "ids_normalizados": normalized_ids,
        "filas_en_cuarentena": quarantined,
        "filas_limpias": len(sales),
    }
    kpis = calculate_kpis(sales)

    output_dir.mkdir(parents=True, exist_ok=True)
    clean_path = output_dir / "reporte_gerencial_limpio.xlsx"
    audit_path = output_dir / "auditoria_calidad.xlsx"
    with pd.ExcelWriter(clean_path, engine="openpyxl") as writer:
        sales.to_excel(writer, sheet_name="ventas_limpias", index=False)
        for sheet, table in kpis.items():
            table.to_excel(writer, sheet_name=sheet[:31], index=False)
    with pd.ExcelWriter(audit_path, engine="openpyxl") as writer:
        anomalies_frame.to_excel(writer, sheet_name="anomalias", index=False)
        pd.DataFrame(
            [{"metrica": key, "valor": value} for key, value in metrics.items()]
        ).to_excel(writer, sheet_name="metricas", index=False)

    return {
        "sales": sales,
        "anomalies": anomalies_frame,
        "metrics": metrics,
        "kpis": kpis,
        "clean_path": clean_path,
        "audit_path": audit_path,
    }


if __name__ == "__main__":
    result = run_pipeline()
    print(
        "Pipeline completado: "
        f"{result['metrics']['filas_limpias']} filas limpias, "
        f"{result['metrics']['filas_en_cuarentena']} en cuarentena."
    )
