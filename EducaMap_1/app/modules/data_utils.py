# NOTE: Popula o banco de dados conforme SQLAlchemy --> model.py

from pathlib import Path  # Garantindo a importação do Path para a busca recursiva
import re
import os
import pandas as pd
from sqlalchemy import text
from app.utils.model import engine

try:
    import geopandas as gpd
except ImportError:
    gpd = None


def get_calculated_radius(porte):
    porte = str(porte).upper()
    if "PEQUENO" in porte:
        return 500
    elif "MÉDIO" in porte or "MEDIO" in porte:
        return 1000
    elif "GRANDE" in porte:
        return 2000
    else:
        return 3000


def extract_maximum_capacity_weight(value: object) -> float:
    if pd.isna(value):
        return 0.0
    text_str = str(value).strip().lower()
    if "sem matrícula" in text_str or "sem matricula" in text_str:
        return 0.0
    numbers = [int(n) for n in re.findall(r"\d+", text_str)]
    if not numbers:
        return 0.0
    max_val = max(numbers)
    if max_val <= 50:
        return 50.0
    elif max_val <= 200:
        return 200.0
    elif max_val <= 500:
        return 500.0
    elif max_val <= 1000:
        return 1000.0
    else:
        return 1001.0


def resolve_municipio_column(df: pd.DataFrame) -> str | None:
    """Detecta dinamicamente a coluna de município no dataframe."""
    possible_cols = ["Município", "Municipio", "municipio"]
    for col in possible_cols:
        if col in df.columns:
            return col
    return None


def setup_spatial_database():
    """Garante que a extensão espacial do PostGIS está ativa no banco."""
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.commit()
    print("✓ Extensão PostGIS verificada/ativada com sucesso.")


# def load_inicial_data() -> None:
#     """Carrega o arquivo CSV tradicional de escolas."""
#     setup_spatial_database()
#
#     csv_path = Path("listaEscolasDFInep.csv")
#     if not csv_path.exists():
#         print(f"Erro: Arquivo {csv_path} nao encontrado.")
#         return
#
#     try:
#         with engine.connect() as conn:
#             conn.execute(text("TRUNCATE TABLE resultados CASCADE;"))
#             conn.execute(text("TRUNCATE TABLE escolas CASCADE;"))
#             conn.commit()
#
#         df = pd.read_csv(csv_path)
#         # df["capacity_weight"] = df["Porte da Escola"].apply(
#         #     extract_maximum_capacity_weight
#         # )
#
#         df_escolas = df.copy().rename(
#             columns={
#                 "Código INEP": "id_escola",
#                 "Escola": "nome_escola",
#                 "Endereço": "endereco",
#                 "Latitude": "latitude",
#                 "Longitude": "longitude",
#                 "Dependência Administrativa": "tipo_rede",
#                 "Localização": "localizacao",
#                 "Porte da Escola": "porte_escola",
#                 "Etapas e Modalidade de Ensino Oferecidas": "modalidade_ensino",
#             }
#         )
#
#         valid_columns = [
#             "id_escola",
#             "nome_escola",
#             "endereco",
#             "latitude",
#             "longitude",
#             "tipo_rede",
#             "localizacao",
#             "porte_escola",
#             "modalidade_ensino",
#             "capacity_weight",
#         ]
#         df_escolas = df_escolas[valid_columns]
#
#         df_escolas.to_sql("escolas", engine, if_exists="append", index=False)
#
#         resultados_data = []
#         for _, row in df.iterrows():
#             resultados_data.append(
#                 {
#                     "id_escola": row["Código INEP"],
#                     "capacidade_matricula": extract_maximum_capacity_weight(
#                         row["Porte da Escola"]
#                     ),
#                 }
#             )
#
#         df_resultados = pd.DataFrame(resultados_data)
#         df_resultados.to_sql("resultados", engine, if_exists="append", index=False)
#
#         print("✓ Banco de dados (CSV) populado com sucesso!")
#     except Exception as e:
#         print(f"Erro ao popular banco com CSV: {e}")


