import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd
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

# city_name = st.text_input("Digite o nome da cidade:", placeholder="ex. Paris, Toquio, Londres")

df = pd.read_csv('Analise-Tabela_da_lista_das_escolas-Detalhado.csv')

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
