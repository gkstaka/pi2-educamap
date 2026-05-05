# NOTE: Popula o banco de dados conforme SQLAlchemy --> model.py

from pathlib import Path
import re
import pandas as pd
from sqlalchemy import text
from app.utils.model import engine

# TODO: Rever essa metodologia se baseando no "workability"
def get_calculated_radius(porte):
    porte = str(porte).upper()
    if "PEQUENO" in porte: return 500
    elif "MÉDIO" in porte or "MEDIO" in porte: return 1000
    elif "GRANDE" in porte: return 2000
    else: return 3000


def extract_maximum_capacity_weight(value: object) -> float:
    """
    Extrai a capacidade baseada em faixas fixas de matrícula:
    - Até 50 -> 50
    - 51 a 200 -> 200
    - 201 a 500 -> 500
    - 501 a 1000 -> 1000
    - Mais de 1000 -> 1001
    - Sem matrícula -> 0
    """
    if pd.isna(value):
        return 0.0

    text_str = str(value).strip().lower()
    
    # Caso específico para escolas sem matrícula
    if "sem matrícula" in text_str or "sem matricula" in text_str:
        return 0.0

    # Extração de todos os números presentes na string
    numbers = [int(n) for n in re.findall(r"\d+", text_str)]
    
    if not numbers:
        return 0.0

    # Lógica baseada nos limites superiores das faixas informadas
    if "mais de 1000" in text_str:
        return 1001.0
    
    if "até 50" in text_str or 50 in numbers:
        return 50.0
    
    if 200 in numbers:
        return 200.0
    
    if 500 in numbers:
        return 500.0
    
    if 1000 in numbers:
        return 1000.0

    # Fallback: retorna o maior número encontrado ou 0
    return float(max(numbers)) if numbers else 0.0


def extract_capacity_weight(value: object) -> float | None:
    #NOTE:Extrai um valor representativo de matrículas do texto de porte da escola.
    if pd.isna(value):
        return None

    text_str = str(value).strip()
    if not text_str:
        return None

    numbers = [float(n) for n in re.findall(r"\d+", text_str)]
    if not numbers:
        return None

    lowered = text_str.lower()

    if len(numbers) >= 2 and "entre" in lowered:
        return sum(numbers[:2]) / 2

    if "até" in lowered or "ate" in lowered:
        return numbers[0] / 2

    if "mais de" in lowered:
        return numbers[0] + max(250.0, numbers[0] * 0.25)

    return float(max(numbers))


@pd.api.extensions.register_dataframe_accessor("educamap")
class _EducaMapAccessor:
    """Namespace para auxiliares vinculados ao dataframe de escolas."""
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
    """Carrega e limpa os dados do CSV."""
    df = pd.read_csv(csv_file)
    df = df.educamap.with_coordinates()

    if "Porte da Escola" in df.columns:
        df["capacity_weight"] = df["Porte da Escola"].apply(extract_capacity_weight)
    else:
        df["capacity_weight"] = pd.NA

    return df


def resolve_csv_path(project_root: Path) -> Path:
    """Localiza o arquivo CSV no projeto dentro do ambiente Docker."""
    # Como definimos WORKDIR /EducaMap no Dockerfile, o arquivo estará na raiz
    candidate = Path("/EducaMap/listaEscolasDFInep.csv")
    
    if candidate.exists():
        return candidate
    
    # Fallback para execução local fora do Docker
    return project_root / "listaEscolasDFInep.csv"


def resolve_municipio_column(df: pd.DataFrame) -> str | None:
    if "Municipio" in df.columns: return "Municipio"
    if "Município" in df.columns: return "Município"
    return None

# WARNING: --- FUNÇÕES DE INTERAÇÃO COM O BANCO DE DADOS ---


def load_inicial_data():
    """Lê o CSV e popula o banco de dados PostgreSQL."""
    try:
        project_root = Path(__file__).resolve().parent.parent
        csv_path = resolve_csv_path(project_root)
        
        print(f"Lendo dados de: {csv_path}")
        df = load_school_data(csv_path)

        # ---- LIMPEZA MANUAL DAS TABELAS ----
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE resultados CASCADE;"))
            conn.execute(text("TRUNCATE TABLE escolas CASCADE;"))
            conn.commit()

        # Mapeamento para o banco de dados
        df_escolas = df[[
                'Código INEP', 'Escola', 'Endereço', 'Latitude', 'Longitude', 
            'Dependência Administrativa', 'Localização', 'Porte da Escola', 
            'Etapas e Modalidade de Ensino Oferecidas', 'capacity_weight'
        ]].rename(columns={
            'Código INEP': 'id_escola',
            'Escola': 'nome_escola',
            'Endereço': 'endereco',
            'Latitude': 'latitude',
            'Longitude': 'longitude',
            'Dependência Administrativa': 'tipo_rede',
            'Localização': 'localizacao',
            'Porte da Escola': 'porte_escola',
            'Etapas e Modalidade de Ensino Oferecidas': 'modalidade_ensino'
        })
        
        df_escolas.to_sql('escolas', engine, if_exists='append', index=False)

        resultados_data = []
        for _, row in df.iterrows():
            resultados_data.append({
                'id_escola': row['Código INEP'],
                # 'raio_calculado': get_calculated_radius(row['Porte da Escola']),
                'capacidade_matricula': extract_maximum_capacity_weight(row['Porte da Escola'])
            })

        df_resultados = pd.DataFrame(resultados_data)
        df_resultados.to_sql('resultados', engine, if_exists='append', index=False)

        print("Banco de dados populado com sucesso!")
    except Exception as e:
        print(f"Erro ao popular banco: {e}")


def load_data_from_postgres() -> pd.DataFrame:
    """Lê os dados do banco e retorna no formato esperado pelo main.py."""
    query = "SELECT * FROM escolas"
    df = pd.read_sql(query, engine)
    
    # Mapeamento reverso para manter compatibilidade com o frontend
    df = df.rename(columns={
        'id_escola': 'Código INEP',
        'nome_escola': 'Escola',
        'endereco': 'Endereço',
        'latitude': 'Latitude',
        'longitude': 'Longitude',
        'tipo_rede': 'Dependência Administrativa',
        'localizacao': 'Localização',
        'porte_escola': 'Porte da Escola',
        'modalidade_ensino': 'Etapas e Modalidade de Ensino Oferecidas'
    })
    return df


if __name__ == "__main__":
    load_inicial_data()
