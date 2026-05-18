import streamlit as st
import pandas as pd
from app.modules.data_utils import load_data_from_postgres, resolve_municipio_column

def render_charts_page():
    st.set_page_config(layout="wide", page_title="Análise de Dados - EducaMap")

    st.markdown("""
        <style>
        .section-header { color: #1F5D8D; font-weight: bold; margin-top: 20px; }
        .kpi-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center; }
        </style>
        <h2 class="section-header">Painel Analítico e Tabelas</h2>
    """, unsafe_allow_html=True)

    # 1. Carga de Dados
    try:
        df = load_data_from_postgres()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return

    # 2. Sidebar - Filtros Globais para a Página
    st.sidebar.header("Filtros de Análise")
    municipio_col = resolve_municipio_column(df)
    
    selected_municipios = []
    if municipio_col:
        municipios = sorted(df[municipio_col].dropna().unique())
        selected_municipios = st.sidebar.multiselect("Filtrar Regiões", municipios, default=municipios)

    filtered_df = df.copy()
    if selected_municipios and municipio_col:
        filtered_df = filtered_df[filtered_df[municipio_col].isin(selected_municipios)]

    # 3. Resumo Executivo (KPIs)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Unidades", len(filtered_df))
    with col2:
        capacidade_total = filtered_df['capacity_weight'].sum()
        st.metric("Capacidade Estimada (Alunos)", f"{capacidade_total:,.0f}".replace(",", "."))
    with col3:
        percent_rural = (len(filtered_df[filtered_df['Localização'] == 'RURAL']) / len(filtered_df)) * 100 if len(filtered_df) > 0 else 0
        st.metric("Escolas Rurais", f"{percent_rural:.1f}%")

    st.divider()

    # 4. Visualizações Gráficas
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Distribuição por Localização")
        loc_count = filtered_df['Localização'].value_counts()
        st.bar_chart(loc_count, color="#1F5D8D")

    with chart_col2:
        st.subheader("Rede de Ensino")
        # Dependência Administrativa = tipo_rede no banco
        rede_count = filtered_df['Dependência Administrativa'].value_counts()
        st.bar_chart(rede_count, color="#5fd819")

    # 5. Exploração Tabular
    st.markdown("<h3 class='section-header'>Exploração de Dados</h3>", unsafe_allow_html=True)
    
    # Adicionando uma busca textual simples
    search = st.text_input("🔍 Buscar escola pelo nome", "")
    if search:
        filtered_df = filtered_df[filtered_df['Escola'].str.contains(search, case=False, na=False)]

    # Formatação da tabela para exibição
    st.dataframe(
        filtered_df[['Escola', 'Localização', 'Dependência Administrativa', 'Porte da Escola', 'capacity_weight']],
        use_container_width=True,
        hide_index=True
    )

    # Botão de Exportação
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar dados filtrados (CSV)",
        data=csv,
        file_name='educamap_filtrado.csv',
        mime='text/csv',
    )

if __name__ == "__main__":
    render_charts_page()
