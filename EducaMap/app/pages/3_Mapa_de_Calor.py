import streamlit as st
from app.modules.data_utils import load_data_from_postgres, resolve_municipio_column
from app.modules.tab_heatmap import render_heatmap_tab

def render_heatmap_page():
    st.set_page_config(layout="wide", page_title="Mapa de Calor - EducaMap")

    # Injeção de CSS para layout full-screen
    st.markdown("""
        <style>
        /* Desabilita/Esconde o botão hambúrguer (controle de colapso) */
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        
        /* Remove o cabeçalho e rodapé nativos */
        header {visibility: hidden;}
        footer {visibility: hidden;}

        /* Faz o mapa ocupar 100% da área (Full Screen) */
        .block-container {
            padding: 0rem;
            margin: 0rem;
            max-width: 100%;
        }

        /* Define largura fixa para a barra lateral */
        [data-testid="stSidebar"] {
            min-width: 260px !important;
            max-width: 260px !important;
        }
        
        /* Ajusta o espaçamento interno da sidebar */
        [data-testid="stSidebar"] .stVerticalBlock {
            padding-top: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

    try:
        df = load_data_from_postgres()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return

    # --- BARRA LATERAL FIXA ---
    with st.sidebar:
        st.markdown("<h2 style='color: #1F5D8D; margin-bottom: 0;'>EducaMap</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color: #666; font-size: 0.8rem;'>Análise de Abrangência Escolar</p>", unsafe_allow_html=True)
        st.markdown("---")
    # Movemos o título e filtros para a Sidebar para liberar o mapa[cite: 15]
        st.sidebar.title("Mapa de Calor")
        st.sidebar.caption("Densidade de Matrículas por Região")
        
        municipio_col = resolve_municipio_column(df)
        selected_municipios = []
        if municipio_col:
            municipios = sorted(df[municipio_col].dropna().unique())
            selected_municipios = st.sidebar.multiselect("Municípios", municipios, default=municipios)

        st.sidebar.header("Ajustes do Mapa")
        blur = st.sidebar.slider("Intensidade (Blur)", min_value=5, max_value=40, value=18)
        min_opacity = st.sidebar.slider("Opacidade Mínima", min_value=0.0, max_value=1.0, value=0.2, step=0.05)

    filtered_df = df.copy()
    if selected_municipios and municipio_col:
        filtered_df = filtered_df[filtered_df[municipio_col].isin(selected_municipios)]

    if not filtered_df.empty:
        heatmap_df = filtered_df.dropna(subset=["capacity_weight"]).copy()
        center_lat = filtered_df["Latitude"].mean()
        center_lon = filtered_df["Longitude"].mean()

        # O componente Folium deve ser renderizado com height alto[cite: 4, 15]
        render_heatmap_tab(
            heatmap_df=heatmap_df,
            center_lat=center_lat,
            center_lon=center_lon,
            blur=blur,
            min_opacity=min_opacity
        )
    else:
        st.warning("Ajuste os filtros na barra lateral.")

if __name__ == "__main__":
    render_heatmap_page()
