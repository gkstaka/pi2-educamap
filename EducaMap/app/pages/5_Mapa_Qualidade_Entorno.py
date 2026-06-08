import streamlit as st
import pandas as pd
import folium
import geopandas as gpd
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from app.modules.data_utils import (
    load_qualidade_entorno_por_ra,
    load_qualidade_entorno_por_escola,
    load_distancia_onibus_osm_por_escola,
    load_quadrante_acesso_onibus_entorno,
    load_oferta_qualidade_por_ra,
    load_escolas_contexto_entorno,
    load_distancia_transporte_por_escola,
    load_paradas_onibus_osm,
    load_linhas_onibus_osm,
)
from app.utils.model import engine


def _nome_escola(row):
    nome = row.get("nome_escola")
    if nome is not None and pd.notna(nome) and str(nome).strip():
        return str(nome)
    return f"Escola {row['id_escola']}"


@st.cache_data(ttl=3600)
def carregar_regioes_administrativas():
    try:
        gdf = gpd.read_postgis(
            "SELECT ra_nome, geom FROM regioes_administrativas", con=engine, geom_col="geom"
        )
        return gdf
    except Exception as e:
        st.error(f"Erro ao carregar Regiões Administrativas do PostGIS: {e}")
        return None


def render_mapa_qualidade_entorno():
    st.set_page_config(layout="wide", page_title="Mapa de Qualidade do Entorno - EducaMap")

    st.markdown(
        "<h2 style='color:#1F5D8D; font-weight:bold;'>Mapa de Qualidade do Entorno Escolar</h2>",
        unsafe_allow_html=True,
    )

    tipo_mapa = st.radio(
        "Tipo de mapa",
        [
            "Região Administrativa",
            "Heatmap por escola",
            "Oferta × Qualidade do Entorno",
            "Urbano × Rural (acessibilidade)",
            "Rede de Ensino × Entorno",
            "Porte da Escola × Entorno",
            "Transporte Público (Metrô/BRT/Terminais)",
            "Transporte Coletivo (Paradas e Linhas de Ônibus - OSM)",
        ],
        horizontal=True,
        key="tipo_mapa_qualidade_entorno",
    )

    if tipo_mapa == "Região Administrativa":
        _render_mapa_coropletico()
    elif tipo_mapa == "Heatmap por escola":
        _render_mapa_heatmap()
    elif tipo_mapa == "Oferta × Qualidade do Entorno":
        _render_mapa_oferta_qualidade()
    elif tipo_mapa == "Urbano × Rural (acessibilidade)":
        _render_mapa_urbano_rural()
    elif tipo_mapa == "Rede de Ensino × Entorno":
        _render_mapa_rede_entorno()
    elif tipo_mapa == "Porte da Escola × Entorno":
        _render_mapa_porte_entorno()
    elif tipo_mapa == "Transporte Público (Metrô/BRT/Terminais)":
        _render_mapa_transporte()
    else:
        _render_mapa_onibus_osm()