def load_inicial_data() -> None:
    """Carrega o arquivo CSV de escolas tratando delimitadores (vírgula ou ponto e vírgula)."""
    setup_spatial_database()

    csv_path = Path("listaEscolasDFInep.csv")
    if not csv_path.exists():
        print(f"Erro: Arquivo {csv_path} nao encontrado.")
        return

    try:
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE resultados CASCADE;"))
            conn.execute(text("TRUNCATE TABLE escolas CASCADE;"))
            conn.commit()

        # Tenta ler primeiro com o separador padrão ','
        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        # Se o Pandas leu tudo como uma única coluna, significa que o separador real é ';'
        if len(df.columns) <= 1:
            df = pd.read_csv(csv_path, sep=";", encoding="utf-8-sig")

        # Limpa espaços em branco invisíveis nas pontas dos nomes das colunas
        df.columns = df.columns.str.strip()

        coluna_alvo = "Porte da Escola"
        if coluna_alvo not in df.columns:
            print(f"\n[ERRO CRÍTICO] A coluna '{coluna_alvo}' não foi encontrada.")
            print(f"Colunas detectadas no seu CSV: {list(df.columns)}\n")
            raise KeyError(f"Coluna '{coluna_alvo}' ausente no arquivo CSV.")

        df["capacity_weight"] = df[coluna_alvo].apply(extract_maximum_capacity_weight)

        df_escolas = df.copy().rename(
            columns={
                "Código INEP": "id_escola",
                "Escola": "nome_escola",
                "Endereço": "endereco",
                "Latitude": "latitude",
                "Longitude": "longitude",
                "Dependência Administrativa": "tipo_rede",
                "Localização": "localizacao",
                "Porte da Escola": "porte_escola",
                "Etapas e Modalidade de Ensino Oferecidas": "modalidade_ensino",
            }
        )

        valid_columns = [
            "id_escola",
            "nome_escola",
            "endereco",
            "latitude",
            "longitude",
            "tipo_rede",
            "localizacao",
            "porte_escola",
            "modalidade_ensino",
            "capacity_weight",
        ]
        columns_to_keep = [col for col in valid_columns if col in df_escolas.columns]
        df_escolas = df_escolas[columns_to_keep]

        df_escolas.to_sql("escolas", engine, if_exists="append", index=False)

        # Populando a tabela de resultados com segurança
        resultados_data = []
        for _, row in df.iterrows():
            resultados_data.append(
                {
                    "id_escola": row["Código INEP"],
                    "capacidade_matricula": extract_maximum_capacity_weight(
                        row["Porte da Escola"]
                    ),
                }
            )

        df_resultados = pd.DataFrame(resultados_data)
        df_resultados.to_sql("resultados", engine, if_exists="append", index=False)

        print("✓ Banco de dados (CSV) populado com sucesso!")
    except Exception as e:
        print(f"Erro ao popular banco com CSV: {e}")


def load_data_from_postgres() -> pd.DataFrame:
    query = "SELECT * FROM escolas"
    df = pd.read_sql(query, engine)
    return df.rename(
        columns={
            "id_escola": "Código INEP",
            "nome_escola": "Escola",
            "endereco": "Endereço",
            "latitude": "Latitude",
            "longitude": "Longitude",
            "tipo_rede": "Dependência Administrativa",
            "localizacao": "Localização",
            "porte_escola": "Porte da Escola",
            "modalidade_ensino": "Etapas e Modalidade de Ensino Oferecidas",
        }
    )


