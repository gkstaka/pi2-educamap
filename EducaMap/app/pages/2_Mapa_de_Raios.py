import streamlit as st
import folium
import pandas as pd
from streamlit_folium import st_folium
from folium.plugins import BeautifyIcon
from app.modules.data_utils import load_data_from_postgres
import geopandas as gpd
from app.utils.model import engine


@st.cache_data(ttl=3600)
def carregar_ra_do_banco():
    """Busca o mapa das Regiões Administrativas direto do PostGIS."""
    try:
        # A coluna geométrica padronizada no seu pipeline é 'geom'
        query = "SELECT * FROM regioes_administrativas;"
        gdf_ra = gpd.read_postgis(query, con=engine, geom_col="geom")
        return gdf_ra
    except Exception as e:
        st.error(f"Erro ao carregar mapa do PostGIS: {e}")
        return None


def get_urban_radius_logic(porte):
    """Retorna o raio e a justificativa baseada no porte da escola."""
    porte = str(porte).upper()
    if "ATÉ 50" in porte or "SEM MATRÍCULA" in porte:
        return 500, "Caminhada Local"
    elif "51 E 200" in porte:
        return 800, "Padrão Fundamental I"
    elif "201 E 500" in porte:
        return 1000, "Padrão Fundamental II"
    elif "501 E 1000" in porte:
        return 2000, "Atendimento Regional"
    else:
        return 3000, "Escola de Referência"


