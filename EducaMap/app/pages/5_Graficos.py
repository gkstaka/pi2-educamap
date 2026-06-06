import streamlit as st
import pandas as pd
from app.modules.data_utils import load_data_from_postgres, load_matriculas_data, resolve_municipio_column


# ---------------------------------------------------------------------------
# Helpers de ordenação
# ---------------------------------------------------------------------------

PORTE_ORDER = [
    "Escola sem matrícula de escolarização",
    "Até 50 matrículas de escolarização",
    "Entre 51 e 200 matrículas de escolarização",
    "Entre 201 e 500 matrículas de escolarização",
    "Entre 501 e 1000 matrículas de escolarização",
    "Mais de 1000 matrículas de escolarização",
]

NIVEL_LABELS = {
    "MAT_CRECHE":   "Creche",
    "MAT_PRE":      "Pré-escola",
    "MAT_EF_INI":   "EF Anos Iniciais",
    "MAT_EF_FIN":   "EF Anos Finais",
    "MAT_EM_TOTAL": "Ensino Médio",
    "MAT_EJA_TOTAL":"EJA",
    "MAT_EP_TOTAL": "Ed. Profissional",
}


def render_charts_page():
    st.set_page_config(layout="wide", page_title="Análise de Dados - EducaMap")

    st.markdown("""
        <style>
        .section-header { color: #1F5D8D; font-weight: bold; margin-top: 20px; }
        .kpi-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center; }
        </style>
        <h2 class="section-header">Painel Analítico e Tabelas</h2>
    """, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # 1. Carga de dados
    # ------------------------------------------------------------------
    try:
        df = load_data_from_postgres()
    except Exception as e:
        st.error(f"Erro ao carregar dados do banco: {e}")
        return

    df_mat = load_matriculas_data()  # pode ser None se arquivo não encontrado

    # ------------------------------------------------------------------
    # 2. Sidebar – filtros (afetam apenas o catálogo de escolas)
    # ------------------------------------------------------------------
    st.sidebar.header("Filtros de Análise")
    municipio_col = resolve_municipio_column(df)

    selected_municipios = []
    if municipio_col:
        municipios = sorted(df[municipio_col].dropna().unique())
        selected_municipios = st.sidebar.multiselect("Filtrar Regiões", municipios, default=municipios)

    filtered_df = df.copy()
    if selected_municipios and municipio_col:
        filtered_df = filtered_df[filtered_df[municipio_col].isin(selected_municipios)]

    # ------------------------------------------------------------------
    # 3. KPIs — linha única com 4 métricas
    # ------------------------------------------------------------------
    st.markdown("<h3 class='section-header'>Visão Geral</h3>", unsafe_allow_html=True)
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        st.metric("Total de Unidades", len(filtered_df))

    with kpi2:
        capacidade_total = filtered_df["capacity_weight"].sum()
        st.metric("Capacidade Estimada (Alunos)", f"{capacidade_total:,.0f}".replace(",", "."))

    with kpi3:
        pct_rural = (
            len(filtered_df[filtered_df["Localização"] == "RURAL"]) / len(filtered_df) * 100
            if len(filtered_df) > 0 else 0
        )
        st.metric("Escolas Rurais", f"{pct_rural:.1f}%")

    with kpi4:
        n_privadas = len(filtered_df[filtered_df["Dependência Administrativa"] == "Privada"])
        pct_privada = n_privadas / len(filtered_df) * 100 if len(filtered_df) > 0 else 0
        st.metric("Escolas Privadas", f"{pct_privada:.1f}%", help="Percentual do total filtrado")

    st.divider()

    # ------------------------------------------------------------------
    # 4. Gráficos do catálogo de escolas
    # ------------------------------------------------------------------
    st.markdown("<h3 class='section-header'>Catálogo de Escolas — DF</h3>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Distribuição por Localização")
        loc_count = filtered_df["Localização"].value_counts()
        st.bar_chart(loc_count, color="#1F5D8D")

    with col2:
        st.subheader("Rede de Ensino (Dependência Administrativa)")
        rede_count = filtered_df["Dependência Administrativa"].value_counts()
        st.bar_chart(rede_count, color="#5fd819")

    # --- Porte de escola (ordenado por faixa crescente) ---
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Porte das Escolas")
        porte_count = filtered_df["Porte da Escola"].value_counts()
        # Reordena pelas faixas definidas (mantém apenas as que existem)
        ordered_index = [p for p in PORTE_ORDER if p in porte_count.index]
        extra = [p for p in porte_count.index if p not in PORTE_ORDER]
        porte_ordered = porte_count.reindex(ordered_index + extra)
        # Rótulos curtos para o eixo
        short_labels = {
            "Escola sem matrícula de escolarização": "Sem matrícula",
            "Até 50 matrículas de escolarização": "Até 50",
            "Entre 51 e 200 matrículas de escolarização": "51–200",
            "Entre 201 e 500 matrículas de escolarização": "201–500",
            "Entre 501 e 1000 matrículas de escolarização": "501–1000",
            "Mais de 1000 matrículas de escolarização": "+1000",
        }
        porte_ordered.index = [short_labels.get(i, i) for i in porte_ordered.index]
        st.bar_chart(porte_ordered, color="#E07B39")

    with col4:
        st.subheader("Modalidades de Ensino Oferecidas (top 10)")
        modalidade_count = (
            filtered_df["Etapas e Modalidade de Ensino Oferecidas"]
            .dropna()
            .replace("", pd.NA)
            .dropna()
            .value_counts()
            .head(10)
        )
        # Rótulos simplificados
        def shorten_modal(s):
            return (s.replace("Educação Infantil", "EI")
                     .replace("Ensino Fundamental", "EF")
                     .replace("Ensino Médio", "EM")
                     .replace("Educação de Jovens Adultos", "EJA")
                     .replace("Educação Profissional", "EP"))
        modalidade_count.index = [shorten_modal(i) for i in modalidade_count.index]
        st.bar_chart(modalidade_count, color="#9B59B6")

    st.divider()

    # ------------------------------------------------------------------
    # 5. Tabela cruzada: Dependência × Porte
    # ------------------------------------------------------------------
    st.markdown("<h3 class='section-header'>Cruzamento: Rede de Ensino × Porte</h3>", unsafe_allow_html=True)
    st.caption("Número de escolas por combinação de dependência administrativa e porte.")

    cross_df = filtered_df.copy()
    cross_df["Porte Resumido"] = cross_df["Porte da Escola"].map(
        lambda x: short_labels.get(str(x), str(x))
    )
    pivot = pd.crosstab(
        cross_df["Dependência Administrativa"],
        cross_df["Porte Resumido"]
    )
    # Reordena colunas na ordem crescente de faixa
    short_order = ["Sem matrícula", "Até 50", "51–200", "201–500", "501–1000", "+1000"]
    pivot = pivot.reindex(columns=[c for c in short_order if c in pivot.columns])
    pivot["TOTAL"] = pivot.sum(axis=1)
    st.dataframe(pivot, use_container_width=True)

    st.divider()

    # ------------------------------------------------------------------
    # 6. Análise de Matrículas — Rede Pública 2023
    # ------------------------------------------------------------------
    st.markdown("<h3 class='section-header'>Rede Pública — Matrículas 2023 (SEEDF + Federal)</h3>", unsafe_allow_html=True)

    if df_mat is None:
        st.info("Arquivo de matrículas não encontrado. Verifique o caminho do JSON em data/raw/Governanca_educa_df/.")
    else:
        st.caption(f"Base: {len(df_mat)} escolas da rede pública registradas no Censo Escolar 2023.")

        mat_col1, mat_col2 = st.columns(2)

        with mat_col1:
            st.subheader("Escolas por Região Administrativa")
            ra_count = df_mat["NO_RA"].value_counts().sort_values(ascending=False)
            st.bar_chart(ra_count, color="#1F5D8D")

        with mat_col2:
            st.subheader("Distribuição por Nível de Ensino")
            nivel_totals = {}
            for col, label in NIVEL_LABELS.items():
                if col in df_mat.columns:
                    total = df_mat[col].sum()
                    if total > 0:
                        nivel_totals[label] = int(total)

            if nivel_totals:
                nivel_series = pd.Series(nivel_totals).sort_values(ascending=False)
                st.bar_chart(nivel_series, color="#E07B39")
            else:
                st.info("Nenhum dado de nível de ensino encontrado.")

        mat_col3, mat_col4 = st.columns(2)

        with mat_col3:
            st.subheader("Distribuição por Raça / Cor")
            if "COR_RACA" in df_mat.columns:
                raca_count = df_mat["COR_RACA"].value_counts()
                st.bar_chart(raca_count, color="#2ECC71")

        with mat_col4:
            st.subheader("Distribuição por Localização")
            if "LOCALIZACAO" in df_mat.columns:
                loc_mat = df_mat["LOCALIZACAO"].value_counts()
                st.bar_chart(loc_mat, color="#9B59B6")
                # KPIs rápidos de contexto
                total = len(df_mat)
                n_rural = int(df_mat["LOCALIZACAO"].eq("Rural").sum())
                c1, c2 = st.columns(2)
                c1.metric("Escolas Urbanas", total - n_rural)
                c2.metric("Escolas Rurais", n_rural)

    st.divider()

    # ------------------------------------------------------------------
    # 7. Exploração tabular (mantida intacta)
    # ------------------------------------------------------------------
    st.markdown("<h3 class='section-header'>Exploração de Dados</h3>", unsafe_allow_html=True)

    search = st.text_input("🔍 Buscar escola pelo nome", "")
    display_df = filtered_df.copy()
    if search:
        display_df = display_df[display_df["Escola"].str.contains(search, case=False, na=False)]

    st.dataframe(
        display_df[["Escola", "Localização", "Dependência Administrativa", "Porte da Escola", "capacity_weight"]],
        use_container_width=True,
        hide_index=True,
    )

    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Baixar dados filtrados (CSV)",
        data=csv,
        file_name="educamap_filtrado.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    render_charts_page()
