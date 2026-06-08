# NOTE: Popula o banco de dados conforme SQLAlchemy --> model.py

from pathlib import Path
import json
import re

from shapely import errors
from shapely.geometry import Point, LineString, MultiLineString
import xml.etree.ElementTree as ET
import requests
import pandas as pd
from sqlalchemy import text
from app.utils.model import engine
import geopandas as gpd


# TODO: Rever essa metodologia se baseando no "workability"
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
    # NOTE:Extrai um valor representativo de matrículas do texto de porte da escola.
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


def load_matriculas_data() -> pd.DataFrame | None:
    """
    Carrega o JSON de matrículas 2023 da rede pública do DF.
    Cada chave é o código da escola (CO_ENTIDADE); cada valor é um registro
    com campos demográficos e totais de matrícula por nível de ensino.
    Retorna None se o arquivo não for encontrado.
    """
    candidates = [
        # Ambiente Docker
        Path("/EducaMap/data/raw/Governanca_educa_df/matriculas_rede_publica_de_ensino_json_2023.json"),
        # Execução local
        Path(__file__).resolve().parent.parent.parent
        / "data/raw/Governanca_educa_df/matriculas_rede_publica_de_ensino_json_2023.json",
    ]

    for path in candidates:
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                df = pd.DataFrame.from_dict(data, orient="index")
                # Converte colunas numéricas relevantes
                numeric_cols = [
                    "MAT_EI_TOTAL", "MAT_EF_INI", "MAT_EF_FIN", "MAT_EF_TOTAL",
                    "MAT_EM_TOTAL", "MAT_EJA_TOTAL", "MAT_EP_TOTAL", "MATRÍCULA",
                    "MAT_CRECHE", "MAT_PRE",
                ]
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                return df
            except Exception as e:
                print(f"[load_matriculas_data] Erro ao carregar JSON: {e}")
                return None

    return None


def resolve_municipio_column(df: pd.DataFrame) -> str | None:
    if "Municipio" in df.columns:
        return "Municipio"
    if "Município" in df.columns:
        return "Município"
    return None


# WARNING: --- FUNÇÕES DE INTERAÇÃO COM O BANCO DE DADOS ---


