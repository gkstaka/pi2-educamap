import streamlit as st
import folium
from streamlit_folium import st_folium
from app.modules.data_utils import load_data_from_postgres, resolve_municipio_column

def get_urban_radius_logic(porte):
    """Retorna o raio e a justificativa baseada no porte da escola."""
    porte = str(porte).upper()
    if "PEQUENO" in porte:
        return 400, "Caminhada de 5-7 min (Educação Infantil/Bairros Densos)"
    elif "MÉDIO" in porte or "MEDIO" in porte:
        return 900, "Caminhada de 10-12 min (Padrão Fundamental I)"
    elif "GRANDE" in porte:
        return 1750, "Atendimento de Bairro (Ensino Médio)"
    else:
        return 3000, "Escola de Referência (Transporte Público/Escolar)"

def render_radius_map():
    # 1. Configuração da Página: Define a barra lateral como expandida por padrão
    st.set_page_config(
        layout="wide", 
        page_title="Mapa de Raios - EducaMap",
        initial_sidebar_state="expanded"
    )
    
    # 2. CSS para desabilitar o botão hambúrguer e fixar layout
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

    # 3. Carregamento de Dados
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

        st.sidebar.title("Mapa de Raios")
        st.sidebar.caption("Raio de Abrangência Escolar")

        # Filtro de Regiões
        municipio_col = resolve_municipio_column(df)
        selected_municipios = []
        if municipio_col:
            municipios = sorted(df[municipio_col].dropna().unique())
            selected_municipios = st.multiselect("Regiões", municipios, default=municipios, placeholder="Selecione")

        # Filtro de Porte
        portes_disponiveis = sorted(df['Porte da Escola'].dropna().unique())
        selected_portes = st.multiselect("Porte da Escola", portes_disponiveis, default=portes_disponiveis, placeholder="Selecione")
        
        # Lógica de contagem para exibição imediata após o filtro
        mask_count = df['Porte da Escola'].isin(selected_portes)
        if selected_municipios and municipio_col:
            mask_count &= df[municipio_col].isin(selected_municipios)
        
        num_escolas = len(df[mask_count]) if not df.empty else 0
        
        # Exibição do número de escolas selecionadas
        st.metric("Escolas Selecionadas", num_escolas)
        
        st.markdown("---")
        st.caption("📍 O ícone representa o centro da unidade e o círculo a área de caminhada.")

    # --- LÓGICA DE FILTRAGEM PARA O MAPA ---
    filtered_df = df[mask_count].copy()

    if filtered_df.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        st.stop()

    # --- MAPA (OCUPANDO 100% DA ÁREA DO NAVEGADOR) ---
    m = folium.Map(
        location=[filtered_df["Latitude"].mean(), filtered_df["Longitude"].mean()],
        zoom_start=12,
        tiles="OpenStreetMap"
    )

    for _, row in filtered_df.iterrows():
        radius_m, justificativa = get_urban_radius_logic(row['Porte da Escola'])
        
        # Definição de cores por porte
        if "PEQUENO" in str(row['Porte da Escola']).upper():
            hex_color, icon_color = "#5fd819", "green"
        elif "GRANDE" in str(row['Porte da Escola']).upper():
            hex_color, icon_color = "#ff8e1d", "orange"
        elif "ESPECIAL" in str(row['Porte da Escola']).upper():
            hex_color, icon_color = "#d7191c", "red"
        else:
            hex_color, icon_color = "#1F5D8D", "blue"

        # Desenho do Raio
        folium.Circle(
            location=[row["Latitude"], row["Longitude"]],
            radius=radius_m,
            color=hex_color,
            fill=True,
            fill_opacity=0.15,
            weight=1,
            popup=f"<b>{row['Escola']}</b><br>Raio: {radius_m}m"
        ).add_to(m)

        # Marcador com Ícone de Escola
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            icon=folium.Icon(color=icon_color, icon="graduation-cap", prefix="fa"),
            tooltip=row['Escola']
        ).add_to(m)

    # Renderização total do componente Folium com altura máxima
    st_folium(m, width="100%", height=920, returned_objects=[])

if __name__ == "__main__":
    render_radius_map()
