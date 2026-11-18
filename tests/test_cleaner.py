from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.cleaner_pipeline import (
    normalize_tax_id,
    parse_mixed_date,
    parse_amount,
    run_pipeline,
)


def test_normalize_tax_id_removes_punctuation_and_normalizes_check_digit() -> None:
    assert normalize_tax_id("12.345.678-k") == "12345678K"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("05/01/2025", "2025-01-05"),
        ("2025-01-05", "2025-01-05"),
        ("31/02/2025", None),
    ],
)
def test_parse_mixed_dates(value: str, expected: str | None) -> None:
    if expected is None:
        with pytest.raises(ValueError, match="fecha inválida"):
            parse_mixed_date(value)
    else:
        assert parse_mixed_date(value).isoformat() == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("$1.234,50", 1234.5),
        ("$1,234.50", 1234.5),
        ("$1.250", 1250),
    ],
)
def test_parse_inconsistent_currency_formats(value: str, expected: float) -> None:
    assert parse_amount(value) == expected


def test_pipeline_deduplicates_and_quarantines_critical_rows(
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    valid = {
        "Fecha": "05/01/2025",
        "Cliente": "Cliente Demo",
        "ID_Tributario": "12.345.678-9",
        "Producto": " SKU-001 ",
        "Unidades": 2,
        "Precio Unitario": "$1.250",
        "Vendedor": "Equipo Norte",
        "Sucursal": "Norte",
    }
    sales = pd.DataFrame(
        [
            valid,
            valid.copy(),
            {
                **valid,
                "Fecha": "2025-01-06",
                "ID_Tributario": None,
            },
        ]
    )
    catalog = pd.DataFrame(
        [{"SKU": "SKU 001", "Costo Unitario": "$700"}]
    )
    sales.to_excel(input_dir / "ventas.xlsx", index=False)
    catalog.to_excel(input_dir / "costos.xlsx", index=False)

    result = run_pipeline(input_dir=input_dir, output_dir=output_dir)

    assert result["metrics"] == {
        "filas_procesadas": 3,
        "duplicados_eliminados": 1,
        "ids_normalizados": 1,
        "filas_en_cuarentena": 1,
        "filas_limpias": 1,
    }
    assert result["sales"].iloc[0]["id_tributario"] == "123456789"
    assert result["sales"].iloc[0]["margen_bruto"] == 1100
    assert {"reporte_gerencial_limpio.xlsx", "auditoria_calidad.xlsx"} == {
        path.name for path in output_dir.iterdir()
    }
