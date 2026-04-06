from pathlib import Path
import re

import pandas as pd


def extract_capacity_weight(value: object) -> float | None:
    """Extract the maximum numeric value from enrollment-capacity text."""
    if pd.isna(value):
        return None

    text = str(value).strip()
    if not text:
        return None

    numbers = [int(n) for n in re.findall(r"\d+", text)]
    if not numbers:
        return None

    return float(max(numbers))


def resolve_csv_path(base_dir: Path) -> Path:
    """Find the schools CSV path from common project locations."""
    candidates = [
        base_dir / "tests" / "Analise-Tabela_da_lista_das_escolas-Detalhado.csv",
        base_dir / "Analise-Tabela_da_lista_das_escolas-Detalhado.csv",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


@pd.api.extensions.register_dataframe_accessor("educamap")
class _EducaMapAccessor:
    """Simple namespace for helpers tied to the schools dataframe."""

    def __init__(self, pandas_obj: pd.DataFrame):
        self._obj = pandas_obj

    def with_coordinates(self) -> pd.DataFrame:
        df = self._obj.copy()
        for col in ["Latitude", "Longitude"]:
            if col not in df.columns:
                raise ValueError(f"Coluna obrigatoria ausente: {col}")

        df["Latitude"] = pd.to_numeric(
            df["Latitude"].astype(str).str.replace(",", ".", regex=False).str.strip(),
            errors="coerce",
        )
        df["Longitude"] = pd.to_numeric(
            df["Longitude"].astype(str).str.replace(",", ".", regex=False).str.strip(),
            errors="coerce",
        )

        return df.dropna(subset=["Latitude", "Longitude"]).copy()


def load_school_data(csv_file: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_file)
    df = df.educamap.with_coordinates()

    if "Porte da Escola" in df.columns:
        df["capacity_weight"] = df["Porte da Escola"].apply(extract_capacity_weight)
    else:
        df["capacity_weight"] = pd.NA

    return df


def resolve_municipio_column(df: pd.DataFrame) -> str | None:
    if "Municipio" in df.columns:
        return "Municipio"
    if "Município" in df.columns:
        return "Município"
    return None