def load_inicial_data():
    """Lê o CSV e popula o banco de dados PostgreSQL."""

    try:
        with engine.connect() as conn:
            # Se a tabela existir e tiver registros: encerra!
            res = conn.execute(text("SELECT COUNT(*) FROM escolas;")).fetchone()
            if res and res[0] > 0:
                print("[SSD SALVO!] Dados das escolas estão persistidos no banco.")
                return
    except Exception:
        # Se a tabela não existir no primeiro boot, segue o fluxo de criação.
        pass

    try:
        project_root = Path(__file__).resolve().parent.parent
        csv_path = resolve_csv_path(project_root)

        print()
        print("=" * 60)
        print(f"Lendo dados de: {csv_path}")
        df = load_school_data(csv_path)

        # ---- LIMPEZA MANUAL DAS TABELAS ----
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE resultados CASCADE;"))
            conn.execute(text("TRUNCATE TABLE escolas CASCADE;"))
            conn.commit()

        # Mapeamento para o banco de dados
        df_escolas = df[
            [
                "Código INEP",
                "Escola",
                "Endereço",
                "Latitude",
                "Longitude",
                "Dependência Administrativa",
                "Localização",
                "Porte da Escola",
                "Etapas e Modalidade de Ensino Oferecidas",
                "capacity_weight",
            ]
        ].rename(
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

        # Garante que coordenadas em branco seja Nulo/NaN
        df_escolas["latitude"] = pd.to_numeric(df_escolas["latitude"], errors="coerce")
        df_escolas["longitude"] = pd.to_numeric(
            df_escolas["longitude"], errors="coerce"
        )

        df_escolas.to_sql("escolas", engine, if_exists="append", index=False)

        resultados_data = []
        for _, row in df.iterrows():
            resultados_data.append(
                {
                    "id_escola": row["Código INEP"],
                    # 'raio_calculado': get_calculated_radius(row['Porte da Escola']),
                    "capacidade_matricula": extract_maximum_capacity_weight(
                        row["Porte da Escola"]
                    ),
                }
            )

        df_resultados = pd.DataFrame(resultados_data)
        df_resultados.to_sql("resultados", engine, if_exists="append", index=False)

        print("Banco de dados populado com sucesso!")
        print("=" * 60)
    except Exception as e:
        print(f"Erro ao popular banco: {e}")


def load_data_from_postgres() -> pd.DataFrame:
    """Lê os dados do banco e retorna no formato esperado pelo main.py."""
    query = "SELECT * FROM escolas"
    df = pd.read_sql(query, engine)

    # Mapeamento reverso para manter compatibilidade com o frontend
    df = df.rename(
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
    return df


def carregar_shapefile_generico(caminho_shp: str, nome_tabela: str) -> bool:
    """[Mantém Igual] Lê o arquivo com GeoPandas e envia ao PostGIS."""
    if gpd is None:
        print(f"Erro: GeoPandas não instalado para {nome_tabela}.")
        return False
    try:
        print(f"Processando Shapefile: {nome_tabela}...")
        gdf = gpd.read_file(caminho_shp)
        if gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs(epsg=4326)
        if "geometry" in gdf.columns:
            gdf = gdf.rename_geometry("geom")

        gdf.to_postgis(
            name=nome_tabela, con=engine, if_exists="replace", index=False
        )  # ver comando para nao fazer nada do nothing
        print(f"✓ Sucesso: Tabela '{nome_tabela}' integrada ao PostGIS.")
        return True
    except Exception as e:
        print(f"Erro no Shapefile {nome_tabela}: {e}")
        return False


def carregar_camada_transporte_remota() -> bool:
    """
    Busca, via serviço ArcGIS REST do Geoportal IDE-DF (SEDUH), a camada pública
    "Estações e Terminais" — que reúne estações de metrô, BRT e terminais
    DFTrans — e persiste como tabela PostGIS `estacoes_terminais_transporte`.
    Usada para calcular a distância das escolas até o ponto de transporte
    público de alta capacidade mais próximo.
    """
    url = (
        "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/"
        "Publico/IDEDF/MapServer/127/query"
    )
    params = {"where": "1=1", "outFields": "*", "returnGeometry": "true", "f": "geojson"}
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        features = resp.json().get("features", [])
        if not features:
            print("[carregar_camada_transporte_remota] Nenhuma feição retornada pelo serviço.")
            return False

        gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
        gdf = gdf.rename(columns={
            "let_tipo": "tipo",
            "let_nome_estac": "nome",
            "let_situacao": "situacao",
        })
        gdf = gdf.rename_geometry("geom")[["tipo", "nome", "situacao", "geom"]]

        gdf.to_postgis(name="estacoes_terminais_transporte", con=engine, if_exists="replace", index=False)
        print(f"✓ Sucesso: Tabela 'estacoes_terminais_transporte' integrada ao PostGIS ({len(gdf)} feições).")
        return True
    except Exception as e:
        print(f"[carregar_camada_transporte_remota] Erro: {e}")
        return False


def _garantir_camada_transporte() -> None:
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT COUNT(*) FROM estacoes_terminais_transporte;")).fetchone()
            if res and res[0] > 0:
                return
    except Exception:
        pass
    carregar_camada_transporte_remota()


def carregar_camada_onibus_osm() -> bool:
    """
    Lê o extrato local do OpenStreetMap (Overpass API, formato XML) e extrai
    paradas de ônibus (`highway=bus_stop` / `public_transport=platform|stop_position`)
    e linhas de ônibus (relations com `route=bus`), persistindo como tabelas
    PostGIS `paradas_onibus_osm` (pontos) e `linhas_onibus_osm` (linhas).
    """
    caminhos = [
        Path("/EducaMap/data/raw/OverpassAPI"),
        Path(__file__).resolve().parent.parent.parent / "data/raw/OverpassAPI",
    ]
    caminho = next((c for c in caminhos if c.exists()), None)
    if caminho is None:
        print("[carregar_camada_onibus_osm] Arquivo 'OverpassAPI' não encontrado.")
        return False

    try:
        nodes: dict[int, tuple[float, float]] = {}
        ways: dict[int, list[int]] = {}
        paradas = []
        linhas_raw = []

        context = ET.iterparse(str(caminho), events=("start", "end"))
        _, root = next(context)

        cur_kind = cur_id = cur_lat = cur_lon = None
        cur_tags: dict[str, str] = {}
        cur_nds: list[int] = []
        cur_members: list[int] = []

        for event, elem in context:
            tag = elem.tag
            if event == "start":
                if tag in ("node", "way", "relation"):
                    cur_kind = tag
                    cur_id = int(elem.get("id"))
                    cur_tags, cur_nds, cur_members = {}, [], []
                    if tag == "node":
                        cur_lat = float(elem.get("lat"))
                        cur_lon = float(elem.get("lon"))
                continue

            if tag == "tag" and cur_kind is not None:
                cur_tags[elem.get("k")] = elem.get("v")
            elif tag == "nd" and cur_kind == "way":
                cur_nds.append(int(elem.get("ref")))
            elif tag == "member" and cur_kind == "relation" and elem.get("type") == "way":
                cur_members.append(int(elem.get("ref")))
            elif tag == "node":
                nodes[cur_id] = (cur_lon, cur_lat)
                tipo_pt = cur_tags.get("public_transport")
                if cur_tags.get("highway") == "bus_stop" or tipo_pt in ("platform", "stop_position"):
                    paradas.append({
                        "id_osm": cur_id, "nome": cur_tags.get("name"),
                        "tipo": tipo_pt or cur_tags.get("highway"),
                        "ref": cur_tags.get("ref"),
                        "geom": Point(cur_lon, cur_lat),
                    })
                cur_kind = None
            elif tag == "way":
                ways[cur_id] = cur_nds
                cur_kind = None
            elif tag == "relation":
                if cur_tags.get("route") == "bus":
                    linhas_raw.append({
                        "id_osm": cur_id,
                        "nome": cur_tags.get("name"),
                        "ref": cur_tags.get("ref"),
                        "way_ids": list(cur_members),
                    })
                cur_kind = None

            if tag in ("node", "way", "relation"):
                elem.clear()
                root.clear()

        linhas = []
        for lr in linhas_raw:
            segmentos = []
            for wid in lr["way_ids"]:
                nd_ids = ways.get(wid)
                if not nd_ids:
                    continue
                coords = [nodes[n] for n in nd_ids if n in nodes]
                if len(coords) >= 2:
                    segmentos.append(LineString(coords))
            if segmentos:
                linhas.append({
                    "id_osm": lr["id_osm"], "nome": lr["nome"], "ref": lr["ref"],
                    "geom": MultiLineString(segmentos) if len(segmentos) > 1 else segmentos[0],
                })

        if not paradas:
            print("[carregar_camada_onibus_osm] Nenhuma parada de ônibus encontrada no extrato OSM.")
            return False

        gdf_paradas = gpd.GeoDataFrame(paradas, geometry="geom", crs="EPSG:4326")
        gdf_linhas = gpd.GeoDataFrame(linhas, geometry="geom", crs="EPSG:4326")

        gdf_paradas.to_postgis("paradas_onibus_osm", engine, if_exists="replace", index=False)
        gdf_linhas.to_postgis("linhas_onibus_osm", engine, if_exists="replace", index=False)
        print(
            f"✓ Sucesso: 'paradas_onibus_osm' ({len(gdf_paradas)} feições) e "
            f"'linhas_onibus_osm' ({len(gdf_linhas)} feições) integradas ao PostGIS via extrato OSM."
        )
        return True
    except Exception as e:
        print(f"[carregar_camada_onibus_osm] Erro: {e}")
        return False


def _garantir_camada_onibus_osm() -> None:
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT COUNT(*) FROM paradas_onibus_osm;")).fetchone()
            if res and res[0] > 0:
                return
    except Exception:
        pass
    carregar_camada_onibus_osm()


def load_shapefiles_data() -> None:
    """Faz apenas a varredura recursiva dos mapas."""

    try:
        with engine.connect() as conn:
            # Se a tabela existir e possuir dados: encerra!
            res = conn.execute(
                text("SELECT COUNT(*) FROM regioes_administrativas;")
            ).fetchone()
            if res and res[0] > 0:
                print("[SSD SALVO] Shapefiles persistidos no banco.")
                _garantir_camada_transporte()
                _garantir_camada_onibus_osm()
                return
    except Exception:
        # Se não tiver nada, cria o banco e popula com os shapefiles.
        pass

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
        print(f"Aviso: Pasta '{pasta_raiz_dados}' não encontrada. Pulando mapas.")
        return

    print()
    print(f"Iniciando varredura RECURSIVA de Shapefiles em '{pasta_raiz_dados}'...")
    arquivos_encontrados = {
        caminho.name: str(caminho) for caminho in pasta_raiz_dados.rglob("*.shp")
    }

    contagem_sucesso = 0
    for arquivo_alvo, nome_tabela in shapefiles_alvo.items():
        if arquivo_alvo in arquivos_encontrados:
            caminho_real = arquivos_encontrados[arquivo_alvo]
            sucesso = carregar_shapefile_generico(caminho_real, nome_tabela)
            if sucesso:
                contagem_sucesso += 1
        else:
            print(f"[Aviso] Arquivo '{arquivo_alvo}' não encontrado nas subpastas.")

    print(
        f"=== PIPELINE GEOGRÁFICO: {contagem_sucesso} de {len(shapefiles_alvo)} mapas carregados ==="
    )

    _garantir_camada_transporte()
    _garantir_camada_onibus_osm()


def load_ibge_frequencia_data() -> pd.DataFrame:
    """Carrega taxa bruta de frequência escolar por faixa etária (Censo 2022 IBGE)."""
    candidates = [
        Path("/EducaMap/data/raw/Censo_2022_IBGE/indicadores_censo_sem_infomacoes_uteis/Censo 2022 - Taxa bruta de frequência escolar, por grupo de idade - Brasil.csv"),
        Path(__file__).resolve().parent.parent.parent
        / "data/raw/Censo_2022_IBGE/indicadores_censo_sem_infomacoes_uteis/Censo 2022 - Taxa bruta de frequência escolar, por grupo de idade - Brasil.csv",
    ]
    for path in candidates:
        if path.exists():
            try:
                df = pd.read_csv(path, sep=";", encoding="utf-8")
                df.columns = [c.strip() for c in df.columns]
                return df
            except Exception:
                pass

    return pd.DataFrame({
        "Grupo de idade": ["0 a 3 anos", "4 e 5 anos", "6 a 14 anos", "15 a 17 anos", "18 a 24 anos", "25 anos ou mais"],
        "Taxa bruta de frequência escolar (%)": [33.88, 86.73, 98.26, 85.25, 27.68, 6.1],
    })


def load_entorno_por_ra() -> pd.DataFrame | None:
    """
    Conta equipamentos públicos (saúde, segurança, parques, cultura) e escolas dentro
    de cada Região Administrativa via PostGIS ST_Within.
    Retorna totais absolutos + colunas normalizadas por escola (_por_escola) e
    um índice 0-100 (indice_normalizado) calculado via min-max sobre o total.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'regioes_administrativas' "
                "AND data_type NOT IN ('USER-DEFINED') "
                "ORDER BY ordinal_position"
            ))
            all_cols = [row[0] for row in result]

        nome_col = next(
            (c for c in ["nome", "ra_nome", "ra", "NM_RA"] if c in all_cols),
            all_cols[0] if all_cols else "nome",
        )

        query = f"""
        SELECT
            ra.{nome_col} AS ra_nome,
            (SELECT COUNT(*) FROM equipamentos_de_saude s WHERE ST_Within(s.geom, ra.geom))     AS saude,
            (SELECT COUNT(*) FROM equipamentos_de_seguranca s WHERE ST_Within(s.geom, ra.geom)) AS seguranca,
            (SELECT COUNT(*) FROM parques_urbanos p WHERE ST_Within(p.geom, ra.geom))           AS parques,
            (SELECT COUNT(*) FROM espacos_culturais c WHERE ST_Within(c.geom, ra.geom))         AS cultura,
            GREATEST(
                (SELECT COUNT(*) FROM escolas e
                 WHERE ST_Within(ST_SetSRID(ST_Point(e.longitude, e.latitude), 4326), ra.geom)),
                1
            ) AS n_escolas
        FROM regioes_administrativas ra
        """

        df = pd.read_sql(text(query), engine)

        eq_cols = ["saude", "seguranca", "parques", "cultura"]
        df["total_equipamentos"] = df[eq_cols].sum(axis=1)

        # Normalização por escola (quantos equipamentos por escola há na RA)
        for col in eq_cols:
            df[f"{col}_por_escola"] = (df[col] / df["n_escolas"]).round(2)
        df["total_por_escola"] = (df["total_equipamentos"] / df["n_escolas"]).round(2)

        # Índice 0-100 via min-max sobre o total por escola
        mn, mx = df["total_por_escola"].min(), df["total_por_escola"].max()
        if mx > mn:
            df["indice_normalizado"] = ((df["total_por_escola"] - mn) / (mx - mn) * 100).round(1)
        else:
            df["indice_normalizado"] = 50.0

        return df.sort_values("total_por_escola", ascending=False)
    except Exception as e:
        print(f"[load_entorno_por_ra] Erro: {e}")
        return None


def load_espacos_culturais_por_ra() -> pd.DataFrame | None:
    """
    Conta espaços culturais por tipo (ecult_equi) e Região Administrativa,
    via join entre espacos_culturais.ecult_ra e regioes_administrativas.ra_cira.
    """
    try:
        query = """
        SELECT
            ra.ra_nome           AS ra_nome,
            ec.ecult_equi        AS tipo,
            COUNT(*)             AS total
        FROM espacos_culturais ec
        JOIN regioes_administrativas ra ON ra.ra_cira::text = ec.ecult_ra::text
        GROUP BY ra.ra_nome, ec.ecult_equi
        """
        df = pd.read_sql(text(query), engine)
        # Normaliza grafias com problema de codificação ("ESPAÃO CULTURAL" == "ESPACO CULTURAL")
        df["tipo"] = df["tipo"].replace({"ESPAÃO CULTURAL": "ESPACO CULTURAL"}).str.title()
        df = df.groupby(["ra_nome", "tipo"], as_index=False)["total"].sum()
        return df
    except Exception as e:
        print(f"[load_espacos_culturais_por_ra] Erro: {e}")
        return None


def load_mobiliario_esporte_lazer() -> pd.DataFrame | None:
    """
    Conta equipamentos de esporte e lazer por tipo (elm_tp_mob) e
    condição física (elm_condic: INTEGRADO/ISOLADO).
    """
    try:
        query = """
        SELECT
            elm_tp_mob AS tipo,
            elm_condic AS condicao,
            COUNT(*)   AS total
        FROM mobiliario_esporte_e_lazer
        WHERE elm_tp_mob IS NOT NULL AND elm_condic IS NOT NULL
        GROUP BY elm_tp_mob, elm_condic
        """
        df = pd.read_sql(text(query), engine)
        # Normaliza grafias divergentes ("PARQUE_INFANTIL" vs "PARQUE INFANTIL") e remove categoria de limpeza
        df["tipo"] = df["tipo"].str.replace("_", " ").str.strip().str.title()
        df["condicao"] = df["condicao"].str.replace("_", " ").str.strip().str.title()
        df = df[df["tipo"] != "Excluir"]
        df = df.groupby(["tipo", "condicao"], as_index=False)["total"].sum()
        return df
    except Exception as e:
        print(f"[load_mobiliario_esporte_lazer] Erro: {e}")
        return None


def load_acessibilidade_por_ra() -> pd.DataFrame | None:
    """
    Para cada escola, calcula a distância (em metros) até o equipamento mais
    próximo de cada categoria (saúde, segurança, parques, cultura, esporte/lazer,
    espaços comunitários e feiras livres) via KNN espacial (operador `<->` +
    ST_Distance geográfico), e agrega a média dessas distâncias por Região
    Administrativa — um proxy de acessibilidade do entorno escolar.
    """
    try:
        query = """
        WITH escola_pts AS (
            SELECT id_escola, ST_SetSRID(ST_Point(longitude, latitude), 4326) AS pt
            FROM escolas
        )
        SELECT
            ra.ra_nome                              AS ra_nome,
            COUNT(*)                                AS n_escolas,
            AVG(d_saude.dist_m)                     AS saude_m,
            AVG(d_seg.dist_m)                       AS seguranca_m,
            AVG(d_parq.dist_m)                      AS parques_m,
            AVG(d_cult.dist_m)                      AS cultura_m,
            AVG(d_esp.dist_m)                       AS esporte_m,
            AVG(d_com.dist_m)                       AS comunitario_m,
            AVG(d_feira.dist_m)                     AS feira_m
        FROM escola_pts e
        JOIN regioes_administrativas ra ON ST_Within(e.pt, ra.geom)
        CROSS JOIN LATERAL (
            SELECT ST_Distance(e.pt::geography, s.geom::geography) AS dist_m
            FROM equipamentos_de_saude s ORDER BY e.pt <-> s.geom LIMIT 1
        ) d_saude
        CROSS JOIN LATERAL (
            SELECT ST_Distance(e.pt::geography, s.geom::geography) AS dist_m
            FROM equipamentos_de_seguranca s ORDER BY e.pt <-> s.geom LIMIT 1
        ) d_seg
        CROSS JOIN LATERAL (
            SELECT ST_Distance(e.pt::geography, s.geom::geography) AS dist_m
            FROM parques_urbanos s ORDER BY e.pt <-> s.geom LIMIT 1
        ) d_parq
        CROSS JOIN LATERAL (
            SELECT ST_Distance(e.pt::geography, s.geom::geography) AS dist_m
            FROM espacos_culturais s ORDER BY e.pt <-> s.geom LIMIT 1
        ) d_cult
        CROSS JOIN LATERAL (
            SELECT ST_Distance(e.pt::geography, s.geom::geography) AS dist_m
            FROM mobiliario_esporte_e_lazer s ORDER BY e.pt <-> s.geom LIMIT 1
        ) d_esp
        CROSS JOIN LATERAL (
            SELECT ST_Distance(e.pt::geography, s.geom::geography) AS dist_m
            FROM espacos_comunitarios s ORDER BY e.pt <-> s.geom LIMIT 1
        ) d_com
        CROSS JOIN LATERAL (
            SELECT ST_Distance(e.pt::geography, s.geom::geography) AS dist_m
            FROM feiras_livres s ORDER BY e.pt <-> s.geom LIMIT 1
        ) d_feira
        GROUP BY ra.ra_nome
        """
        df = pd.read_sql(text(query), engine)

        dist_cols = [
            "saude_m", "seguranca_m", "parques_m", "cultura_m",
            "esporte_m", "comunitario_m", "feira_m",
        ]
        df[dist_cols] = df[dist_cols].round(0)
        df["distancia_media_m"] = df[dist_cols].mean(axis=1).round(0)

        # Índice 0-100 via min-max (invertido: menor distância = maior acessibilidade)
        mn, mx = df["distancia_media_m"].min(), df["distancia_media_m"].max()
        if mx > mn:
            df["indice_acessibilidade"] = (100 - (df["distancia_media_m"] - mn) / (mx - mn) * 100).round(1)
        else:
            df["indice_acessibilidade"] = 50.0

        return df.sort_values("distancia_media_m")
    except Exception as e:
        print(f"[load_acessibilidade_por_ra] Erro: {e}")
        return None


def load_qualidade_entorno_por_ra() -> pd.DataFrame | None:
    """
    Combina o Índice de Infraestrutura (quantidade de equipamentos por escola,
    via load_entorno_por_ra) com o Índice de Acessibilidade (proximidade real,
    via load_acessibilidade_por_ra) numa média simples — o Índice de Qualidade
    do Entorno Escolar (0-100): quanto maior, mais o entorno da RA reúne tanto
    fartura de equipamentos quanto proximidade deles às escolas.
    """
    try:
        df_infra = load_entorno_por_ra()
        df_acess = load_acessibilidade_por_ra()
        if df_infra is None or df_acess is None:
            return None

        df = df_infra[["ra_nome", "indice_normalizado"]].merge(
            df_acess[["ra_nome", "indice_acessibilidade"]], on="ra_nome", how="inner"
        )
        df = df.rename(columns={"indice_normalizado": "indice_infraestrutura"})
        df["indice_qualidade_entorno"] = (
            (df["indice_infraestrutura"] + df["indice_acessibilidade"]) / 2
        ).round(1)
        return df.sort_values("indice_qualidade_entorno", ascending=False)
    except Exception as e:
        print(f"[load_qualidade_entorno_por_ra] Erro: {e}")
        return None


def load_capacidade_por_ra() -> pd.DataFrame | None:
    """
    Soma a capacidade estimada de matrícula (resultados.capacidade_matricula)
    das escolas de cada Região Administrativa via PostGIS ST_Within, e calcula
    a capacidade média por escola — um proxy do porte/escala da oferta de vagas
    de cada RA (não representa demanda real de matrículas).
    """
    try:
        query = """
        SELECT
            ra.ra_nome                          AS ra_nome,
            COUNT(*)                            AS n_escolas,
            SUM(r.capacidade_matricula)         AS capacidade_total
        FROM escolas e
        JOIN resultados r ON r.id_escola = e.id_escola
        JOIN regioes_administrativas ra
            ON ST_Within(ST_SetSRID(ST_Point(e.longitude, e.latitude), 4326), ra.geom)
        GROUP BY ra.ra_nome
        """
        df = pd.read_sql(text(query), engine)
        df["capacidade_por_escola"] = (df["capacidade_total"] / df["n_escolas"]).round(0)
        return df.sort_values("capacidade_total", ascending=False)
    except Exception as e:
        print(f"[load_capacidade_por_ra] Erro: {e}")
        return None


def load_oferta_qualidade_por_ra() -> pd.DataFrame | None:
    """
    Cruza a Oferta de Capacidade Estimada (`load_capacidade_por_ra`) com o
    Índice de Qualidade do Entorno Escolar (`load_qualidade_entorno_por_ra`)
    por Região Administrativa, classificando cada RA num quadrante a partir
    da mediana de cada métrica:

    - "Oferta alta + Entorno bom"   : região bem atendida nas duas dimensões
    - "Oferta alta + Entorno fraco" : concentra vagas, mas carece de infraestrutura
                                      ao redor — alerta de planejamento
    - "Oferta baixa + Entorno bom"  : entorno rico, mas pouca capacidade de matrícula
    - "Oferta baixa + Entorno fraco": carência nas duas dimensões — região mais vulnerável
    """
    try:
        df_cap = load_capacidade_por_ra()
        df_qual = load_qualidade_entorno_por_ra()
        if df_cap is None or df_qual is None:
            return None

        df = df_cap[["ra_nome", "n_escolas", "capacidade_total", "capacidade_por_escola"]].merge(
            df_qual[["ra_nome", "indice_infraestrutura", "indice_acessibilidade", "indice_qualidade_entorno"]],
            on="ra_nome", how="inner",
        )

        mediana_cap = df["capacidade_total"].median()
        mediana_qual = df["indice_qualidade_entorno"].median()

        def classificar(row):
            oferta = "Oferta alta" if row["capacidade_total"] >= mediana_cap else "Oferta baixa"
            entorno = "entorno bom" if row["indice_qualidade_entorno"] >= mediana_qual else "entorno fraco"
            return f"{oferta} + {entorno}"

        df["quadrante"] = df.apply(classificar, axis=1)
        return df.sort_values("capacidade_total", ascending=False)
    except Exception as e:
        print(f"[load_oferta_qualidade_por_ra] Erro: {e}")
        return None


def load_qualidade_entorno_por_escola() -> pd.DataFrame | None:
    """
    Para cada escola individualmente, calcula a distância (em metros) até o
    equipamento mais próximo de cada categoria (saúde, segurança, parques,
    cultura, esporte/lazer, espaços comunitários e feiras livres) via KNN
    espacial, e converte a distância média num índice de acessibilidade 0-100
    (min-max invertido: menor distância = maior índice).

    Diferente de `load_acessibilidade_por_ra`, não agrega por Região
    Administrativa — devolve uma linha por escola, com latitude/longitude,
    útil para visualizações mais granulares (ex.: heatmap ponderado).
    """
    try:
        query = """
        SELECT
            e.id_escola,
            e.latitude,
            e.longitude,
            ST_Distance(
                e.pt::geography,
                (SELECT s.geom FROM equipamentos_de_saude s ORDER BY e.pt <-> s.geom LIMIT 1)::geography
            ) AS saude_m,
            ST_Distance(
                e.pt::geography,
                (SELECT s.geom FROM equipamentos_de_seguranca s ORDER BY e.pt <-> s.geom LIMIT 1)::geography
            ) AS seguranca_m,
            ST_Distance(
                e.pt::geography,
                (SELECT s.geom FROM parques_urbanos s ORDER BY e.pt <-> s.geom LIMIT 1)::geography
            ) AS parques_m,
            ST_Distance(
                e.pt::geography,
                (SELECT s.geom FROM espacos_culturais s ORDER BY e.pt <-> s.geom LIMIT 1)::geography
            ) AS cultura_m,
            ST_Distance(
                e.pt::geography,
                (SELECT s.geom FROM mobiliario_esporte_e_lazer s ORDER BY e.pt <-> s.geom LIMIT 1)::geography
            ) AS esporte_m,
            ST_Distance(
                e.pt::geography,
                (SELECT s.geom FROM espacos_comunitarios s ORDER BY e.pt <-> s.geom LIMIT 1)::geography
            ) AS comunitario_m,
            ST_Distance(
                e.pt::geography,
                (SELECT s.geom FROM feiras_livres s ORDER BY e.pt <-> s.geom LIMIT 1)::geography
            ) AS feira_m
        FROM (
            SELECT id_escola, latitude, longitude,
                   ST_SetSRID(ST_Point(longitude, latitude), 4326) AS pt
            FROM escolas
        ) e
        """
        df = pd.read_sql(text(query), engine)

        dist_cols = [
            "saude_m", "seguranca_m", "parques_m", "cultura_m",
            "esporte_m", "comunitario_m", "feira_m",
        ]
        df[dist_cols] = df[dist_cols].round(0)
        df["distancia_media_m"] = df[dist_cols].mean(axis=1).round(0)

        # Índice 0-100 via min-max (invertido: menor distância = maior acessibilidade)
        mn, mx = df["distancia_media_m"].min(), df["distancia_media_m"].max()
        if mx > mn:
            df["indice_qualidade_entorno"] = (100 - (df["distancia_media_m"] - mn) / (mx - mn) * 100).round(1)
        else:
            df["indice_qualidade_entorno"] = 50.0

        return df
    except Exception as e:
        print(f"[load_qualidade_entorno_por_escola] Erro: {e}")
        return None


def load_distancia_transporte_por_escola() -> pd.DataFrame | None:
    """
    Para cada escola, calcula a distância (em metros) até a estação/terminal de
    transporte público de alta capacidade mais próximo (metrô, BRT ou terminal
    DFTrans — camada `estacoes_terminais_transporte`, importada do Geoportal
    IDE-DF/SEDUH), via KNN espacial. Proxy de acesso da comunidade escolar ao
    transporte coletivo estruturante do DF.
    """
    try:
        query = """
        SELECT
            e.id_escola,
            e.nome_escola,
            e.latitude,
            e.longitude,
            t.nome AS estacao_mais_proxima,
            t.tipo AS tipo_estacao,
            ST_Distance(e.pt::geography, t.geom::geography) AS distancia_transporte_m
        FROM (
            SELECT id_escola, nome_escola, latitude, longitude,
                   ST_SetSRID(ST_Point(longitude, latitude), 4326) AS pt
            FROM escolas
        ) e
        JOIN LATERAL (
            SELECT nome, tipo, geom
            FROM estacoes_terminais_transporte
            ORDER BY e.pt <-> geom
            LIMIT 1
        ) t ON true
        """
        df = pd.read_sql(text(query), engine)
        df["distancia_transporte_m"] = df["distancia_transporte_m"].round(0)
        return df
    except Exception as e:
        print(f"[load_distancia_transporte_por_escola] Erro: {e}")
        return None


def load_distancia_onibus_osm_por_escola() -> pd.DataFrame | None:
    """
    Para cada escola, calcula (via KNN espacial / JOIN LATERAL) a distância até a
    parada/plataforma de ônibus mapeada no OpenStreetMap mais próxima — um proxy
    de acesso ao transporte coletivo convencional (diferente das estações
    estruturantes de metrô/BRT/terminais do Geoportal IDE-DF).
    """
    try:
        query = """
        SELECT
            e.id_escola, e.nome_escola, e.latitude, e.longitude,
            p.nome AS parada_mais_proxima, p.tipo AS tipo_parada,
            ST_Distance(e.pt::geography, p.geom::geography) AS distancia_onibus_m
        FROM (
            SELECT id_escola, nome_escola, latitude, longitude,
                   ST_SetSRID(ST_Point(longitude, latitude), 4326) AS pt
            FROM escolas
        ) e
        JOIN LATERAL (
            SELECT nome, tipo, geom
            FROM paradas_onibus_osm
            ORDER BY e.pt <-> geom
            LIMIT 1
        ) p ON true
        """
        df = pd.read_sql(text(query), engine)
        df["distancia_onibus_m"] = df["distancia_onibus_m"].round(0)
        return df
    except Exception as e:
        print(f"[load_distancia_onibus_osm_por_escola] Erro: {e}")
        return None


def load_onibus_osm_por_ra() -> pd.DataFrame | None:
    """
    Para cada Região Administrativa, conta as paradas/plataformas de ônibus
    (OpenStreetMap) dentro de seus limites e calcula a distância média das
    suas escolas até a parada mais próxima — combinando cobertura local
    (quantas paradas existem na RA) com acesso real das escolas (mesmo que a
    parada mais próxima esteja em outra RA). Substitui a antiga agregação
    baseada nas 43 estações estruturantes do Geoportal IDE-DF por uma malha
    bem mais densa (1.937 paradas mapeadas).
    """
    try:
        df_dist = load_distancia_onibus_osm_por_escola()
        if df_dist is None:
            return None

        query_contagem = """
        SELECT ra.ra_nome AS ra_nome, COUNT(p.geom) AS n_paradas
        FROM regioes_administrativas ra
        LEFT JOIN paradas_onibus_osm p
            ON ST_Within(p.geom, ra.geom)
        GROUP BY ra.ra_nome
        """
        df_contagem = pd.read_sql(text(query_contagem), engine)

        query_ra_escola = """
        SELECT e.id_escola, ra.ra_nome AS ra_nome
        FROM escolas e
        JOIN regioes_administrativas ra
            ON ST_Within(ST_SetSRID(ST_Point(e.longitude, e.latitude), 4326), ra.geom)
        """
        df_ra_escola = pd.read_sql(text(query_ra_escola), engine)

        df = df_dist.merge(df_ra_escola, on="id_escola", how="inner")
        df_resumo = (
            df.groupby("ra_nome", as_index=False)["distancia_onibus_m"]
            .mean()
            .rename(columns={"distancia_onibus_m": "distancia_media_onibus_m"})
        )
        df_resumo["distancia_media_onibus_m"] = df_resumo["distancia_media_onibus_m"].round(0)

        df_final = df_contagem.merge(df_resumo, on="ra_nome", how="left")
        return df_final.sort_values("distancia_media_onibus_m")
    except Exception as e:
        print(f"[load_onibus_osm_por_ra] Erro: {e}")
        return None


QUADRANTES_ACESSO_ENTORNO = [
    "Bom acesso + bom entorno",
    "Bom acesso + entorno carente",
    "Acesso ruim + bom entorno",
    "Dupla desvantagem (acesso ruim + entorno carente)",
]


def load_quadrante_acesso_onibus_entorno() -> pd.DataFrame | None:
    """
    Classifica cada escola num quadrante cruzando o acesso ao transporte
    coletivo (distância até a parada de ônibus OSM mais próxima) com a
    qualidade do seu entorno (Índice de Qualidade do Entorno 0-100), usando
    as medianas do Distrito Federal como linha de corte. Inclui a Região
    Administrativa de cada escola, permitindo agregações geográficas.

    Quadrantes: "Bom acesso + bom entorno", "Bom acesso + entorno carente",
    "Acesso ruim + bom entorno" e "Dupla desvantagem (acesso ruim + entorno
    carente)".
    """
    try:
        df_dist = load_distancia_onibus_osm_por_escola()
        df_qual = load_qualidade_entorno_por_escola()
        if df_dist is None or df_qual is None:
            return None

        df = df_dist.merge(
            df_qual[["id_escola", "indice_qualidade_entorno"]], on="id_escola", how="inner"
        )

        query_ra = """
        SELECT e.id_escola, ra.ra_nome
        FROM escolas e
        JOIN regioes_administrativas ra
            ON ST_Within(ST_SetSRID(ST_Point(e.longitude, e.latitude), 4326), ra.geom)
        """
        df_ra = pd.read_sql(text(query_ra), engine)
        df = df.merge(df_ra, on="id_escola", how="inner")
        df = df.dropna(subset=["distancia_onibus_m", "indice_qualidade_entorno"])

        mediana_dist = df["distancia_onibus_m"].median()
        mediana_indice = df["indice_qualidade_entorno"].median()

        def _classificar(row):
            acesso_bom = row["distancia_onibus_m"] <= mediana_dist
            entorno_bom = row["indice_qualidade_entorno"] >= mediana_indice
            if acesso_bom and entorno_bom:
                return QUADRANTES_ACESSO_ENTORNO[0]
            elif acesso_bom and not entorno_bom:
                return QUADRANTES_ACESSO_ENTORNO[1]
            elif not acesso_bom and entorno_bom:
                return QUADRANTES_ACESSO_ENTORNO[2]
            return QUADRANTES_ACESSO_ENTORNO[3]

        df["quadrante"] = df.apply(_classificar, axis=1)
        df.attrs["mediana_distancia_onibus_m"] = mediana_dist
        df.attrs["mediana_indice_qualidade_entorno"] = mediana_indice
        return df
    except Exception as e:
        print(f"[load_quadrante_acesso_onibus_entorno] Erro: {e}")
        return None


def load_paradas_onibus_osm() -> "gpd.GeoDataFrame | None":
    """Paradas/plataformas de ônibus extraídas do OpenStreetMap (Overpass API)."""
    try:
        return gpd.read_postgis(
            "SELECT id_osm, nome, tipo, ref, geom FROM paradas_onibus_osm",
            con=engine, geom_col="geom",
        )
    except Exception as e:
        print(f"[load_paradas_onibus_osm] Erro: {e}")
        return None


def load_linhas_onibus_osm() -> "gpd.GeoDataFrame | None":
    """Traçados de linhas de ônibus (relations route=bus) extraídos do OpenStreetMap."""
    try:
        return gpd.read_postgis(
            "SELECT id_osm, nome, ref, geom FROM linhas_onibus_osm",
            con=engine, geom_col="geom",
        )
    except Exception as e:
        print(f"[load_linhas_onibus_osm] Erro: {e}")
        return None


def load_escolas_contexto_entorno() -> pd.DataFrame | None:
    """
    Para cada escola, junta atributos cadastrais (rede, localização urbana/rural,
    porte, modalidade) com a Região Administrativa onde está localizada, o
    Índice de Qualidade do Entorno da RA e a acessibilidade individual da
    escola (distâncias por categoria + índice 0-100).

    Base unificada para cruzamentos do tipo "característica da escola × entorno":
    urbano/rural, rede pública/privada, porte da escola, etc.
    """
    try:
        query = """
        SELECT
            e.id_escola, e.nome_escola, e.latitude, e.longitude, e.tipo_rede,
            e.localizacao, e.porte_escola, e.modalidade_ensino, ra.ra_nome
        FROM escolas e
        JOIN regioes_administrativas ra
            ON ST_Within(ST_SetSRID(ST_Point(e.longitude, e.latitude), 4326), ra.geom)
        """
        df_attrs = pd.read_sql(text(query), engine)

        df_qual_ra = load_qualidade_entorno_por_ra()
        df_acess_escola = load_qualidade_entorno_por_escola()
        if df_qual_ra is None or df_acess_escola is None:
            return None

        df = df_attrs.merge(
            df_qual_ra[["ra_nome", "indice_qualidade_entorno"]].rename(
                columns={"indice_qualidade_entorno": "indice_qualidade_ra"}
            ),
            on="ra_nome", how="left",
        )

        dist_cols = [
            "saude_m", "seguranca_m", "parques_m", "cultura_m",
            "esporte_m", "comunitario_m", "feira_m", "distancia_media_m",
        ]
        df = df.merge(
            df_acess_escola[["id_escola"] + dist_cols + ["indice_qualidade_entorno"]].rename(
                columns={"indice_qualidade_entorno": "indice_acessibilidade_escola"}
            ),
            on="id_escola", how="left",
        )
        return df
    except Exception as e:
        print(f"[load_escolas_contexto_entorno] Erro: {e}")
        return None


def load_diversidade_modalidades_por_ra() -> pd.DataFrame | None:
    """
    Para cada Região Administrativa, conta quantas modalidades de ensino
    distintas (`modalidade_ensino`) estão presentes em suas escolas, e cruza
    com o Índice de Qualidade do Entorno — para checar se RAs mais carentes
    de infraestrutura também oferecem um leque mais restrito de modalidades.
    """
    try:
        query = """
        SELECT
            ra.ra_nome AS ra_nome,
            e.modalidade_ensino AS modalidade
        FROM escolas e
        JOIN regioes_administrativas ra
            ON ST_Within(ST_SetSRID(ST_Point(e.longitude, e.latitude), 4326), ra.geom)
        WHERE e.modalidade_ensino IS NOT NULL AND e.modalidade_ensino <> ''
        """
        df_raw = pd.read_sql(text(query), engine)
        diversidade = (
            df_raw.groupby("ra_nome")["modalidade"].nunique()
            .reset_index(name="n_modalidades")
        )

        df_qual = load_qualidade_entorno_por_ra()
        if df_qual is None:
            return None

        df = diversidade.merge(
            df_qual[["ra_nome", "indice_qualidade_entorno"]], on="ra_nome", how="inner"
        )
        return df.sort_values("n_modalidades", ascending=False)
    except Exception as e:
        print(f"[load_diversidade_modalidades_por_ra] Erro: {e}")
        return None


def load_densidade_escolar_por_ra() -> pd.DataFrame | None:
    """
    Calcula a densidade escolar (escolas por km²) e a densidade de capacidade
    (vagas estimadas por km²) de cada Região Administrativa, cruzando a
    contagem/capacidade de escolas (`load_capacidade_por_ra`) com a área
    territorial (`ra_areakm2`) — um proxy de cobertura territorial, e não
    apenas de quantidade absoluta de escolas.
    """
    try:
        df_cap = load_capacidade_por_ra()
        if df_cap is None:
            return None

        query = "SELECT ra_nome, ra_areakm2 FROM regioes_administrativas"
        df_area = pd.read_sql(text(query), engine)

        df = df_cap.merge(df_area, on="ra_nome", how="inner")
        df["escolas_por_km2"] = (df["n_escolas"] / df["ra_areakm2"]).round(3)
        df["capacidade_por_km2"] = (df["capacidade_total"] / df["ra_areakm2"]).round(1)
        return df.sort_values("escolas_por_km2", ascending=False)
    except Exception as e:
        print(f"[load_densidade_escolar_por_ra] Erro: {e}")
        return None


def load_esporte_lazer_distancia_por_condicao() -> pd.DataFrame | None:
    """
    Para cada escola, calcula a distância (em metros) até o equipamento de
    esporte/lazer mais próximo, separando por condição física do equipamento
    (`elm_condic`: Integrado ou Isolado), via KNN espacial. Permite comparar
    se equipamentos "integrados" (geralmente vinculados a escolas/uso
    compartilhado) estão de fato mais perto das escolas do que os "isolados".
    """
    try:
        query = """
        WITH escola_pts AS (
            SELECT id_escola, ST_SetSRID(ST_Point(longitude, latitude), 4326) AS pt
            FROM escolas
        )
        SELECT
            e.id_escola,
            d_int.dist_m AS integrado_m,
            d_iso.dist_m AS isolado_m
        FROM escola_pts e
        CROSS JOIN LATERAL (
            SELECT ST_Distance(e.pt::geography, s.geom::geography) AS dist_m
            FROM mobiliario_esporte_e_lazer s
            WHERE s.elm_condic = 'INTEGRADO'
            ORDER BY e.pt <-> s.geom LIMIT 1
        ) d_int
        CROSS JOIN LATERAL (
            SELECT ST_Distance(e.pt::geography, s.geom::geography) AS dist_m
            FROM mobiliario_esporte_e_lazer s
            WHERE s.elm_condic = 'ISOLADO'
            ORDER BY e.pt <-> s.geom LIMIT 1
        ) d_iso
        """
        df = pd.read_sql(text(query), engine)
        df[["integrado_m", "isolado_m"]] = df[["integrado_m", "isolado_m"]].round(0)

        melted = df.melt(
            id_vars="id_escola", value_vars=["integrado_m", "isolado_m"],
            var_name="condicao", value_name="distancia_m",
        )
        melted["condicao"] = melted["condicao"].map(
            {"integrado_m": "Integrado", "isolado_m": "Isolado"}
        )
        return melted
    except Exception as e:
        print(f"[load_esporte_lazer_distancia_por_condicao] Erro: {e}")
        return None


# --- BLOCO DE EXECUÇÃO MODIFICADO APENAS NA CHAMADA ---
if __name__ == "__main__":
    print("\n=== INICIANDO PIPELINE DE CARGA DE DADOS ===")

    # 1. Roda a sua função atual do CSV (que você me disse que já funciona perfeitamente)
    load_inicial_data()

    # 2. Roda a nova função dos Shapefiles de forma totalmente independente
    load_shapefiles_data()

    print("=== PIPELINE DE CARGA DE DADOS FINALIZADO ===\n")
