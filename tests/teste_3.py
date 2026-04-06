import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd

# 1. Configurações Iniciais
st.set_page_config(layout="wide", page_title="EducaMap")

@st.cache_data
def load_data():
    df = pd.read_csv('Analise-Tabela_da_lista_das_escolas-Detalhado.csv')
    # Conversão de coordenadas para float
    for col in ['Latitude', 'Longitude']:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    return df.dropna(subset=['Latitude', 'Longitude'])

df_escola = load_data()

st.title("📍 EducaMap")

# 2. Estado da Sessão para evitar resets e loops
if 'map_center' not in st.session_state:
    st.session_state.map_center = [-15.793889, -47.8828]
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 11

# 3. Criar o mapa BASE (sempre o mesmo objeto)
m = folium.Map(
    location=st.session_state.map_center,
    zoom_start=st.session_state.map_zoom,
    tiles="OpenStreetMap"
)

# 4. Adicionar marcadores de forma estática (Evita o lag de recálculo constante)
# DICA: Se tiver muitas escolas, use .head(100) para testar a fluidez primeiro
for i, row in df_escola.iterrows():
    folium.Marker(
        location=[row['Latitude'], row['Longitude']],
        popup=f"<b>{row['Escola']}</b>",
        tooltip=row['Escola'],
        icon=folium.Icon(color="blue", icon="graduation-cap", prefix="fa")
    ).add_to(m)

# 5. Renderizar o mapa
# IMPORTANTE: use_container_width=True e uma key fixa são essenciais
output = st_folium(
    m,
    key="mapa_educamap",
    width=1400,
    height=600,
    use_container_width=True,
    returned_objects=["bounds", "center", "zoom"] # Só pede o necessário para evitar lag
)

# 6. Atualizar o estado APENAS se houver mudança real (evita o travamento)
if output and output.get("center"):
    new_lat = output["center"]["lat"]
    new_lng = output["center"]["lng"]
    new_zoom = output["zoom"]
    
    # Só atualiza se a diferença for relevante (evita micro-loops)
    if abs(st.session_state.map_center[0] - new_lat) > 0.001:
        st.session_state.map_center = [new_lat, new_lng]
        st.session_state.map_zoom = new_zoom

# Rodapé com informações
st.write(f"Total de escolas carregadas: {len(df_escola)}")
