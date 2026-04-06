import folium
import pandas as pd
import streamlit as st
from folium.plugins import HeatMap
from streamlit_folium import st_folium


def render_heatmap_tab(
    heatmap_df: pd.DataFrame,
    center_lat: float,
    center_lon: float,
    blur: int,
    min_opacity: float,
) -> None:
    st.subheader("Heatmap ponderado por capacidade")

    if heatmap_df.empty:
        st.info("Sem dados de capacidade para o heatmap apos aplicar os filtros.")
        return

    heat_local = heatmap_df.copy()
    heat_local["capacity_heat"] = heat_local["capacity_weight"] * 3
    heat_data = heat_local[["Latitude", "Longitude", "capacity_heat"]].values.tolist()

    heat_map = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles="OpenStreetMap", control_scale=True)
    HeatMap(
        heat_data,
        radius=15,
        blur=blur,
        min_opacity=min_opacity,
        max_zoom=14,
    ).add_to(heat_map)

    st_folium(
        heat_map,
        key="heatmap_tab_map",
        height=650,
        use_container_width=True,
        returned_objects=[],
    )
