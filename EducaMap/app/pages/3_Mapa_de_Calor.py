import streamlit as st
from app.modules.data_utils import load_data_from_postgres, resolve_municipio_column
from app.modules.tab_heatmap import render_heatmap_tab

def render_heatmap_page():
    st.set_page_config(layout="wide", page_title="Mapa de Calor - EducaMap")

    st.markdown("""
        <style>
        .map-header { color: #1F5D8D; font-weight: bold; }
        </style>
        <h2 class="map-header">Densidade de Matrículas (Heatmap)</h2>
    """, unsafe_allow_html=True)

    # 1. Carregamento de Dados do Postgres
    try:
        df = load_data_from_postgres() #
    except Exception as e:
        st.error(f"Erro ao carregar dados do banco: {e}")
        return

    if df.empty:
        st.warning("Não há dados disponíveis para gerar o mapa de calor.")
        return

    # 2. Sidebar - Filtros e Configurações (Reaproveitado do seu main.py original)
    st.sidebar.header("Filtros de Região")
    municipio_col = resolve_municipio_column(df) #
    
    selected_municipios = []
    if municipio_col:
        municipios = sorted(df[municipio_col].dropna().unique())
        selected_municipios = st.sidebar.multiselect("Municípios", municipios, default=municipios)

    # Aplicação de filtros
    filtered_df = df.copy()
    if selected_municipios and municipio_col:
        filtered_df = filtered_df[filtered_df[municipio_col].isin(selected_municipios)]

    # 3. Configurações Específicas do Heatmap
    st.sidebar.header("Ajustes do Mapa")
    blur = st.sidebar.slider("Intensidade (Blur)", min_value=5, max_value=40, value=18)
    min_opacity = st.sidebar.slider("Opacidade Mínima", min_value=0.0, max_value=1.0, value=0.2, step=0.05)

    # 4. Preparação e Renderização
    if not filtered_df.empty:
        # Filtrar apenas as que possuem peso de capacidade calculado
        heatmap_df = filtered_df.dropna(subset=["capacity_weight"]).copy()
        
        center_lat = filtered_df["Latitude"].mean()
        center_lon = filtered_df["Longitude"].mean()

        # Chamada da função modularizada que você já possui
        render_heatmap_tab(
            heatmap_df=heatmap_df,
            center_lat=center_lat,
            center_lon=center_lon,
            blur=blur,
            min_opacity=min_opacity
        )
    else:
        st.info("Ajuste os filtros para visualizar o calor das matrículas.")

if __name__ == "__main__":
    render_heatmap_page()
