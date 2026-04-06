from pathlib import Path
import re

import folium
import pandas as pd
import streamlit as st
from folium.plugins import HeatMap
from streamlit_folium import st_folium


def extract_capacity_weight(value: object) -> float | None:
	"""Extract the numeric upper-bound capacity from text like 'Entre 201 e 500 matriculas'."""
	if pd.isna(value):
		return None

	text = str(value).strip()
	if not text:
		return None

	numbers = [int(n) for n in re.findall(r"\d+", text)]
	if not numbers:
		return None

	# Use the largest number found to represent maximum capacity.
	return float(max(numbers))


st.set_page_config(page_title="Heatmap de Escolas do DF", layout="wide")

st.title("Heatmap de Escolas do DF")
st.caption("Mapa de densidade das escolas usando latitude e longitude do arquivo CSV.")

csv_path = Path(__file__).resolve().parent / "Analise-Tabela_da_lista_das_escolas-Detalhado.csv"

if not csv_path.exists():
	st.error(f"Arquivo nao encontrado: {csv_path}")
	st.stop()

df = pd.read_csv(csv_path)

required_columns = ["Latitude", "Longitude"]
missing_columns = [col for col in required_columns if col not in df.columns]

if missing_columns:
	st.error(f"Colunas obrigatorias ausentes: {', '.join(missing_columns)}")
	st.stop()

# Remove espacos e converte coordenadas para numero.
df["Latitude"] = pd.to_numeric(df["Latitude"].astype(str).str.strip(), errors="coerce")
df["Longitude"] = pd.to_numeric(df["Longitude"].astype(str).str.strip(), errors="coerce")

map_df = df.dropna(subset=["Latitude", "Longitude"]).copy()

if map_df.empty:
	st.warning("Nao ha coordenadas validas para gerar o heatmap.")
	st.stop()

capacity_col = "Porte da Escola" if "Porte da Escola" in map_df.columns else None
if capacity_col:
	map_df["capacity_weight"] = map_df[capacity_col].apply(extract_capacity_weight)
	map_df = map_df.dropna(subset=["capacity_weight"]).copy()

st.sidebar.header("Configuracoes do Heatmap")
radius = st.sidebar.slider("Raio dos pontos", min_value=5, max_value=30, value=12)
blur = st.sidebar.slider("Desfoque (blur)", min_value=5, max_value=40, value=18)
min_opacity = st.sidebar.slider("Opacidade minima", min_value=0.0, max_value=1.0, value=0.2, step=0.05)

municipio_col = "Município" if "Município" in map_df.columns else "Municipio" if "Municipio" in map_df.columns else None

if municipio_col:
	municipios = sorted(m for m in map_df[municipio_col].dropna().astype(str).unique() if m)
	selected_municipios = st.sidebar.multiselect("Filtrar por municipio", options=municipios, default=municipios)
	if selected_municipios:
		map_df = map_df[map_df[municipio_col].astype(str).isin(selected_municipios)]

if map_df.empty:
	st.warning("Nenhum registro disponivel apos aplicar os filtros ou capacidade de matriculas.")
	st.stop()

heat_data = map_df[["Latitude", "Longitude", "capacity_weight"]].values.tolist()
center_lat = map_df["Latitude"].mean()
center_lon = map_df["Longitude"].mean()

folium_map = folium.Map(location=[center_lat, center_lon], zoom_start=11, control_scale=True)

HeatMap(
	heat_data,
	radius=radius,
	blur=blur,
	min_opacity=min_opacity,
	max_zoom=14,
).add_to(folium_map)

st.subheader("Mapa")
st_folium(folium_map, width=None, height=700)

st.subheader("Resumo dos dados")
col1, col2, col3 = st.columns(3)
col1.metric("Registros no CSV", len(df))
col2.metric("Registros usados no heatmap", len(map_df))
col3.metric("Soma dos pesos", f"{map_df['capacity_weight'].sum():,.0f}")

with st.expander("Visualizar amostra dos dados utilizados"):
	st.dataframe(map_df.head(50), use_container_width=True)
