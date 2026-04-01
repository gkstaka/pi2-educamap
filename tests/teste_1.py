import  streamlit as st
from streamlit_folium import st_folium
import folium

st.title("Adding a Marker")

m = folium.Map(location=[48.8566, 2.3522], zoom_start=12)

folium.Marker(
    [48.8566, 2.3522],
    popup="Hello from Paris!",
    tooltip="Click me",
    icon=folium.Icon(color="red", icon="heart", prefix="fa")
).add_to(m)

st_folium(m, width=700)


