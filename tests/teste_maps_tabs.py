from pathlib import Path
import re

import folium
import pandas as pd
import streamlit as st
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium


st.set_page_config(layout="wide", page_title="EducaMap - Heatmap e Pinos")


def extract_capacity_weight(value: object) -> float | None:
    """Extract the maximum numeric value from enrollment-capacity text."""
    if pd.isna(value):
        return None

    text = str(value).strip()
    if not text:
        return None

    numbers = [int(n) for n in re.findall(r"\d+", text)]
    if not numbers:
        return None

    return float(max(numbers))


@st.cache_data
def load_school_data(csv_file: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_file)

    for col in ["Latitude", "Longitude"]:
        if col not in df.columns:
            raise ValueError(f"Coluna obrigatoria ausente: {col}")

    # Clean coordinate text and convert to numeric.
    df["Latitude"] = pd.to_numeric(df["Latitude"].astype(str).str.replace(",", ".", regex=False).str.strip(), errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"].astype(str).str.replace(",", ".", regex=False).str.strip(), errors="coerce")

    df = df.dropna(subset=["Latitude", "Longitude"]).copy()

    if "Porte da Escola" in df.columns:
        df["capacity_weight"] = df["Porte da Escola"].apply(extract_capacity_weight)
    else:
        df["capacity_weight"] = pd.NA

    return df


st.title("EducaMap")
st.caption("Visualizacao em abas: heatmap ponderado por capacidade, pinos agrupados, pinos sem agrupamento e heatmap com pinos de capacidade.")

csv_path = Path(__file__).resolve().parent / "Analise-Tabela_da_lista_das_escolas-Detalhado.csv"
if not csv_path.exists():
    st.error(f"Arquivo nao encontrado: {csv_path}")
    st.stop()

try:
    df = load_school_data(csv_path)
except Exception as exc:
    st.error(f"Erro ao carregar dados: {exc}")
    st.stop()

if df.empty:
    st.warning("Nao ha coordenadas validas para exibir no mapa.")
    st.stop()

municipio_col = "Municipio"
if "Municipio" not in df.columns and "Município" in df.columns:
    municipio_col = "Município"
elif "Municipio" not in df.columns and "Município" not in df.columns:
    municipio_col = None

st.sidebar.header("Filtros")
if municipio_col:
    municipios = sorted(m for m in df[municipio_col].dropna().astype(str).unique() if m)
    selected_municipios = st.sidebar.multiselect("Filtrar por municipio", municipios, default=municipios)
else:
    selected_municipios = []

if municipio_col and selected_municipios:
    filtered_df = df[df[municipio_col].astype(str).isin(selected_municipios)].copy()
else:
    filtered_df = df.copy()

if filtered_df.empty:
    st.warning("Nenhum registro encontrado para os filtros selecionados.")
    st.stop()

center_lat = filtered_df["Latitude"].mean()
center_lon = filtered_df["Longitude"].mean()

# Controls used only by heatmap tab.
st.sidebar.header("Heatmap")
blur = st.sidebar.slider("Blur", min_value=5, max_value=40, value=18)
min_opacity = st.sidebar.slider("Opacidade minima", min_value=0.0, max_value=1.0, value=0.2, step=0.05)

heatmap_df = filtered_df.dropna(subset=["capacity_weight"]).copy()

if "Escola" in filtered_df.columns:
    school_name_col = "Escola"
else:
    school_name_col = None

heatmap_tab, pins_tab, pins_plain_tab, heatmap_pins_tab = st.tabs([
    "Heatmap",
    "Pinos",
    "Pinos sem agrupamento",
    "Heatmap + Pinos (Capacidade)",
])

with heatmap_tab:
    st.subheader("Heatmap ponderado por capacidade")

    if heatmap_df.empty:
        st.info("Sem dados de capacidade para o heatmap apos aplicar os filtros.")
    else:
        # Formula solicitada: raio/intensidade proporcional a capacidade * 3.
        heatmap_df["capacity_heat"] = heatmap_df["capacity_weight"] * 3
        heat_data = heatmap_df[["Latitude", "Longitude", "capacity_heat"]].values.tolist()

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

with pins_tab:
    st.subheader("Mapa de pinos")

    pin_map = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles="OpenStreetMap", control_scale=True)
    cluster = MarkerCluster(name="Escolas").add_to(pin_map)

    for _, row in filtered_df.iterrows():
        school_name = row[school_name_col] if school_name_col else "Escola"
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=f"<b>{school_name}</b>",
            tooltip=str(school_name),
            icon=folium.Icon(color="blue", icon="graduation-cap", prefix="fa"),
        ).add_to(cluster)

    st_folium(
        pin_map,
        key="pins_tab_map",
        height=650,
        use_container_width=True,
        returned_objects=[],
    )

with pins_plain_tab:
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

with heatmap_pins_tab:
    st.subheader("Heatmap com pinos de capacidade")

    if heatmap_df.empty:
        st.info("Sem dados de capacidade para exibir heatmap com pinos.")
    else:
        heatmap_df["capacity_heat"] = heatmap_df["capacity_weight"] * 3
        heat_data = heatmap_df[["Latitude", "Longitude", "capacity_heat"]].values.tolist()

        heat_pin_map = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles="OpenStreetMap", control_scale=True)
        HeatMap(
            heat_data,
            radius=15,
            blur=blur,
            min_opacity=min_opacity,
            max_zoom=14,
        ).add_to(heat_pin_map)

        for _, row in heatmap_df.iterrows():
            school_name = row[school_name_col] if school_name_col else "Escola"
            capacity_text = row["Porte da Escola"] if "Porte da Escola" in heatmap_df.columns else "Nao informado"
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

st.subheader("Resumo")
col1, col2, col3 = st.columns(3)
col1.metric("Total com coordenadas", len(df))
col2.metric("Total apos filtros", len(filtered_df))
col3.metric("Total com peso (heatmap)", len(heatmap_df))
