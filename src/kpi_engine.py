"""Business metrics derived from validated and cost-enriched sales."""

from __future__ import annotations

import pandas as pd


def calculate_kpis(sales: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build the tables used by the dashboard and the Excel management report."""
    branch_columns = ["sucursal", "ventas_netas", "costo_total", "margen_bruto"]
    seller_columns = ["vendedor", "ventas_netas", "margen_bruto"]
    product_columns = ["sku", "ventas_netas", "margen_bruto", "unidades"]

    if sales.empty:
        return {
            "sucursal": pd.DataFrame(columns=branch_columns),
            "vendedor": pd.DataFrame(columns=seller_columns),
            "mensual": pd.DataFrame(
                columns=["mes", "ventas_netas", "margen_bruto"]
            ),
            "producto": pd.DataFrame(columns=product_columns),
        }

    branch = (
        sales.groupby("sucursal", as_index=False)[
            ["ventas_netas", "costo_total", "margen_bruto"]
        ]
        .sum()
        .sort_values("ventas_netas", ascending=False)
    )
    seller = (
        sales.groupby("vendedor", as_index=False)[["ventas_netas", "margen_bruto"]]
        .sum()
        .sort_values("ventas_netas", ascending=False)
    )
    monthly_sales = sales.assign(
        mes=pd.to_datetime(sales["fecha"]).dt.to_period("M").dt.to_timestamp()
    )
    monthly = (
        monthly_sales.groupby("mes", as_index=False)[
            ["ventas_netas", "margen_bruto"]
        ]
        .sum()
        .sort_values("mes")
    )
    products = (
        sales.groupby("sku", as_index=False)[
            ["ventas_netas", "margen_bruto", "unidades"]
        ]
        .sum()
        .sort_values("ventas_netas", ascending=False)
    )
    return {
        "sucursal": branch,
        "vendedor": seller,
        "mensual": monthly,
        "producto": products,
    }
