
from pathlib import Path

import streamlit as st

from tabs_lib import (
    load_school_data,
    render_heatmap_pins_tab,
    render_heatmap_tab,
    render_pins_cluster_tab,
    render_pins_plain_tab,
    resolve_csv_path,
    resolve_municipio_column,
)


def main() -> None:
    st.set_page_config(layout="wide", page_title="EducaMap")
    st.title("EducaMap")
    st.caption("Aplicacao modular com abas em arquivos separados.")

    project_root = Path(__file__).resolve().parent
    csv_path = resolve_csv_path(project_root)

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

    municipio_col = resolve_municipio_column(df)

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
    heatmap_df = filtered_df.dropna(subset=["capacity_weight"]).copy()

    st.sidebar.header("Heatmap")
    blur = st.sidebar.slider("Blur", min_value=5, max_value=40, value=18)
    min_opacity = st.sidebar.slider("Opacidade minima", min_value=0.0, max_value=1.0, value=0.2, step=0.05)

    school_name_col = "Escola" if "Escola" in filtered_df.columns else None

    heatmap_tab, pins_tab, pins_plain_tab, heatmap_pins_tab = st.tabs([
        "Heatmap",
        "Pinos",
        "Pinos sem agrupamento",
        "Heatmap + Pinos (Capacidade)",
    ])

    with heatmap_tab:
        render_heatmap_tab(heatmap_df, center_lat, center_lon, blur, min_opacity)

    with pins_tab:
        render_pins_cluster_tab(filtered_df, school_name_col, center_lat, center_lon)

    with pins_plain_tab:
        render_pins_plain_tab(filtered_df, school_name_col, center_lat, center_lon)

    with heatmap_pins_tab:
        render_heatmap_pins_tab(heatmap_df, school_name_col, center_lat, center_lon, blur, min_opacity)

    st.subheader("Resumo")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total com coordenadas", len(df))
    col2.metric("Total apos filtros", len(filtered_df))
    col3.metric("Total com peso (heatmap)", len(heatmap_df))


if __name__ == "__main__":
    main()
