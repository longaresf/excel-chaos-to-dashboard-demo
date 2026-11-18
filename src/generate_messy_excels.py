"""Generate deterministic, intentionally inconsistent Excel workbooks."""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data" / "dirty_input"


def _sales_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = random.Random(42)
    north = [
        {
            "Fecha": "05/01/2025",
            "Cliente": "  almacenes del valle ",
            "ID_Tributario": "12.345.678-9",
            "Producto": " SKU-001 ",
            "Unidades": 12,
            "Precio Unitario": "$1.250",
            "Vendedor": "Equipo Norte A",
            "Sucursal": "Norte",
        },
        {
            "Fecha": "2025-01-18",
            "Cliente": "COMERCIAL ANDINA",
            "ID_Tributario": "9.876.543-K",
            "Producto": "SKU 002",
            "Unidades": 5,
            "Precio Unitario": "$8.900",
            "Vendedor": "Equipo Norte B",
            "Sucursal": "Norte",
        },
        {
            "Fecha": "fin de enero",
            "Cliente": "Tienda Central",
            "ID_Tributario": "15.222.111-3",
            "Producto": "SKU-003",
            "Unidades": 3,
            "Precio Unitario": "$ 12.500",
            "Vendedor": "Equipo Norte A",
            "Sucursal": "Norte",
        },
        {
            "Fecha": "12/02/2025",
            "Cliente": "  Mercado   Uno ",
            "ID_Tributario": "12.345.678-9",
            "Producto": "SKU-001",
            "Unidades": 8,
            "Precio Unitario": "$1.100",
            "Vendedor": "Equipo Norte B",
            "Sucursal": "Norte",
        },
    ]
    north[1]["Cliente"] = "".join(
        char.upper() if rng.random() > 0.5 else char.lower()
        for char in north[1]["Cliente"]
    )
    north.append(north[0].copy())

    south = [
        {
            "Fecha Venta": "2025-01-09",
            "Cliente": "Distribuidora del Sur",
            "Cliente_RUT": "123456789",
            "SKU": "SKU 001",
            "Cantidad": 15,
            "Precio Unitario": "$1,050.00",
            "Ejecutivo": "Equipo Sur A",
            "Sucursal": "Sur",
        },
        {
            "Fecha Venta": "14/02/2025",
            "Cliente": "  Bazar Austral ",
            "Cliente_RUT": "7.654.321-K",
            "SKU": " SKU-002 ",
            "Cantidad": 4,
            "Precio Unitario": "$7.500",
            "Ejecutivo": "Equipo Sur B",
            "Sucursal": "Sur",
        },
        {
            "Fecha Venta": "2025-02-20",
            "Cliente": "Comercial Horizonte",
            "Cliente_RUT": "18.111.222-4",
            "SKU": "SKU-003",
            "Cantidad": 2,
            "Precio Unitario": "$11.000",
            "Ejecutivo": "Equipo Sur A",
            "Sucursal": "Sur",
        },
        {
            "Fecha Venta": "2025-02-25",
            "Cliente": "Cliente sin identificación",
            "Cliente_RUT": None,
            "SKU": "SKU-001",
            "Cantidad": 6,
            "Precio Unitario": "$1.300",
            "Ejecutivo": "Equipo Sur B",
            "Sucursal": "Sur",
        },
        {
            "Fecha Venta": "28/02/2025",
            "Cliente": "Datos incompletos",
            "Cliente_RUT": "11.222.333-4",
            "SKU": "SKU-002",
            "Cantidad": None,
            "Precio Unitario": "$7.900",
            "Ejecutivo": "Equipo Sur A",
            "Sucursal": "Sur",
        },
    ]
    return pd.DataFrame(north), pd.DataFrame(south)


def generate_files(
    output_dir: Path = DEFAULT_OUTPUT_DIR, *, force: bool = False
) -> list[Path]:
    """Create the three demo workbooks, preserving existing files by default."""
    output_dir.mkdir(parents=True, exist_ok=True)
    north, south = _sales_data()
    catalog = pd.DataFrame(
        [
            {"SKU": " SKU-001 ", "Costo Unitario": "$700"},
            {"SKU": "SKU 002", "Costo Unitario": "$8.100"},
            {"SKU": "SKU-003 ", "Costo Unitario": "$9.000"},
        ]
    )
    workbooks = {
        "ventas_sucursal_norte.xlsx": north,
        "ventas_sucursal_sur.xlsx": south,
        "catalogo_costos_maestro.xlsx": catalog,
    }

    paths = []
    for filename, frame in workbooks.items():
        path = output_dir / filename
        if force or not path.exists():
            frame.to_excel(path, index=False)
        paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--force", action="store_true", help="Replace existing generated workbooks."
    )
    args = parser.parse_args()
    for path in generate_files(args.output_dir, force=args.force):
        print(path)


if __name__ == "__main__":
    main()