def carregar_shapefile_generico(caminho_shp: str, nome_tabela: str) -> bool:
    """
    Lê um dos 9 Shapefiles com GeoPandas, normaliza a projeção
    para EPSG:4326 (WGS 84) e injeta via SQLAlchemy no PostGIS.
    """
    if gpd is None:
        print(
            f"Erro: GeoPandas não instalado. Não foi possível carregar {nome_tabela}."
        )
        return False

    if not os.path.exists(caminho_shp):
        print(
            f"Aviso: Arquivo '{os.path.basename(caminho_shp)}' não encontrado. Pulando..."
        )
        return False

    try:
        print(f"Processando Shapefile: {nome_tabela}...")
        gdf = gpd.read_file(caminho_shp)

        if gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs(epsg=4326)

        if "geometry" in gdf.columns:
            gdf = gdf.rename_geometry("geom")

        gdf.to_postgis(name=nome_tabela, con=engine, if_exists="replace", index=False)
        print(f"✓ Sucesso: Tabela '{nome_tabela}' integrada ao PostGIS.")
        return True
    except Exception as e:
        print(f"Erro crítico ao processar o Shapefile {nome_tabela}: {e}")
        return False


# --- BLOCO DE EXECUÇÃO E AUTOMAÇÃO INTEGRADA RECURSIVA ---
if __name__ == "__main__":
    print("\n=== INICIANDO PIPELINE DE CARGA DE DADOS ===")

    # 1. População tradicional de Escolas (CSV)
    load_inicial_data()

    # 2. Mapeamento exato dos 9 Shapefiles esperados e seus respectivos nomes de tabela
    shapefiles_alvo = {
        "equipamentos_de_saude.shp": "equipamentos_de_saude",
        "equipamentos_de_seguranca.shp": "equipamentos_de_seguranca",
        "espacos_comunitarios.shp": "espacos_comunitarios",
        "espacos_culturais.shp": "espacos_culturais",
        "feiras_livres.shp": "feiras_livres",
        "mobiliario_esporte_e_lazer.shp": "mobiliario_esporte_e_lazer",
        "parques_urbanos.shp": "parques_urbanos",
        "limite_do_distrito_federal.shp": "limite_do_distrito_federal",
        "regioes_administrativas.shp": "regioes_administrativas",
    }

    pasta_raiz_dados = Path("data/raw")

    if not pasta_raiz_dados.exists():
        print(f"Erro: A pasta raiz '{pasta_raiz_dados}' não existe no projeto.")
    else:
        print(f"Iniciando varredura RECURSIVA dentro de '{pasta_raiz_dados}'...")

        arquivos_encontrados = {}

        for caminho_arquivo in pasta_raiz_dados.rglob("*.shp"):
            nome_arquivo_shp = caminho_arquivo.name
            arquivos_encontrados[nome_arquivo_shp] = str(caminho_arquivo)

        contagem_sucesso = 0
        for arquivo_alvo, nome_tabela in shapefiles_alvo.items():
            if arquivo_alvo in arquivos_encontrados:
                caminho_real = arquivos_encontrados[arquivo_alvo]
                print(f"\n[Encontrado] -> {arquivo_alvo} em: {caminho_real}")

                sucesso = carregar_shapefile_generico(caminho_real, nome_tabela)
                if sucesso:
                    contagem_sucesso += 1
            else:
                print(
                    f"\n[Aviso] Arquivo '{arquivo_alvo}' não foi localizado em nenhuma subpasta de '{pasta_raiz_dados}'."
                )

        print(
            f"\n=== PIPELINE FINALIZADO: {contagem_sucesso} de {len(shapefiles_alvo)} Shapefiles carregados com sucesso! ===\n"
        )


def resolve_csv_path() -> str:
    """
    Função de compatibilidade restaurada para o frontend.
    Retorna o caminho estável do CSV de escolas esperado pelo projeto.
    """
    caminhos_possiveis = [
        Path("listaEscolasDFInep.csv"),
        Path("data/raw/listaEscolasDFInep.csv"),
        Path("app/data/listaEscolasDFInep.csv"),
    ]
    for caminho in caminhos_possiveis:
        if caminho.exists():
            return str(caminho)

    # Caso não ache em lugar nenhum, retorna o padrão esperado na raiz
    return "listaEscolasDFInep.csv"


# --- ALIAS DE COMPATIBILIDADE COM O FRONTEND ---
# Caso alguma parte antiga do código tente chamar por este nome antigo:
load_school_data = load_data_from_postgres
