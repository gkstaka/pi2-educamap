import folium
import pandas as pd
import streamlit as st
from folium.plugins import HeatMap
from streamlit_folium import st_folium


def render_heatmap_pins_tab(
    heatmap_df: pd.DataFrame,
    school_name_col: str | None,
    center_lat: float,
    center_lon: float,
    blur: int,
    min_opacity: float,
) -> None:
    st.subheader("Heatmap com pinos de capacidade")

    if heatmap_df.empty:
        st.info("Sem dados de capacidade para exibir heatmap com pinos.")
        return

    heat_local = heatmap_df.copy()
    heat_local["capacity_heat"] = heat_local["capacity_weight"] * 3
    heat_data = heat_local[["Latitude", "Longitude", "capacity_heat"]].values.tolist()

    heat_pin_map = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles="OpenStreetMap", control_scale=True)
    HeatMap(
        heat_data,
        radius=15,
        blur=blur,
        min_opacity=min_opacity,
        max_zoom=14,
    ).add_to(heat_pin_map)

    for _, row in heat_local.iterrows():
        school_name = row[school_name_col] if school_name_col else "Escola"
        capacity_text = row["Porte da Escola"] if "Porte da Escola" in heat_local.columns else "Nao informado"
        capacity_num = int(row["capacity_weight"]) if pd.notna(row["capacity_weight"]) else 0
        popup_html = (
            f"<b>{school_name}</b><br>"
            f"Capacidade (faixa): {capacity_text}<br>"
            f"Capacidade usada: {capacity_num}"
        )

        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=4,
            color="#1f77b4",
            fill=True,
            fill_color="#1f77b4",
            fill_opacity=0.85,
            tooltip=f"{school_name} | capacidade: {capacity_num}",
            popup=popup_html,
        ).add_to(heat_pin_map)

    st_folium(
        heat_pin_map,
        key="heatmap_pins_tab_map",
        height=650,
        use_container_width=True,
        returned_objects=[],
    )
