import streamlit as st
import folium
import pandas as pd
from streamlit_folium import st_folium
from app.modules.data_utils import load_data_from_postgres

def get_urban_radius_logic(porte):
    """Retorna o raio e a justificativa baseada no porte da escola."""
    porte = str(porte).upper()
    if "ATÉ 50" in porte or "SEM MATRÍCULA" in porte:
        return 400, "Caminhada Local"
    elif "51 E 200" in porte:
        return 900, "Padrão Fundamental I"
    elif "201 E 500" in porte:
        return 1500, "Padrão Fundamental II"
    elif "501 E 1000" in porte:
        return 2200, "Atendimento Regional"
    else:
        return 3000, "Escola de Referência"

def render_radius_map():
    # 1. Configuração da Página
    st.set_page_config(
        layout="wide", 
        page_title="Mapa de Raios - EducaMap",
        initial_sidebar_state="expanded"
    )
    
    # 2. CSS para Layout Full Screen
    st.markdown("""
        <style>
        [data-testid="collapsedControl"] { display: none !important; }
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container { padding: 0rem; margin: 0rem; max-width: 100%; }
        [data-testid="stSidebar"] { min-width: 280px !important; max-width: 280px !important; }
        </style>
    """, unsafe_allow_html=True)

    # 3. Carregamento de Dados
    try:
        df = load_data_from_postgres()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return

    # --- BARRA LATERAL (FILTROS) ---
    with st.sidebar:
        st.markdown("<h2 style='color: #1F5D8D; margin-bottom: 0;'>EducaMap</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color: #666; font-size: 0.8rem;'>Análise de Abrangência Escolar</p>", unsafe_allow_html=True)
        st.markdown("---")

        st.sidebar.title("Filtros de Análise")

        modalidades_map = {
            "Educação Infantil": "infantil",
            "Ensino Fundamental": "fundamental",
            "Ensino Médio": "médio",
            "Educação de Jovens Adultos": "jovens e adultos",
            "Educação Profissional": "profissional"
        }
        
        selected_modalidades = st.multiselect(
            "Modalidade de Ensino",
            options=list(modalidades_map.keys()),
            default=["Educação Infantil"]
        )

        opcoes_porte = [
            "Escola sem matrícula de escolarização",
            "Até 50 matrículas de escolarização",
            "Entre 51 e 200 matrículas de escolarização",
            "Entre 201 e 500 matrículas de escolarização",
            "Entre 501 e 1000 matrículas de escolarização",
            "Mais de 1000 matrículas de escolarização"
        ]
        
        selected_portes = st.multiselect(
            "Porte da Escola",
            options=opcoes_porte,
            default=["Entre 201 e 500 matrículas de escolarização"]
        )

        # --- LÓGICA DE FILTRAGEM ---
        col_mod = 'Etapas e Modalidade de Ensino Oferecidas'
        if selected_modalidades:
            keywords = [modalidades_map[name] for name in selected_modalidades]
            pattern = '|'.join(keywords)
            mask_modalidade = df[col_mod].fillna('').str.contains(pattern, case=False, na=False)
        else:
            mask_modalidade = pd.Series(False, index=df.index)

        mask_final = mask_modalidade & df['Porte da Escola'].isin(selected_portes)
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
        location=[center_lat, center_lon],
        zoom_start=zoom,
        tiles="OpenStreetMap"
    )

    # --- ADIÇÃO DE ELEMENTOS (APENAS SE HOUVER DADOS) ---
    if not df[mask_final].empty:
        for _, row in df[mask_final].iterrows():
            radius_m, justificativa = get_urban_radius_logic(row['Porte da Escola'])
            
            # Cores dinâmicas
            porte_txt = str(row['Porte da Escola']).lower()
            color = "#1F5D8D" # Padrão Azul
            if "até 50" in porte_txt: color = "#5fd819"
            elif "mais de 1000" in porte_txt: color = "#ff8e1d"

            folium.Circle(
                location=[row["Latitude"], row["Longitude"]],
                radius=radius_m,
                color=color,
                fill=True,
                fill_opacity=0.2,
                weight=1,
                popup=f"<b>{row['Escola']}</b><br>Raio: {radius_m}m"
            ).add_to(m)

            folium.Marker(
                location=[row["Latitude"], row["Longitude"]],
                icon=folium.Icon(color="blue", icon="graduation-cap", prefix="fa"),
                tooltip=row['Escola']
            ).add_to(m)

    # O Mapa é renderizado SEMPRE, independentemente do filtro
    st_folium(m, width="100%", height=900, returned_objects=[])

if __name__ == "__main__":
    render_radius_map()
