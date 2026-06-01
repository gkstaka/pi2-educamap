import streamlit as st
import folium
import geopandas as gpd
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, BeautifyIcon
from app.modules.data_utils import load_data_from_postgres
from app.utils.model import engine


# --- FUNÇÕES DE CARREGAMENTO GEOGRÁFICO DO POSTGIS ---
@st.cache_data(ttl=3600)
def carregar_camada_geografica(nome_tabela):
    """Busca tabelas espaciais genéricas direto do PostGIS."""
    try:
        query = f"SELECT * FROM {nome_tabela};"
        gdf = gpd.read_postgis(query, con=engine, geom_col="geom")
        return gdf
    except Exception as e:
        st.error(f"Erro ao carregar a camada '{nome_tabela}' do PostGIS: {e}")
        return None


def render_atratividade_map():
    st.set_page_config(
        layout="wide",
        page_title="Mapa de Atratividade - EducaMap",
        initial_sidebar_state="expanded",
    )

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

    try:
        df_escolas = load_data_from_postgres()
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados das escolas: {e}")
        return

    gdf_regioes = carregar_camada_geografica("regioes_administrativas")
    gdf_cultura = carregar_camada_geografica("espacos_culturais")
    gdf_feiras = carregar_camada_geografica("feiras_livres")
    gdf_seguranca = carregar_camada_geografica("equipamentos_de_seguranca")
    gdf_parques = carregar_camada_geografica("parques_urbanos")
    gdf_saude = carregar_camada_geografica("equipamentos_de_saude")
    # gdf_comunitarios = carregar_camada_geografica("espacos_comunitarios")
    # gdf_esporte = carregar_camada_geografica("mobiliario_esporte_e_lazer")

    # FIX: ver o que fazer com gdf_esporte que trava o navegador
    # FIX: ver o que fazer com comunitarios que está com muito s NULL no banco

    # --- BARRA LATERAL (FILTROS E CONTROLE DE CAMADAS) ---
    with st.sidebar:
        st.markdown(
            "<h2 style='color: #1F5D8D; margin-bottom: 0;'>EducaMap</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='color: #666; font-size: 0.8rem;'>Análise Multicritério de Entorno</p>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        st.title("Filtros do Entorno")

        opcoes_rede = (
            list(df_escolas["Dependência Administrativa"].unique())
            if not df_escolas.empty
            else []
        )
        selected_rede = st.multiselect(
            "Rede de Ensino", options=opcoes_rede, default=opcoes_rede
        )

        mask_final = df_escolas["Dependência Administrativa"].isin(selected_rede)
        df_filtrado = df_escolas[mask_final]

        st.metric("Escolas em Análise", len(df_filtrado))
        st.markdown("---")
        st.info(
            "💡 Use o controle de camadas (ícone flutuante no topo direito do mapa) para ligar ou desligar os pontos de atratividade."
        )

    # --- INICIALIZAÇÃO DO MAPA BASE ---
    if not df_filtrado.empty:
        center_lat = df_filtrado["Latitude"].mean()
        center_lon = df_filtrado["Longitude"].mean()
        zoom = 12
    else:
        center_lat, center_lon = -15.793889, -47.882778
        zoom = 11

    m = folium.Map(
        location=[center_lat, center_lon], zoom_start=zoom, tiles="OpenStreetMap"
    )

    # --- 1. RENDERIZAÇÃO DA BASE DAS RAs (POLÍGONOS) ---
    if gdf_regioes is not None and not gdf_regioes.empty:
        colunas_possiveis = ["nome", "ra_nome", "ra", "NM_RA"]
        campo_nome_ra = next(
            (c for c in colunas_possiveis if c in gdf_regioes.columns),
            gdf_regioes.columns[0],
        )
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
                "fillColor": mapa_cores_ras.get(
                    feature["properties"].get(campo_nome_ra, ""), "#1F5D8D"
                ),
                "color": "#113c5e",
                "weight": 1.2,
                "fillOpacity": 0.15,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=[campo_nome_ra], aliases=["RA:"], localize=True
            ),
        ).add_to(m)

    # --- 2. ADIÇÃO DAS CAMADAS DE ATRATIVIDADE (SHAPEFILES) ---

    # ==========================================
    # CAMADA: ESPAÇOS CULTURAIS (Roxo)
    # ========================================
    if gdf_cultura is not None and not gdf_cultura.empty:
        camada_cultura = folium.FeatureGroup(name="Espaços Culturais", show=False)
        cluster_cultura = MarkerCluster(
            options={
                "maxClusterRadius": 30,
                "spiderfyOnMaxZoom": True,
            }
        )
        for _, row_geo in gdf_cultura.iterrows():
            if row_geo["geom"] is not None:
                ponto_central = row_geo["geom"].centroid
                coord = [ponto_central.y, ponto_central.x]

                nome_cultural = row_geo.get("ecult_nome", "Não Informado")
                tipo_equipamento = row_geo.get("ecult_equi", "Espaço Cultural")
                popup_text = (
                    f"<small><b>{nome_cultural}</b><br>{tipo_equipamento}</small>"
                )

                folium.Marker(
                    location=coord,
                    icon=BeautifyIcon(
                        icon="theater-masks",
                        iconSize=[30, 30],
                        prefix="fa",
                        icon_shape="circle",
                        background_color="#8A2BE2",
                        border_color="#000000",
                        border_width=1,
                        text_color="#FFFFFF",
                    ),
                    popup=popup_text,
                    tooltip=f"<small>ESPAÇO CULTURAL: {tipo_equipamento}</small>",
                ).add_to(cluster_cultura)
        cluster_cultura.add_to(camada_cultura)
        camada_cultura.add_to(m)

    # ==========================================
    # CAMADA: PARQUES URBANOS (Verde)
    # ==========================================
    if gdf_parques is not None and not gdf_parques.empty:
        camada_parques = folium.FeatureGroup(name="Parques Urbanos", show=False)
        cluster_parque = MarkerCluster(
            options={
                "maxClusterRadius": 40,
                "spiderfyOnMaxZoom": True,
            }
        )
        for _, row_geo in gdf_parques.iterrows():
            if row_geo["geom"] is not None:
                centroid = row_geo["geom"].centroid
                coord = [centroid.y, centroid.x]

                nome_parque = row_geo.get("pqu_nome", "Não Informado")

                folium.Marker(
                    location=coord,
                    icon=BeautifyIcon(
                        icon="tree",
                        iconSize=[30, 30],
                        prefix="fa",
                        icon_shape="circle",
                        background_color="#2E8B57",
                        border_color="#000000",
                        border_width=1,
                        text_color="#FFFFFF",
                    ),
                    popup=f"<small>{nome_parque}</small>",
                    tooltip="<small>PARQUE URBANO</small>",
                ).add_to(cluster_parque)
        cluster_parque.add_to(camada_parques)
        camada_parques.add_to(m)

    # ==========================================
    # CAMADA: FEIRAS LIVRES (Laranja)
    # ==========================================
    if gdf_feiras is not None and not gdf_feiras.empty:
        camada_feiras = folium.FeatureGroup(name="Feiras Livres", show=False)
        cluster_feira = MarkerCluster(
            options={
                "maxClusterRadius": 40,
                "spiderfyOnMaxZoom": True,
            }
        )
        for _, row_geo in gdf_feiras.iterrows():
            if row_geo["geom"] is not None:
                ponto_central = row_geo["geom"].centroid
                coord = [ponto_central.y, ponto_central.x]

                nome_feira = row_geo.get("fei_nome", "Não Informado")
                endereco_feira = row_geo.get("fei_endere", "Não Informado")

                popup_text = f"<small><b>{nome_feira}</b><br>{endereco_feira}</small>"

                folium.Marker(
                    location=coord,
                    icon=BeautifyIcon(
                        icon="shop",
                        iconSize=[30, 30],
                        prefix="fa",
                        icon_shape="circle",
                        background_color="#FF8C00",
                        border_color="#000000",
                        border_width=1,
                        text_color="#FFFFFF",
                    ),
                    popup=popup_text,
                    tooltip="<small>FEIRA LIVRE</small>",
                ).add_to(cluster_feira)
        cluster_feira.add_to(camada_feiras)
        camada_feiras.add_to(m)

    # FIX: Tentativa de código! travou o navegador.

    # ==========================================
    # CAMADA: MOBILIÁRIO DE ESPORTE E LAZER
    # ==========================================
    # if gdf_esporte is not None and not gdf_esporte.empty:
    #     camada_esporte = folium.FeatureGroup(name="Esporte e Lazer", show=False)
    #     cluster_esporte = MarkerCluster(
    #         options={
    #             "maxClusterRadius": 40,
    #             "spiderfyOnMaxZoom": True,
    #         }
    #     )
    #     for _, row_geo in gdf_esporte.iterrows():
    #         if row_geo["geom"] is not None:
    #             ponto_central = row_geo["geom"].centroid
    #             coord = [ponto_central.y, ponto_central.x]
    #
    #             nome_mob = row_geo.get("elm_tp_mob", "Não Informado")
    #             endereco_mob = row_geo.get("elm_endere", "Não Informado")
    #
    #             popup_text = f"<small><b>{nome_mob}</b><br>{endereco_mob}</small>"
    #
    #             folium.Marker(
    #                 location=coord,
    #                 icon=BeautifyIcon(
    #                     icon="volleyball",
    #                     iconSize=[30, 30],
    #                     prefix="fa",
    #                     icon_shape="circle",
    #                     background_color="#D2691E",
    #                     border_color="#000000",
    #                     border_width=1,
    #                     text_color="#FFFFFF",
    #                 ),
    #                 popup=popup_text,
    #                 tooltip="<small>EPORTE E LAZER</small>",
    #             ).add_to(cluster_esporte)
    #     cluster_esporte.add_to(camada_esporte)
    #     camada_esporte.add_to(m)

    # ==========================================
    # CAMADA: EQUIPAMENTOS DE SEGURANÇA (Vermelho)
    # ==========================================
    if gdf_seguranca is not None and not gdf_seguranca.empty:
        camada_seguranca = folium.FeatureGroup(
            name="Equipamentos de Segurança", show=False
        )
        cluster_seguranca = MarkerCluster(
            options={
                "maxClusterRadius": 40,
                "spiderfyOnMaxZoom": True,
            }
        )
        for _, row_geo in gdf_seguranca.iterrows():
            if row_geo["geom"] is not None:
                ponto_central = row_geo["geom"].centroid
                coord = [ponto_central.y, ponto_central.x]

                nome_seg = row_geo.get("seg_unidad", "Não Informado")
                endereco_seg = row_geo.get("seg_endere", "Não Informado")
                orgao_seg = row_geo.get("seg_orgao", "Não Informado")

                popup_text = f"<small><b>{nome_seg}</b><br>{endereco_seg}<br><b>{orgao_seg}</b></small>"

                folium.Marker(
                    location=coord,
                    icon=BeautifyIcon(
                        icon="shield-halved",
                        iconSize=[30, 30],
                        prefix="fa",
                        icon_shape="circle",
                        background_color="#B22222",
                        border_color="#000000",
                        border_width=1,
                        text_color="#FFFFFF",
                    ),
                    popup=popup_text,
                    tooltip=f"<small>EQUIP. SEGURANÇA: {orgao_seg}</small>",
                ).add_to(cluster_seguranca)
        cluster_seguranca.add_to(camada_seguranca)
        camada_seguranca.add_to(m)

    # ==========================================
    # CAMADA: EQUIPAMENTOS DE SAÚDE
    # ==========================================
    if gdf_saude is not None and not gdf_saude.empty:
        camada_saude = folium.FeatureGroup(name="Equipamentos de Saúde", show=False)
        cluster_saude = MarkerCluster(
            options={
                "maxClusterRadius": 40,
                "spiderfyOnMaxZoom": True,
            }
        )
        for _, row_geo in gdf_saude.iterrows():
            if row_geo["geom"] is not None:
                ponto_central = row_geo["geom"].centroid
                coord = [ponto_central.y, ponto_central.x]

                nome_eq = row_geo.get("sau_nome", "Não Informado")
                endereco_eq = row_geo.get("sau_endere", "Não Informado")
                tipo_eq = row_geo.get("sau_tipo", "Não Informado")

                popup_text = f"<small><b>{nome_eq}</b><br>{endereco_eq}<br><b>Tipo:</b><br>{tipo_eq}</small>"

                folium.Marker(
                    location=coord,
                    icon=BeautifyIcon(
                        icon="user-doctor",
                        iconSize=[30, 30],
                        prefix="fa",
                        icon_shape="circle",
                        background_color="#B0E0E6",
                        border_color="#000000",
                        border_width=1,
                        text_color="#FFFFFF",
                    ),
                    popup=popup_text,
                    tooltip=f"<small>EQUIP. SAÚDE: {tipo_eq}</small>",
                ).add_to(cluster_saude)
        cluster_saude.add_to(camada_saude)
        camada_saude.add_to(m)

    # --- 3. RENDERIZAÇÃO DAS ESCOLAS FILTRADAS (Azul Identidade) ---
    if not df_filtrado.empty:
        camada_escolas = folium.FeatureGroup(name="Escolas Selecionadas", show=True)
        cluster_escolas = MarkerCluster(
            options={
                "maxClusterRadius": 35,
                "spiderfyOnMaxZoom": True,
            }
        )
        for _, row in df_filtrado.iterrows():
            mapa_cores_localizacao = {
                "Urbana": "#1f5d8d",
                "Rural": "#006400",
            }
            color_marker = mapa_cores_localizacao.get(row["Localização"], "#515151")
            popup_text = f"<small><b>{row['Escola']}</b><br>{row['Endereço']}<br><b>Localização:</b><br>{row['Localização']}<br><b>Rede:</b><br>{row['Dependência Administrativa']}</small>"
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
                popup=popup_text,
            ).add_to(cluster_escolas)
        cluster_escolas.add_to(camada_escolas)
        camada_escolas.add_to(m)

    # --- CONTROLE INTERATIVO DE CAMADAS ---
    folium.LayerControl(position="topright", collapsed=False).add_to(m)

    st_folium(m, width="100%", height=900, returned_objects=[])


if __name__ == "__main__":
    render_atratividade_map()