def render_radius_map():
    # 1. Configuração da Página
    st.set_page_config(
        layout="wide",
        page_title="Mapa de Raios - EducaMap",
        initial_sidebar_state="expanded",
    )

    # 2. CSS para Layout Full Screen
    st.markdown(
        """
        <style>
        [data-testid="collapsedControl"] { display: none !important; }
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container { padding: 0rem; margin: 0rem; max-width: 100%; }
        [data-testid="stSidebar"] { min-width: 280px !important; max-width: 280px !important; }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # 3. Carregamento de Dados
    try:
        df = load_data_from_postgres()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return

    # 4. Carregamento do Shapefile das Regiões Administrativas do Banco
    gdf_regioes = carregar_ra_do_banco()

    # --- BARRA LATERAL (FILTROS) ---
    with st.sidebar:
        st.markdown(
            "<h2 style='color: #1F5D8D; margin-bottom: 0;'>EducaMap</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='color: #666; font-size: 0.8rem;'>Análise de Abrangência Escolar</p>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        st.sidebar.title("Filtros de Análise")

        modalidades_map = {
            "Educação Infantil": "infantil",
            "Ensino Fundamental": "fundamental",
            "Ensino Médio": "médio",
            "Educação de Jovens Adultos": "jovens e adultos",
            "Educação Profissional": "profissional",
        }

        selected_modalidades = st.multiselect(
            "Modalidade de Ensino",
            options=list(modalidades_map.keys()),
            default=["Educação Infantil"],
        )

        opcoes_porte = [
            "Escola sem matrícula de escolarização",
            "Até 50 matrículas de escolarização",
            "Entre 51 e 200 matrículas de escolarização",
            "Entre 201 e 500 matrículas de escolarização",
            "Entre 501 e 1000 matrículas de escolarização",
            "Mais de 1000 matrículas de escolarização",
        ]

        selected_portes = st.multiselect(
            "Porte da Escola",
            options=opcoes_porte,
            default=["Entre 201 e 500 matrículas de escolarização"],
        )

        # --- LÓGICA DE FILTRAGEM ---
        col_mod = "Etapas e Modalidade de Ensino Oferecidas"
        if selected_modalidades:
            keywords = [modalidades_map[name] for name in selected_modalidades]
            pattern = "|".join(keywords)
            mask_modalidade = (
                df[col_mod].fillna("").str.contains(pattern, case=False, na=False)
            )
        else:
            mask_modalidade = pd.Series(False, index=df.index)

        mask_final = mask_modalidade & df["Porte da Escola"].isin(selected_portes)
        num_escolas = len(df[mask_final])
        st.metric("Escolas Filtradas", num_escolas)

        if num_escolas == 0:
            st.warning("Nenhuma escola corresponde aos filtros. Mostrando mapa base.")

    # --- INICIALIZAÇÃO DO MAPA ---
    # Define um centro padrão (Brasília) caso o filtro esteja vazio
    if not df[mask_final].empty:
        center_lat = df[mask_final]["Latitude"].mean()
        center_lon = df[mask_final]["Longitude"].mean()
        zoom = 12
    else:
        center_lat, center_lon = -15.793889, -47.882778
        zoom = 11

    m = folium.Map(
        location=[center_lat, center_lon], zoom_start=zoom, tiles="OpenStreetMap"
    )

    # --- DESENHO DAS REGIÕES ADMINISTRATIVAS (SHAPEFILE) ---
    if gdf_regioes is not None and not gdf_regioes.empty:
        # Detecta dinamicamente a coluna de nome disponível no shapefile do DF
        colunas_possiveis = ["nome", "ra_nome", "ra", "NM_RA"]
        campo_nome = next(
            (c for c in colunas_possiveis if c in gdf_regioes.columns),
            gdf_regioes.columns[0],
        )
        # campo_ra = next(c for c in ra_codigo if c gdf_regioes.columns),gdf_regioes.columns[0],)

        # Dicionário de cores inserido aqui dentro ou no escopo global
        mapa_cores_ras = {
            "PLANO PILOTO": "#1F5D8D",
            "GAMA": "#4682B4",
            "TAGUATINGA": "#008080",
            "BRAZLÃNDIA": "#2E8B57",
            "SOBRADINHO": "#3CB371",
            "PLANALTINA": "#556B2F",
            "PARANOÃ": "#6B8E23",
            "NÃCLEO BANDEIRANTE": "#8B4513",
            "CEILÃNDIA": "#A0522D",
            "GUARÃ": "#CD853F",
            "CRUZEIRO": "#D2691E",
            "SAMAMBAIA": "#B22222",
            "SANTA MARIA": "#FF4500",
            "SÃO SEBASTIÃO": "#FF8C00",
            "RECANTO DAS EMAS": "#E9967A",
            "LAGO SUL": "#4B0082",
            "LAGO NORTE": "#483D8B",
            "CANDANGOLÃNDIA": "#6A5ACD",
            "ÃGUAS CLARAS": "#7B68EE",
            "RIACHO FUNDO": "#9370DB",
            "SUDOESTE/OCTOGONAL": "#8A2BE2",
            "VARJÃO": "#C71585",
            "PARK WAY": "#DB7093",
            "SCIA": "#FF1493",
            "SOBRADINHO II": "#FF69B4",
            "JARDIM BOTÃNICO": "#20B2AA",
            "ITAPOÃ": "#00CED1",
            "SIA": "#708090",
            "VICENTE PIRES": "#778899",
            "FERCAL": "#5F9EA0",
            "SOL NASCENTE E POR DO SOL": "#D2B48C",
            "ARNIQUEIRA": "#BC8F8F",
            "ARAPOANGA": "#F4A460",
            "AGUA QUENTE": "#DEB887",
        }

        folium.GeoJson(
            gdf_regioes,
            name="Regiões Administrativas",
            style_function=lambda feature: {
                # Puxa o nome da RA da linha atual do Shapefile e busca a cor correspondente
                "fillColor": mapa_cores_ras.get(
                    feature["properties"].get(campo_nome, ""), "#1F5D8D"
                ),
                "color": "#113c5e",  # Linha de contorno fina separando as RAs
                "weight": 1.2,
                "fillOpacity": 0.25,  # Opacidade um pouco maior para evidenciar as cores sem cobrir as escolas
            },
            tooltip=folium.GeoJsonTooltip(
                fields=[campo_nome], aliases=["RA:"], localize=True
            ),
        ).add_to(m)

    # --- CRIAÇÃO DAS CAMADAS ---
    camada_raios = folium.FeatureGroup(name="Raio de Abrangência", show=True)
    camada_escolas = folium.FeatureGroup(name="Escolas Filtradas", show=True)

    # --- ADIÇÃO DE ELEMENTOS (APENAS SE HOUVER DADOS) ---
    if not df[mask_final].empty:
        for _, row in df[mask_final].iterrows():
            radius_m, justificativa = get_urban_radius_logic(row["Porte da Escola"])

            mapa_cores_porte = {
                "Escola sem matrícula de escolarização": "#98FB98",
                "Até 50 matrículas de escolarização": "#C0D870",
                "Entre 51 e 200 matrículas de escolarização": "#E8D858",
                "Entre 201 e 500 matrículas de escolarização": "#FCD04B",
                "Entre 501 e 1000 matrículas de escolarização": "#FFA63A",
                "Mais de 1000 matrículas de escolarização": "#FF7F24",
            }

            mapa_cores_localizacao = {
                "Urbana": "darkblue",
                "Rural": "darkgreen",
            }

            color_circle = mapa_cores_porte.get(row["Porte da Escola"], "#1F5D8D")
            color_marker = mapa_cores_localizacao.get(row["Localização"], "gray")

            popup_text_marker = f"<small><b>{row['Escola']}</b><br>{row['Endereço']}<br><b>Localização:</b><br>{row['Localização']}<br><b>Rede:</b><br>{row['Dependência Administrativa']}</small>"
            popup_text_circle = f"<small><b>{row['Escola']}</b><br>Raio: {radius_m}m<br><b>Justificativa:</b><br>{justificativa}</small>"

            folium.Circle(
                location=[row["Latitude"], row["Longitude"]],
                radius=radius_m,
                color=color_circle,
                fill=True,
                fill_opacity=0.2,
                weight=1,
                popup=popup_text_circle,
            ).add_to(camada_raios)

            folium.Marker(
                location=[row["Latitude"], row["Longitude"]],
                icon=BeautifyIcon(
                    icon="graduation-cap",
                    iconSize=[30, 30],
                    prefix="fa",
                    icon_shape="circle",
                    background_color=color_marker,
                    border_color="#000000",
                    border_width=1,
                    text_color="#FFFFFF",
                ),
                tooltip=f"<small>{row['Escola']}</small>",
                popup=popup_text_marker,
            ).add_to(camada_escolas)

    camada_raios.add_to(m)
    camada_escolas.add_to(m)

    folium.LayerControl(position="topright", collapsed=False).add_to(m)

    st_folium(m, width="100%", height=900, returned_objects=[])


if __name__ == "__main__":
    render_radius_map()
