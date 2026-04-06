import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium


def render_pins_plain_tab(
    filtered_df: pd.DataFrame,
    school_name_col: str | None,
    center_lat: float,
    center_lon: float,
) -> None:
    st.subheader("Mapa de pinos sem agrupamento")

    plain_pin_map = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles="OpenStreetMap", control_scale=True)

    for _, row in filtered_df.iterrows():
        school_name = row[school_name_col] if school_name_col else "Escola"
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=f"<b>{school_name}</b>",
            tooltip=str(school_name),
            icon=folium.Icon(color="blue", icon="graduation-cap", prefix="fa"),
        ).add_to(plain_pin_map)

    st_folium(
        plain_pin_map,
        key="pins_plain_tab_map",
        height=650,
        use_container_width=True,
        returned_objects=[],
    )