def _render_mapa_coropletico():
    st.caption(
        "Mapa coroplético do Distrito Federal: cada Região Administrativa é colorida pelo "
        "Índice de Qualidade do Entorno Escolar (0–100), que combina o Índice de Infraestrutura "
        "(quantidade de equipamentos públicos por escola) com o Índice de Acessibilidade "
        "(distância média até o equipamento mais próximo). Quanto mais verde, melhor o entorno "
        "escolar da região; quanto mais vermelho, maior a carência relativa."
    )

    with st.spinner("Calculando índice combinado e carregando geometrias via PostGIS…"):
        df_qualidade = load_qualidade_entorno_por_ra()
        gdf_ra = carregar_regioes_administrativas()

    if df_qualidade is None or df_qualidade.empty or gdf_ra is None or gdf_ra.empty:
        st.info("Dados geoespaciais não disponíveis ou PostGIS não acessível.")
        return

    gdf = gdf_ra.merge(df_qualidade, on="ra_nome", how="inner")

    m = folium.Map(location=[-15.793889, -47.882778], zoom_start=10, tiles="OpenStreetMap")

    folium.Choropleth(
        geo_data=gdf,
        data=gdf,
        columns=["ra_nome", "indice_qualidade_entorno"],
        key_on="feature.properties.ra_nome",
        fill_color="RdYlGn",
        fill_opacity=0.75,
        line_opacity=0.6,
        line_color="#113c5e",
        legend_name="Índice de Qualidade do Entorno Escolar (0–100)",
        nan_fill_color="#cccccc",
    ).add_to(m)

    folium.GeoJson(
        gdf,
        name="Regiões Administrativas",
        style_function=lambda feature: {"fillOpacity": 0, "color": "transparent", "weight": 0},
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "ra_nome",
                "indice_qualidade_entorno",
                "indice_infraestrutura",
                "indice_acessibilidade",
            ],
            aliases=[
                "Região Administrativa:",
                "Índice de Qualidade do Entorno:",
                "Índice de Infraestrutura:",
                "Índice de Acessibilidade:",
            ],
            localize=True,
        ),
    ).add_to(m)

    st_folium(m, width="100%", height=750, returned_objects=[])

    st.divider()
    st.subheader("Ranking das Regiões Administrativas")
    st.dataframe(
        df_qualidade.rename(
            columns={
                "ra_nome": "Região Administrativa",
                "indice_qualidade_entorno": "Índice de Qualidade do Entorno",
                "indice_infraestrutura": "Índice de Infraestrutura",
                "indice_acessibilidade": "Índice de Acessibilidade",
            }
        )[
            [
                "Região Administrativa",
                "Índice de Qualidade do Entorno",
                "Índice de Infraestrutura",
                "Índice de Acessibilidade",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


def _render_mapa_heatmap():
    st.caption(
        "Versão mais granular do mapa de qualidade do entorno: em vez de agregar por Região "
        "Administrativa, cada escola contribui individualmente com seu próprio Índice de "
        "Acessibilidade (0–100), calculado pela distância até o equipamento mais próximo de "
        "cada categoria (saúde, segurança, parques, cultura, esporte/lazer, espaços comunitários "
        "e feiras livres). O heatmap interpola esses valores no espaço, revelando focos de boa "
        "ou má cobertura mesmo dentro de uma mesma RA."
    )

    with st.spinner("Calculando índice de acessibilidade por escola via PostGIS…"):
        df_escolas = load_qualidade_entorno_por_escola()

    if df_escolas is None or df_escolas.empty:
        st.info("Dados geoespaciais não disponíveis ou PostGIS não acessível.")
        return

    heat_data = df_escolas[["latitude", "longitude", "indice_qualidade_entorno"]].dropna().values.tolist()

    m = folium.Map(location=[-15.793889, -47.882778], zoom_start=10, tiles="OpenStreetMap", control_scale=True)
    HeatMap(
        heat_data,
        radius=22,
        blur=20,
        min_opacity=0.3,
        max_zoom=14,
        gradient={
            0.10: "#d7191c",  # baixo índice = pior entorno (vermelho)
            0.35: "#ff8e1d",
            0.55: "#F4D03F",
            0.75: "#5fd819",
            1.00: "#1a9641",  # alto índice = melhor entorno (verde)
        },
    ).add_to(m)

    st_folium(m, width="100%", height=750, returned_objects=[])

    st.divider()
    st.subheader("Escolas com pior e melhor entorno (por índice de acessibilidade)")
    col1, col2 = st.columns(2)
    cols_exibir = ["id_escola", "indice_qualidade_entorno", "distancia_media_m"]
    renomear = {
        "id_escola": "Escola",
        "indice_qualidade_entorno": "Índice de Acessibilidade",
        "distancia_media_m": "Distância média (m)",
    }
    with col1:
        st.caption("10 escolas com entorno menos acessível")
        st.dataframe(
            df_escolas.nsmallest(10, "indice_qualidade_entorno")[cols_exibir].rename(columns=renomear),
            use_container_width=True,
            hide_index=True,
        )
    with col2:
        st.caption("10 escolas com entorno mais acessível")
        st.dataframe(
            df_escolas.nlargest(10, "indice_qualidade_entorno")[cols_exibir].rename(columns=renomear),
            use_container_width=True,
            hide_index=True,
        )


def _render_mapa_oferta_qualidade():
    st.caption(
        "Cruza, por Região Administrativa, a **Oferta de Capacidade Estimada** (soma da "
        "capacidade de matrícula das escolas) com o **Índice de Qualidade do Entorno Escolar** "
        "(0–100). O mapa de fundo mostra a qualidade do entorno (verde = melhor, vermelho = pior); "
        "os círculos, centrados em cada RA, têm tamanho proporcional à capacidade de vagas. "
        "Círculos grandes sobre áreas avermelhadas indicam **regiões que concentram muitas vagas "
        "mas têm pouca infraestrutura ao redor** — um possível desalinhamento de planejamento. "
        "Círculos pequenos sobre áreas esverdeadas indicam o oposto: bom entorno, mas pouca oferta."
    )

    with st.spinner("Cruzando oferta de capacidade e qualidade do entorno via PostGIS…"):
        df_cruz = load_oferta_qualidade_por_ra()
        gdf_ra = carregar_regioes_administrativas()

    if df_cruz is None or df_cruz.empty or gdf_ra is None or gdf_ra.empty:
        st.info("Dados geoespaciais não disponíveis ou PostGIS não acessível.")
        return

    gdf = gdf_ra.merge(df_cruz, on="ra_nome", how="inner")
    centroides = gdf.geometry.centroid

    m = folium.Map(location=[-15.793889, -47.882778], zoom_start=10, tiles="OpenStreetMap")

    folium.Choropleth(
        geo_data=gdf,
        data=gdf,
        columns=["ra_nome", "indice_qualidade_entorno"],
        key_on="feature.properties.ra_nome",
        fill_color="RdYlGn",
        fill_opacity=0.6,
        line_opacity=0.6,
        line_color="#113c5e",
        legend_name="Índice de Qualidade do Entorno Escolar (0–100)",
        nan_fill_color="#cccccc",
    ).add_to(m)

    cap_min, cap_max = gdf["capacidade_total"].min(), gdf["capacidade_total"].max()

    def raio_px(capacidade):
        if cap_max > cap_min:
            return 8 + (capacidade - cap_min) / (cap_max - cap_min) * 27
        return 18

    cores_quadrante = {
        "Oferta alta + entorno bom": "#1a9641",
        "Oferta alta + entorno fraco": "#d7191c",
        "Oferta baixa + entorno bom": "#2b83ba",
        "Oferta baixa + entorno fraco": "#fdae61",
    }

    for (_, row), centroide in zip(gdf.iterrows(), centroides):
        folium.CircleMarker(
            location=[centroide.y, centroide.x],
            radius=raio_px(row["capacidade_total"]),
            color="#113c5e",
            weight=1.5,
            fill=True,
            fill_color=cores_quadrante.get(row["quadrante"], "#777777"),
            fill_opacity=0.85,
            tooltip=folium.Tooltip(
                f"<b>{row['ra_nome']}</b><br>"
                f"Capacidade total: {row['capacidade_total']:,.0f} vagas<br>"
                f"Índice de Qualidade do Entorno: {row['indice_qualidade_entorno']:.1f}<br>"
                f"Classificação: {row['quadrante']}".replace(",", "."),
            ),
        ).add_to(m)

    st_folium(m, width="100%", height=750, returned_objects=[])

    st.markdown(
        "**Legenda dos círculos (quadrantes pela mediana de cada métrica):** "
        "🟢 Oferta alta + entorno bom &nbsp;|&nbsp; "
        "🔴 Oferta alta + entorno fraco (alerta) &nbsp;|&nbsp; "
        "🔵 Oferta baixa + entorno bom &nbsp;|&nbsp; "
        "🟠 Oferta baixa + entorno fraco (mais vulnerável)"
    )

    st.divider()
    st.subheader("Regiões Administrativas por quadrante")
    st.dataframe(
        df_cruz.rename(
            columns={
                "ra_nome": "Região Administrativa",
                "capacidade_total": "Capacidade Total",
                "capacidade_por_escola": "Capacidade/Escola",
                "indice_qualidade_entorno": "Índice de Qualidade do Entorno",
                "quadrante": "Classificação",
            }
        )[
            [
                "Região Administrativa",
                "Capacidade Total",
                "Capacidade/Escola",
                "Índice de Qualidade do Entorno",
                "Classificação",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


def _render_mapa_urbano_rural():
    st.caption(
        "Mostra cada escola individualmente, colorida pela sua **localização** "
        "(Urbana ou Rural) e dimensionada pela **distância média até os equipamentos "
        "públicos do entorno** — quanto maior o círculo, mais distante a escola está "
        "dos equipamentos de saúde, segurança, cultura, esporte/lazer, parques, "
        "espaços comunitários e feiras livres. Permite verificar visualmente se as "
        "escolas rurais tendem a ficar mais isoladas dos equipamentos urbanos."
    )

    with st.spinner("Cruzando localização urbana/rural com acessibilidade do entorno via PostGIS…"):
        df_ctx = load_escolas_contexto_entorno()

    if df_ctx is None or df_ctx.empty:
        st.info("Dados geoespaciais não disponíveis ou PostGIS não acessível.")
        return

    df_pontos = df_ctx.dropna(subset=["latitude", "longitude", "localizacao", "distancia_media_m"])

    dist_min, dist_max = df_pontos["distancia_media_m"].min(), df_pontos["distancia_media_m"].max()

    def raio_px(distancia):
        if dist_max > dist_min:
            return 3 + (distancia - dist_min) / (dist_max - dist_min) * 12
        return 6

    cores_localizacao = {"Urbana": "#2b83ba", "Rural": "#fdae61"}

    m = folium.Map(location=[-15.793889, -47.882778], zoom_start=10, tiles="OpenStreetMap")

    for _, row in df_pontos.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=raio_px(row["distancia_media_m"]),
            color="#113c5e",
            weight=0.8,
            fill=True,
            fill_color=cores_localizacao.get(row["localizacao"], "#777777"),
            fill_opacity=0.75,
            tooltip=folium.Tooltip(
                f"<b>{_nome_escola(row)}</b><br>"
                f"Localização: {row['localizacao']}<br>"
                f"RA: {row['ra_nome']}<br>"
                f"Distância média ao entorno: {row['distancia_media_m']:.0f} m".replace(",", "."),
            ),
        ).add_to(m)

    st_folium(m, width="100%", height=750, returned_objects=[])

    st.markdown(
        "**Legenda:** 🔵 Urbana &nbsp;|&nbsp; 🟠 Rural — "
        "círculos maiores indicam escolas mais distantes, em média, dos equipamentos do entorno."
    )

    st.divider()
    st.subheader("Distância média ao entorno por localização")
    resumo = (
        df_pontos.groupby("localizacao")["distancia_media_m"]
        .agg(["count", "mean", "median"])
        .rename(columns={"count": "Nº de escolas", "mean": "Distância média (m)", "median": "Distância mediana (m)"})
        .rename_axis("Localização")
        .reset_index()
    )
    st.dataframe(resumo, use_container_width=True, hide_index=True)


def _render_mapa_rede_entorno():
    st.caption(
        "Mostra cada escola colorida pela **rede de ensino** (Pública Estadual, "
        "Pública Federal ou Privada) sobre o mapa de fundo do **Índice de Qualidade "
        "do Entorno** por Região Administrativa. Ajuda a identificar se redes "
        "específicas se concentram em regiões com entorno mais ou menos favorável."
    )

    with st.spinner("Cruzando rede de ensino com qualidade do entorno via PostGIS…"):
        df_ctx = load_escolas_contexto_entorno()
        gdf_ra = carregar_regioes_administrativas()
        df_qual_ra = load_qualidade_entorno_por_ra()

    if (
        df_ctx is None or df_ctx.empty
        or gdf_ra is None or gdf_ra.empty
        or df_qual_ra is None or df_qual_ra.empty
    ):
        st.info("Dados geoespaciais não disponíveis ou PostGIS não acessível.")
        return

    df_pontos = df_ctx.dropna(subset=["latitude", "longitude", "tipo_rede"])
    gdf = gdf_ra.merge(df_qual_ra, on="ra_nome", how="inner")

    m = folium.Map(location=[-15.793889, -47.882778], zoom_start=10, tiles="OpenStreetMap")

    folium.Choropleth(
        geo_data=gdf,
        data=gdf,
        columns=["ra_nome", "indice_qualidade_entorno"],
        key_on="feature.properties.ra_nome",
        fill_color="RdYlGn",
        fill_opacity=0.55,
        line_opacity=0.6,
        line_color="#113c5e",
        legend_name="Índice de Qualidade do Entorno Escolar (0–100)",
        nan_fill_color="#cccccc",
    ).add_to(m)

    cores_rede = {
        "Estadual": "#1a9641",
        "Federal": "#2b83ba",
        "Privada": "#d7191c",
    }

    for _, row in df_pontos.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            color="#113c5e",
            weight=0.8,
            fill=True,
            fill_color=cores_rede.get(row["tipo_rede"], "#777777"),
            fill_opacity=0.8,
            tooltip=folium.Tooltip(
                f"<b>{_nome_escola(row)}</b><br>"
                f"Rede: {row['tipo_rede']}<br>"
                f"RA: {row['ra_nome']}<br>"
                f"Índice de Qualidade do Entorno (RA): {row['indice_qualidade_ra']:.1f}".replace(",", "."),
            ),
        ).add_to(m)

    st_folium(m, width="100%", height=750, returned_objects=[])

    st.markdown(
        "**Legenda dos pontos:** 🟢 Rede Pública Estadual &nbsp;|&nbsp; "
        "🔵 Rede Pública Federal &nbsp;|&nbsp; 🔴 Rede Privada — "
        "o fundo colorido mostra o Índice de Qualidade do Entorno da Região Administrativa."
    )

    st.divider()
    st.subheader("Índice de Qualidade do Entorno (RA) por rede de ensino")
    resumo = (
        df_pontos.groupby("tipo_rede")["indice_qualidade_ra"]
        .agg(["count", "mean", "median"])
        .rename(columns={"count": "Nº de escolas", "mean": "Índice médio", "median": "Índice mediano"})
        .rename_axis("Rede de Ensino")
        .reset_index()
    )
    st.dataframe(resumo, use_container_width=True, hide_index=True)


PORTE_LABELS = {
    "Escola sem matrícula de escolarização": "Sem matrícula",
    "Até 50 matrículas de escolarização": "Até 50",
    "Entre 51 e 200 matrículas de escolarização": "51–200",
    "Entre 201 e 500 matrículas de escolarização": "201–500",
    "Entre 501 e 1000 matrículas de escolarização": "501–1000",
    "Mais de 1000 matrículas de escolarização": "+1000",
}

PORTE_CORES = {
    "Sem matrícula": "#cccccc",
    "Até 50": "#2b83ba",
    "51–200": "#abdda4",
    "201–500": "#ffffbf",
    "501–1000": "#fdae61",
    "+1000": "#d7191c",
}


def _render_mapa_porte_entorno():
    st.caption(
        "Mostra cada escola colorida pelo seu **porte** (faixa de número de matrículas) "
        "sobre o mapa de fundo do **Índice de Qualidade do Entorno** por Região "
        "Administrativa. Indica se escolas maiores tendem a se concentrar em regiões "
        "com entorno melhor ou pior — um possível sinal de como o planejamento de "
        "novas unidades considerou (ou não) a infraestrutura ao redor."
    )

    with st.spinner("Cruzando porte das escolas com qualidade do entorno via PostGIS…"):
        df_ctx = load_escolas_contexto_entorno()
        gdf_ra = carregar_regioes_administrativas()
        df_qual_ra = load_qualidade_entorno_por_ra()

    if (
        df_ctx is None or df_ctx.empty
        or gdf_ra is None or gdf_ra.empty
        or df_qual_ra is None or df_qual_ra.empty
    ):
        st.info("Dados geoespaciais não disponíveis ou PostGIS não acessível.")
        return

    df_pontos = df_ctx.dropna(subset=["latitude", "longitude", "porte_escola"]).copy()
    df_pontos["Porte"] = df_pontos["porte_escola"].map(lambda x: PORTE_LABELS.get(str(x), str(x)))
    gdf = gdf_ra.merge(df_qual_ra, on="ra_nome", how="inner")

    m = folium.Map(location=[-15.793889, -47.882778], zoom_start=10, tiles="OpenStreetMap")

    folium.Choropleth(
        geo_data=gdf,
        data=gdf,
        columns=["ra_nome", "indice_qualidade_entorno"],
        key_on="feature.properties.ra_nome",
        fill_color="RdYlGn",
        fill_opacity=0.55,
        line_opacity=0.6,
        line_color="#113c5e",
        legend_name="Índice de Qualidade do Entorno Escolar (0–100)",
        nan_fill_color="#cccccc",
    ).add_to(m)

    for _, row in df_pontos.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=5,
            color="#113c5e",
            weight=0.8,
            fill=True,
            fill_color=PORTE_CORES.get(row["Porte"], "#777777"),
            fill_opacity=0.8,
            tooltip=folium.Tooltip(
                f"<b>{_nome_escola(row)}</b><br>"
                f"Porte: {row['Porte']}<br>"
                f"RA: {row['ra_nome']}<br>"
                f"Índice de Qualidade do Entorno (RA): {row['indice_qualidade_ra']:.1f}".replace(",", "."),
            ),
        ).add_to(m)

    st_folium(m, width="100%", height=750, returned_objects=[])

    legenda_html = " &nbsp;|&nbsp; ".join(
        f"<span style='color:{cor}'>●</span> {porte}" for porte, cor in PORTE_CORES.items()
    )
    st.markdown(f"**Legenda dos pontos (porte da escola):** {legenda_html}", unsafe_allow_html=True)
    st.caption("O fundo colorido mostra o Índice de Qualidade do Entorno da Região Administrativa (verde = melhor, vermelho = pior).")

    st.divider()
    st.subheader("Índice de Qualidade do Entorno (RA) por porte da escola")
    ordem_porte = [PORTE_LABELS[p] for p in PORTE_LABELS if PORTE_LABELS[p] in df_pontos["Porte"].unique()]
    resumo = (
        df_pontos.groupby("Porte")["indice_qualidade_ra"]
        .agg(["count", "mean", "median"])
        .reindex(ordem_porte)
        .rename(columns={"count": "Nº de escolas", "mean": "Índice médio", "median": "Índice mediano"})
        .rename_axis("Porte da Escola")
        .reset_index()
    )
    st.dataframe(resumo, use_container_width=True, hide_index=True)


CORES_TIPO_TRANSPORTE = {
    "ESTAÇÃO METRÔ": "#2b83ba",
    "ESTAÇÃO BRT": "#1a9641",
    "TERMINAIS DFTRANS": "#fdae61",
}


def _render_mapa_transporte():
    st.caption(
        "Cruza a localização das escolas com a rede de **transporte público de alta "
        "capacidade do DF** (estações de metrô, BRT e terminais DFTrans, dados do "
        "Geoportal IDE-DF/SEDUH). Os losangos coloridos marcam as estações/terminais; "
        "os círculos marcam as escolas, coloridos por **distância até o ponto de "
        "transporte mais próximo** — quanto mais avermelhado, mais distante a escola "
        "está da rede estrutural de transporte coletivo."
    )

    with st.spinner("Calculando distância das escolas até estações/terminais de transporte via PostGIS…"):
        df_dist = load_distancia_transporte_por_escola()
        gdf_estacoes = gpd.read_postgis(
            "SELECT tipo, nome, situacao, geom FROM estacoes_terminais_transporte",
            con=engine, geom_col="geom",
        )

    if df_dist is None or df_dist.empty or gdf_estacoes is None or gdf_estacoes.empty:
        st.info("Dados geoespaciais não disponíveis ou PostGIS não acessível.")
        return

    df_pontos = df_dist.dropna(subset=["latitude", "longitude", "distancia_transporte_m"])

    dist_min, dist_max = df_pontos["distancia_transporte_m"].min(), df_pontos["distancia_transporte_m"].max()

    def cor_distancia(distancia):
        if dist_max > dist_min:
            t = (distancia - dist_min) / (dist_max - dist_min)
        else:
            t = 0.5
        if t < 0.33:
            return "#1a9641"
        elif t < 0.66:
            return "#fdae61"
        return "#d7191c"

    m = folium.Map(location=[-15.793889, -47.882778], zoom_start=10, tiles="OpenStreetMap")

    for _, row in gdf_estacoes.iterrows():
        folium.RegularPolygonMarker(
            location=[row["geom"].y, row["geom"].x],
            number_of_sides=4,
            radius=8,
            rotation=45,
            color="#113c5e",
            weight=1.2,
            fill=True,
            fill_color=CORES_TIPO_TRANSPORTE.get(row["tipo"], "#777777"),
            fill_opacity=0.9,
            popup=folium.Popup(
                f"<b>{row['nome'] if row['nome'] else row['tipo'].title()}</b><br>"
                f"Tipo: {row['tipo'].title()}<br>"
                f"Situação: {row['situacao'] or '—'}",
                max_width=250,
            ),
        ).add_to(m)

    for _, row in df_pontos.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=4,
            color="#113c5e",
            weight=0.6,
            fill=True,
            fill_color=cor_distancia(row["distancia_transporte_m"]),
            fill_opacity=0.7,
            tooltip=folium.Tooltip(
                f"<b>{_nome_escola(row)}</b><br>"
                f"Distância até o transporte mais próximo: {row['distancia_transporte_m']:.0f} m<br>"
                f"Ponto mais próximo: {row['estacao_mais_proxima'] or row['tipo_estacao'].title()} "
                f"({row['tipo_estacao'].title()})".replace(",", "."),
            ),
        ).add_to(m)

    st_folium(m, width="100%", height=750, returned_objects=[])

    st.markdown(
        "**Legenda das estações/terminais (losangos):** "
        "🔵 Estação de Metrô &nbsp;|&nbsp; 🟢 Estação de BRT &nbsp;|&nbsp; 🟠 Terminal DFTrans<br>"
        "**Legenda das escolas (círculos, por distância ao transporte mais próximo):** "
        "🟢 mais perto &nbsp;|&nbsp; 🟠 intermediário &nbsp;|&nbsp; 🔴 mais distante",
        unsafe_allow_html=True,
    )

    st.divider()
    st.subheader("Escolas mais distantes e mais próximas da rede de transporte")
    col1, col2 = st.columns(2)
    cols_exibir = ["nome_escola_exibicao", "distancia_transporte_m", "estacao_mais_proxima", "tipo_estacao"]
    renomear = {
        "nome_escola_exibicao": "Escola",
        "distancia_transporte_m": "Distância (m)",
        "estacao_mais_proxima": "Ponto mais próximo",
        "tipo_estacao": "Tipo",
    }
    df_exibicao = df_pontos.copy()
    df_exibicao["nome_escola_exibicao"] = df_exibicao.apply(_nome_escola, axis=1)
    df_exibicao["estacao_mais_proxima"] = df_exibicao["estacao_mais_proxima"].fillna("—")
    df_exibicao["tipo_estacao"] = df_exibicao["tipo_estacao"].str.title()
    with col1:
        st.caption("10 escolas mais distantes do transporte estruturante")
        st.dataframe(
            df_exibicao.nlargest(10, "distancia_transporte_m")[cols_exibir].rename(columns=renomear),
            use_container_width=True,
            hide_index=True,
        )
    with col2:
        st.caption("10 escolas mais próximas do transporte estruturante")
        st.dataframe(
            df_exibicao.nsmallest(10, "distancia_transporte_m")[cols_exibir].rename(columns=renomear),
            use_container_width=True,
            hide_index=True,
        )


CORES_LINHAS_ONIBUS = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
    "#46f0f0", "#f032e6", "#bcf60c", "#fabebe", "#008080",
    "#e6beff", "#9a6324", "#800000", "#aaffc3", "#808000",
    "#000075", "#a9a9a9", "#fffac8", "#ffd8b1", "#808080",
]


def _render_mapa_onibus_osm():
    st.caption(
        "Camada complementar de transporte coletivo extraída do **OpenStreetMap** (extrato "
        "Overpass API): mostra **paradas/plataformas de ônibus** (pontos azuis) e os "
        "**traçados de linhas de ônibus** mapeados na região (linhas coloridas, uma cor por "
        "linha). Diferente do mapa anterior — focado nas estações estruturantes do "
        "Geoportal IDE-DF (metrô/BRT/terminais) — esta camada dá uma visão da malha de "
        "ônibus convencional que efetivamente passa perto das escolas."
    )

    with st.spinner("Carregando paradas, linhas de ônibus e dados das escolas via PostGIS…"):
        gdf_paradas = load_paradas_onibus_osm()
        gdf_linhas = load_linhas_onibus_osm()
        df_quadrante = load_quadrante_acesso_onibus_entorno()

    if gdf_paradas is None or gdf_paradas.empty:
        st.info("Dados de transporte coletivo (OSM) não disponíveis ou PostGIS não acessível.")
        return

    mostrar_escolas = st.checkbox(
        "🏫 Sobrepor escolas no mapa, classificadas por acesso ao ônibus × qualidade do entorno",
        value=False,
        key="onibus_osm_overlay_escolas",
    )

    m = folium.Map(location=[-15.793889, -47.882778], zoom_start=10, tiles="OpenStreetMap")

    if gdf_linhas is not None and not gdf_linhas.empty:
        for i, row in gdf_linhas.iterrows():
            cor = CORES_LINHAS_ONIBUS[i % len(CORES_LINHAS_ONIBUS)]
            nome_linha = row["nome"] or row["ref"] or f"Linha {row['id_osm']}"
            folium.GeoJson(
                row["geom"],
                style_function=lambda _f, cor=cor: {"color": cor, "weight": 3, "opacity": 0.75},
                tooltip=folium.Tooltip(f"<b>{nome_linha}</b>"),
            ).add_to(m)

    for _, row in gdf_paradas.iterrows():
        nome_parada = row["nome"] if row["nome"] else (row["tipo"] or "Parada de ônibus").replace("_", " ").title()
        folium.CircleMarker(
            location=[row["geom"].y, row["geom"].x],
            radius=3,
            color="#113c5e",
            weight=0.5,
            fill=True,
            fill_color="#2b83ba",
            fill_opacity=0.8,
            tooltip=folium.Tooltip(
                f"<b>{nome_parada}</b><br>"
                f"Tipo: {(row['tipo'] or '—').replace('_', ' ').title()}"
                + (f"<br>Ref.: {row['ref']}" if row["ref"] else "")
            ),
        ).add_to(m)

    QUADRANTE_CORES = {
        "Bom acesso + bom entorno": "#1a9641",
        "Bom acesso + entorno carente": "#8856a7",
        "Acesso ruim + bom entorno": "#fdae61",
        "Dupla desvantagem (acesso ruim + entorno carente)": "#d7191c",
    }

    legenda_escolas = ""
    if mostrar_escolas and df_quadrante is not None and not df_quadrante.empty:
        df_pts = df_quadrante.dropna(subset=["latitude", "longitude"]).copy()
        mediana_dist = df_pts.attrs.get("mediana_distancia_onibus_m", df_pts["distancia_onibus_m"].median())
        mediana_indice = df_pts.attrs.get("mediana_indice_qualidade_entorno", df_pts["indice_qualidade_entorno"].median())

        for _, row in df_pts.iterrows():
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=4,
                color="#113c5e",
                weight=0.5,
                fill=True,
                fill_color=QUADRANTE_CORES[row["quadrante"]],
                fill_opacity=0.8,
                tooltip=folium.Tooltip(
                    f"<b>{_nome_escola(row)}</b><br>"
                    f"<b>{row['quadrante']}</b><br>"
                    f"Distância até a parada de ônibus mais próxima: {row['distancia_onibus_m']:.0f} m "
                    f"(mediana do DF: {mediana_dist:.0f} m)<br>"
                    f"Índice de Qualidade do Entorno: {row['indice_qualidade_entorno']:.1f} "
                    f"(mediana do DF: {mediana_indice:.1f})"
                ),
            ).add_to(m)

        legenda_escolas = (
            "<br>**Escolas (círculos), classificadas por acesso ao ônibus × qualidade do entorno "
            "(em relação às medianas do DF):** "
            "🟢 Bom acesso + bom entorno &nbsp;|&nbsp; "
            "🟣 Bom acesso + entorno carente &nbsp;|&nbsp; "
            "🟠 Acesso ruim + bom entorno &nbsp;|&nbsp; "
            "🔴 Dupla desvantagem (acesso ruim + entorno carente)"
        )

    st_folium(m, width="100%", height=750, returned_objects=[])

    st.markdown(
        f"**Legenda:** 🔵 Paradas/plataformas de ônibus ({len(gdf_paradas)} pontos mapeados) "
        + (
            f"&nbsp;|&nbsp; 〰️ Linhas de ônibus, uma cor por linha ({len(gdf_linhas)} traçados mapeados)"
            if gdf_linhas is not None and not gdf_linhas.empty else ""
        )
        + legenda_escolas
        + "<br><span style='font-size:0.85em;color:#666;'>Fonte: OpenStreetMap, extraído via Overpass API "
        "— a cobertura de linhas mapeadas é parcial e depende do mapeamento colaborativo da comunidade OSM.</span>",
        unsafe_allow_html=True,
    )

    if df_quadrante is not None and not df_quadrante.empty:
        st.caption(
            "💡 A análise **'Transporte e educação: o acesso ao ônibus reflete a qualidade do "
            "entorno escolar?'** (dispersão, correlação, escolas em dupla desvantagem, contagem "
            "por classificação e proporção por Região Administrativa) está disponível na aba "
            "**Gráficos**, na sessão **Transporte**."
        )

    if gdf_linhas is not None and not gdf_linhas.empty:
        st.divider()
        st.subheader("Linhas de ônibus mapeadas")
        df_linhas_exibir = gdf_linhas[["nome", "ref"]].rename(
            columns={"nome": "Nome/Itinerário", "ref": "Referência"}
        )
        st.dataframe(df_linhas_exibir, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    render_mapa_qualidade_entorno()
