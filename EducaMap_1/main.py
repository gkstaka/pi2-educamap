import streamlit as st
from app.modules import (
    load_data_from_postgres,
    render_heatmap_pins_tab,
    render_heatmap_tab,
    render_pins_cluster_tab,
    render_pins_plain_tab,
    resolve_municipio_column,
)

def main() -> None:
    st.set_page_config(layout="wide", page_title="EducaMap")
    st.title("EducaMap")
    st.caption("Aplicação integrada com base de dados PostgreSQL.")

    # troca a lógica de CSV pela leitura do Banco de Dados
    try:
        df = load_data_from_postgres()
    except Exception as exc:
        st.error(f"Erro ao carregar dados do banco: {exc}")
        st.stop()

    if df.empty:
        st.warning("Não há dados disponíveis no banco para exibir no mapa.")
        st.stop()

    municipio_col = resolve_municipio_column(df)

    st.sidebar.header("Filtros")
    if municipio_col:
        municipios = sorted(m for m in df[municipio_col].dropna().astype(str).unique() if m)
        selected_municipios = st.sidebar.multiselect("Filtrar por município", municipios, default=municipios)
    else:
        selected_municipios = []

    # Aplicação de filtros
    filtered_df = df.copy()
    if selected_municipios and municipio_col:
        filtered_df = filtered_df[filtered_df[municipio_col].isin(selected_municipios)]

    if filtered_df.empty:
        st.warning("Nenhum registro encontrado para os filtros selecionados.")
        st.stop()

    # Cálculos para o Mapa
    center_lat = filtered_df["Latitude"].mean()
    center_lon = filtered_df["Longitude"].mean()
    heatmap_df = filtered_df.dropna(subset=["capacity_weight"]).copy()

    st.sidebar.header("Configurações do Mapa")
    blur = st.sidebar.slider("Blur", min_value=5, max_value=40, value=18)
    min_opacity = st.sidebar.slider("Opacidade mínima", min_value=0.0, max_value=1.0, value=0.2, step=0.05)

    school_name_col = "Escola" if "Escola" in filtered_df.columns else None

    # Interface em Abas
    heatmap_tab, pins_tab, pins_plain_tab, heatmap_pins_tab = st.tabs([
        "Heatmap",
        "Pinos (Agrupados)",
        "Pinos (Simples)",
        "Heatmap + Capacidade",
    ])

    with heatmap_tab:
        render_heatmap_tab(heatmap_df, center_lat, center_lon, blur, min_opacity)

    with pins_tab:
        render_pins_cluster_tab(filtered_df, school_name_col, center_lat, center_lon)

    with pins_plain_tab:
        render_pins_plain_tab(filtered_df, school_name_col, center_lat, center_lon)

    with heatmap_pins_tab:
        render_heatmap_pins_tab(heatmap_df, school_name_col, center_lat, center_lon, blur, min_opacity)

if __name__ == "__main__":
    main()
