import streamlit as st
import folium
import pandas as pd
from streamlit_folium import st_folium
from app.modules.data_utils import load_data_from_postgres, resolve_municipio_column

# FIX: Criar módulo para essa função e adaptar ao workability
# Por enquanto ela não calcula nada. e enfeia o mapa todo.
def get_urban_radius_logic(porte):
    """
    Retorna o raio estimado e a justificativa baseada na proposta urbanística.
    """
    # FIX: Não exite porte PEQUENO/MÉDIO/GRANDE no banco de dados... 
    porte = str(porte).upper()
    if "PEQUENO" in porte:
        return 400, "Caminhada de 5-7 min (Ideal para Educação Infantil/Bairros Densos)"
    elif "MÉDIO" in porte or "MEDIO" in porte:
        return 900, "Caminhada de 10-12 min (Padrão Fundamental I)"
    elif "GRANDE" in porte:
        return 1750, "Atendimento de Bairro/Áreas Adjacentes (Ensino Médio)"
    else:
        # Categoria Especial ou não identificada
        return 3000, "Escola de Referência/Técnica (Uso de transporte público/escolar)"

def render_radius_map():
    st.set_page_config(layout="wide", page_title="Mapa de Raios - EducaMap")
    
    st.markdown("""
        <style>
        .map-header { color: #1F5D8D; font-weight: bold; }
        .legend-box { background-color: #f9f9f9; color:black; padding: 10px; border-radius: 5px; border: 1px solid #ddd; }
        </style>
        <h2 class="map-header">Análise de Abrangência Escolar (Walkability)</h2>
    """, unsafe_allow_html=True)

    # Carregar dados
    try:
        df = load_data_from_postgres()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return

    # Sidebar
    st.sidebar.header("Configurações de Abrangência")
    municipio_col = resolve_municipio_column(df)
    
    selected_municipios = []
    if municipio_col:
        municipios = sorted(df[municipio_col].dropna().unique())
        selected_municipios = st.sidebar.multiselect("Municípios", municipios, default=municipios)

    # Filtro de Porte
    portes_disponiveis = sorted(df['Porte da Escola'].dropna().unique())
    selected_portes = st.sidebar.multiselect("Porte da Escola", portes_disponiveis, default=portes_disponiveis)

    # Aplicação dos filtros
    mask = df['Porte da Escola'].isin(selected_portes)
    if selected_municipios and municipio_col:
        mask &= df[municipio_col].isin(selected_municipios)
    
    filtered_df = df[mask].copy()

    if filtered_df.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    # Layout: Mapa + Legenda explicativa
    col_map, col_info = st.columns([4, 1])

    with col_info:
        st.markdown("### Critérios Urbanos")
        st.markdown("""
        <div class="legend-box">
            <small><b>Pequeno:</b> 300-500m</small><br>
            <small><b>Médio:</b> 800-1000m</small><br>
            <small><b>Grande:</b> 1.5-2km</small><br>
            <small><b>Especial:</b> 3km+</small>
        </div>
        """, unsafe_allow_html=True)
        st.info("O raio representa a área de influência por caminhada ou transporte.")

    with col_map:
        # Centro do Mapa
        m = folium.Map(
            location=[filtered_df["Latitude"].mean(), filtered_df["Longitude"].mean()],
            zoom_start=12,
            tiles="OpenStreetMap"
        )

        for _, row in filtered_df.iterrows():
            # FIX: Preparar e passar a coluna que conste os dados relativos ao porte.
            radius_m, justificativa = get_urban_radius_logic(row['Porte da Escola'])
            # NOTE: Medio -> azul; Pequeno -> verde; Grande -> laranja.
            # Cor baseada no porte para facilitar visualização
            # Mapeamento de cores e nomes de cores do Folium para os ícones
            if "PEQUENO" in str(row['Porte da Escola']).upper():
                hex_color = "#5fd819"
                icon_color = "green"
            elif "GRANDE" in str(row['Porte da Escola']).upper():
                hex_color = "#ff8e1d"
                icon_color = "orange"
            elif "ESPECIAL" in str(row['Porte da Escola']).upper():
                hex_color = "#d7191c"
                icon_color = "red"
            else:
                hex_color = "#1F5D8D" # Médio
                icon_color = "blue"

            # Desenhar o raio de abrangência
            folium.Circle(
                location=[row["Latitude"], row["Longitude"]],
                radius=radius_m,
                color=hex_color,
                fill=True,
                fill_opacity=0.15,
                weight=1,
                popup=folium.Popup(f"""
                    <b>Escola:</b> {row['Escola']}<br>
                    <b>Porte:</b> {row['Porte da Escola']}<br>
                    <b>Raio:</b> {radius_m}m<br>
                    <b>Justificativa:</b> {justificativa}
                """, max_width=300)
            ).add_to(m)

            # Marcador central
            folium.Marker(
                location=[row["Latitude"], row["Longitude"]],
                radius=2,
                color="black",
                fill=True,
                fill_color="black",
                icon=folium.Icon(color=icon_color, icon="graduation-cap", prefix="fa")
            ).add_to(m)

        st_folium(m, width="100%", height=600, returned_objects=[])

if __name__ == "__main__":
    render_radius_map()
