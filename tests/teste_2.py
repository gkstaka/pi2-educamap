import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd
from pathlib import Path
# from geopy.geocoders import Nominatim

st.set_page_config(layout="wide")

st.markdown("""
    <style>
    .main > div {
        padding-left = 0rem;
        padding-right = 0rem;
        padding-top = 0rem;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("EducaMap")

# Construct an absolute path to the data relative to this script's location.
# __file__ is /tests/teste_2.py, so .parent.parent is the project root.
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / 'data' / 'Catalogo_Escola' / 'Análise - Tabela da lista das escolas - Detalhado.csv'

try:
    df = pd.read_csv(DATA_PATH)
except Exception as e:
    st.error(f"Erro ao carregar os dados: {e}")
    df = pd.DataFrame() # Fallback to empty dataframe

location = [-15.793889, -47.8828]
zoom = 10.5

# if city_name:
#     geolocator = Nominatim(user_agent="streamlit_map_app")
#     location_data = geolocator.geocode(city_name)
#
#     if location_data:
#         location = [location_data.latitude, location_data.longitude]
#         zoom=10
#         st.success(f"Encontrou: {location_data.address}")
#     else:
#         st.error("Cidade não encontrada! Mostrando Brasília!")
#
m = folium.Map(location=location, zoom_start=zoom)

folium.Marker(
    location,
    #popup=f"Olá de {city_name or 'Brasília'}!",
    popup="Olá Brasília!",
    tooltip="Clique aqui",
    icon=folium.Icon(color="red", icon="heart", prefix="fa")
).add_to(m)

st_folium(m, width="100%", height=900, use_container_width=True)

st.write(df)
