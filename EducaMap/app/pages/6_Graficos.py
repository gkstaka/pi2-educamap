import streamlit as st
import pandas as pd
import altair as alt
from app.modules.data_utils import (
    load_data_from_postgres,
    load_matriculas_data,
    resolve_municipio_column,
    load_ibge_frequencia_data,
    load_entorno_por_ra,
    load_espacos_culturais_por_ra,
    load_mobiliario_esporte_lazer,
    load_acessibilidade_por_ra,
    load_capacidade_por_ra,
    load_qualidade_entorno_por_ra,
    load_onibus_osm_por_ra,
    load_quadrante_acesso_onibus_entorno,
    QUADRANTES_ACESSO_ENTORNO,
)


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
    # 7. Novos Painéis Analíticos
    # ------------------------------------------------------------------
    st.markdown("<h3 class='section-header'>Painéis Analíticos Avançados</h3>", unsafe_allow_html=True)

    # ---- 7.1 Curva de Frequência Escolar por Faixa Etária (Censo 2022) ----
    st.subheader("Taxa Bruta de Frequência Escolar por Faixa Etária — Brasil (Censo 2022)")
    st.caption("A curva expõe os gargalos no fluxo escolar: o pico no Ensino Fundamental e a queda abrupta após os 15 anos contextualizam a importância da oferta de EM e EJA.")

    try:
        df_freq = load_ibge_frequencia_data()
        col_taxa = next(
            (c for c in df_freq.columns if "taxa" in c.lower() or "frequência" in c.lower() or "frequencia" in c.lower()),
            df_freq.columns[1],
        )
        col_faixa = df_freq.columns[0]
        df_freq[col_taxa] = pd.to_numeric(
            df_freq[col_taxa].astype(str).str.replace(",", "."), errors="coerce"
        )

        order_faixas = ["0 a 3 anos", "4 e 5 anos", "6 a 14 anos", "15 a 17 anos", "18 a 24 anos", "25 anos ou mais"]
        df_freq_clean = df_freq[[col_faixa, col_taxa]].dropna()
        df_freq_clean.columns = ["Faixa Etária", "Frequência (%)"]

        bar_chart = (
            alt.Chart(df_freq_clean)
            .mark_bar(color="#1F5D8D")
            .encode(
                x=alt.X(
                    "Faixa Etária:N",
                    sort=order_faixas,
                    title="Faixa Etária",
                ),
                y=alt.Y("Frequência (%):Q", scale=alt.Scale(domain=[0, 105]), title="Taxa (%)"),
                tooltip=[
                    alt.Tooltip("Faixa Etária:N"),
                    alt.Tooltip("Frequência (%):Q", format=".1f"),
                ],
            )
            .properties(height=280)
        )
        st.altair_chart(bar_chart, use_container_width=True)
    except Exception as e:
        st.warning(f"Não foi possível gerar este gráfico: {e}")

    st.divider()

    # ---- 7.2 Funil de Evasão por Ano Escolar (EF e EM) ----
    st.subheader("Funil de Matrículas por Ano/Série Escolar — Rede Pública 2023")
    st.caption("Volume de matrículas em cada ano do Ensino Fundamental e série do Ensino Médio. A forma da curva evidencia onde ocorrem as quedas de fluxo entre etapas.")

    if df_mat is not None:
        try:
            etapa_cols = {
                "MAT_EF_1ANO": "EF 1º ano", "MAT_EF_2ANO": "EF 2º ano",
                "MAT_EF_3ANO": "EF 3º ano", "MAT_EF_4ANO": "EF 4º ano",
                "MAT_EF_5ANO": "EF 5º ano", "MAT_EF_6ANO": "EF 6º ano",
                "MAT_EF_7ANO": "EF 7º ano", "MAT_EF_8ANO": "EF 8º ano",
                "MAT_EF_9ANO": "EF 9º ano",
                "MAT_EM_1SER": "EM 1ª série", "MAT_EM_2SER": "EM 2ª série",
                "MAT_EM_3SER": "EM 3ª série",
            }
            cols_disp = [c for c in etapa_cols if c in df_mat.columns]
            totals = df_mat[cols_disp].apply(pd.to_numeric, errors="coerce").sum()
            df_funil = pd.DataFrame({
                "Etapa": [etapa_cols[c] for c in cols_disp],
                "Matrículas": totals.values,
            })
            ordem_etapas = list(etapa_cols.values())

            funil_chart = (
                alt.Chart(df_funil)
                .mark_bar(color="#1F5D8D")
                .encode(
                    x=alt.X("Etapa:N", sort=ordem_etapas, title="Ano/Série"),
                    y=alt.Y("Matrículas:Q", title="Matrículas"),
                    color=alt.Color(
                        "Etapa:N", sort=ordem_etapas,
                        scale=alt.Scale(scheme="blues"), legend=None,
                    ),
                    tooltip=[
                        alt.Tooltip("Etapa:N"),
                        alt.Tooltip("Matrículas:Q", format=","),
                    ],
                )
                .properties(height=300)
            )
            st.altair_chart(funil_chart, use_container_width=True)
        except Exception as e:
            st.warning(f"Não foi possível gerar este gráfico: {e}")
    else:
        st.info("Dados de matrículas não disponíveis.")

    st.divider()

    # ---- 7.4 Composição Pública × Privada por Nível de Ensino ----
    st.subheader("Composição Pública × Privada por Nível de Ensino")
    st.caption("Percentual de cada rede (Estadual, Federal, Municipal, Privada) dentro de cada nível. Revela em quais etapas o setor privado concentra mais oferta.")

    if df_mat is not None and "NO_REDE" in df_mat.columns:
        try:
            nivel_cols_disp = [c for c in NIVEL_LABELS if c in df_mat.columns]
            nivel_por_rede = df_mat.groupby("NO_REDE")[nivel_cols_disp].sum()
            nivel_por_rede.columns = [NIVEL_LABELS[c] for c in nivel_por_rede.columns]
            nivel_melted = (
                nivel_por_rede.reset_index()
                .melt(id_vars="NO_REDE", var_name="Nível", value_name="Matrículas")
            )
            nivel_melted = nivel_melted[nivel_melted["Matrículas"] > 0]

            stacked = (
                alt.Chart(nivel_melted)
                .mark_bar()
                .encode(
                    x=alt.X("Matrículas:Q", stack="normalize", title="Proporção", axis=alt.Axis(format="%")),
                    y=alt.Y("Nível:N", title="Nível de Ensino"),
                    color=alt.Color("NO_REDE:N", title="Rede"),
                    tooltip=[
                        alt.Tooltip("Nível:N"),
                        alt.Tooltip("NO_REDE:N", title="Rede"),
                        alt.Tooltip("Matrículas:Q", format=","),
                    ],
                )
                .properties(height=280)
            )
            st.altair_chart(stacked, use_container_width=True)
        except Exception as e:
            st.warning(f"Não foi possível gerar este gráfico: {e}")
    else:
        st.info("Dados de rede de ensino não disponíveis.")

    st.divider()

    # ---- 7.3 Índice de Infraestrutura de Entorno por Região Administrativa ----
    st.subheader("Índice de Infraestrutura de Entorno por Região Administrativa")

    with st.spinner("Calculando entorno via PostGIS…"):
        df_entorno = load_entorno_por_ra()

    if df_entorno is not None and not df_entorno.empty:
        try:
            label_map = {
                "saude": "Saúde", "seguranca": "Segurança",
                "parques": "Parques", "cultura": "Cultura",
            }
            COLOR_SCALE = alt.Scale(
                domain=["Saúde", "Segurança", "Parques", "Cultura"],
                range=["#B0E0E6", "#B22222", "#2E8B57", "#8A2BE2"],
            )

            visao = st.radio(
                "Modo de visualização",
                ["Absoluto", "Por escola", "Índice 0–100"],
                horizontal=True,
            )

            if visao == "Absoluto":
                st.caption("Contagem bruta de equipamentos públicos por RA.")
                value_cols = ["saude", "seguranca", "parques", "cultura"]
                sort_col = "total_equipamentos"
                x_title = "Número de equipamentos"

                melted = df_entorno.melt(
                    id_vars="ra_nome", value_vars=value_cols,
                    var_name="Tipo", value_name="Valor",
                )
                melted["Tipo"] = melted["Tipo"].map(label_map)
                order = df_entorno.sort_values(sort_col, ascending=False)["ra_nome"].tolist()

                chart = (
                    alt.Chart(melted)
                    .mark_bar()
                    .encode(
                        x=alt.X("Valor:Q", title=x_title),
                        y=alt.Y("ra_nome:N", sort=order, title="Região Administrativa", axis=alt.Axis(labelOverlap=False)),
                        color=alt.Color("Tipo:N", scale=COLOR_SCALE),
                        tooltip=["ra_nome:N", "Tipo:N", alt.Tooltip("Valor:Q", format=",")],
                    )
                    .properties(height=max(380, len(df_entorno) * 22))
                )
                st.altair_chart(chart, use_container_width=True)

            elif visao == "Por escola":
                st.caption(
                    "Equipamentos disponíveis **por escola** em cada RA — compara RAs de tamanhos diferentes de forma justa."
                )
                value_cols = ["saude_por_escola", "seguranca_por_escola", "parques_por_escola", "cultura_por_escola"]
                sort_col = "total_por_escola"

                melted = df_entorno.melt(
                    id_vars="ra_nome", value_vars=value_cols,
                    var_name="Tipo", value_name="Valor",
                )
                melted["Tipo"] = (
                    melted["Tipo"]
                    .str.replace("_por_escola", "")
                    .map(label_map)
                )
                order = df_entorno.sort_values(sort_col, ascending=False)["ra_nome"].tolist()

                chart = (
                    alt.Chart(melted)
                    .mark_bar()
                    .encode(
                        x=alt.X("Valor:Q", title="Equipamentos por escola"),
                        y=alt.Y("ra_nome:N", sort=order, title="Região Administrativa", axis=alt.Axis(labelOverlap=False)),
                        color=alt.Color("Tipo:N", scale=COLOR_SCALE),
                        tooltip=["ra_nome:N", "Tipo:N", alt.Tooltip("Valor:Q", format=".2f")],
                    )
                    .properties(height=max(380, len(df_entorno) * 22))
                )
                st.altair_chart(chart, use_container_width=True)

            else:  # Índice 0–100
                st.caption(
                    "Índice **0–100** calculado via min-max sobre o total de equipamentos por escola. "
                    "100 = RA com melhor infraestrutura relativa; 0 = pior."
                )
                order = df_entorno.sort_values("indice_normalizado", ascending=False)["ra_nome"].tolist()

                chart = (
                    alt.Chart(df_entorno)
                    .mark_bar()
                    .encode(
                        x=alt.X(
                            "indice_normalizado:Q",
                            scale=alt.Scale(domain=[0, 100]),
                            title="Índice (0–100)",
                        ),
                        y=alt.Y("ra_nome:N", sort=order, title="Região Administrativa", axis=alt.Axis(labelOverlap=False)),
                        color=alt.Color(
                            "indice_normalizado:Q",
                            scale=alt.Scale(scheme="redyellowgreen"),
                            legend=None,
                        ),
                        tooltip=[
                            "ra_nome:N",
                            alt.Tooltip("indice_normalizado:Q", title="Índice", format=".1f"),
                            alt.Tooltip("total_por_escola:Q", title="Equip./escola", format=".2f"),
                            alt.Tooltip("n_escolas:Q", title="Escolas na RA", format=","),
                        ],
                    )
                    .properties(height=max(380, len(df_entorno) * 22))
                )
                st.altair_chart(chart, use_container_width=True)

        except Exception as e:
            st.warning(f"Não foi possível gerar este gráfico: {e}")
    else:
        st.info("Dados geoespaciais não disponíveis ou PostGIS não acessível.")

    st.divider()

    # ---- 7.5 Diversidade de Equipamentos Culturais por RA ----
    st.subheader("Diversidade de Equipamentos Culturais por Região Administrativa")
    st.caption("Decompõe os espaços culturais por tipo (biblioteca, teatro, museu, clube, ginásio...). Revela não apenas a quantidade, mas o perfil da oferta cultural de cada RA.")

    with st.spinner("Carregando espaços culturais via PostGIS…"):
        df_cult = load_espacos_culturais_por_ra()

    if df_cult is not None and not df_cult.empty:
        try:
            order_ra = (
                df_cult.groupby("ra_nome")["total"].sum()
                .sort_values(ascending=False)
                .index.tolist()
            )
            heatmap = (
                alt.Chart(df_cult)
                .mark_rect()
                .encode(
                    x=alt.X("tipo:N", title="Tipo de equipamento"),
                    y=alt.Y("ra_nome:N", sort=order_ra, title="Região Administrativa"),
                    color=alt.Color("total:Q", scale=alt.Scale(scheme="purples"), title="Quantidade"),
                    tooltip=[
                        alt.Tooltip("ra_nome:N", title="RA"),
                        alt.Tooltip("tipo:N", title="Tipo"),
                        alt.Tooltip("total:Q", title="Quantidade"),
                    ],
                )
                .properties(height=max(320, len(order_ra) * 18))
            )
            st.altair_chart(heatmap, use_container_width=True)
        except Exception as e:
            st.warning(f"Não foi possível gerar este gráfico: {e}")
    else:
        st.info("Dados geoespaciais não disponíveis ou PostGIS não acessível.")

    st.divider()

    # ---- 7.6 Condição dos Equipamentos de Esporte e Lazer ----
    st.subheader("Condição dos Equipamentos de Esporte e Lazer")
    st.caption("Compara, por tipo de equipamento, quantos estão integrados a um espaço maior (INTEGRADO) versus isolados (ISOLADO) — uma proxy de qualidade da infraestrutura de lazer no entorno das escolas.")

    with st.spinner("Carregando mobiliário de esporte e lazer via PostGIS…"):
        df_esp = load_mobiliario_esporte_lazer()

    if df_esp is not None and not df_esp.empty:
        try:
            order_tipo = (
                df_esp.groupby("tipo")["total"].sum()
                .sort_values(ascending=False)
                .index.tolist()
            )
            esp_chart = (
                alt.Chart(df_esp)
                .mark_bar()
                .encode(
                    x=alt.X("total:Q", title="Quantidade"),
                    y=alt.Y("tipo:N", sort=order_tipo, title="Tipo de equipamento"),
                    color=alt.Color(
                        "condicao:N", title="Condição",
                        scale=alt.Scale(domain=["Integrado", "Isolado"], range=["#2E8B57", "#B22222"]),
                    ),
                    tooltip=[
                        alt.Tooltip("tipo:N", title="Tipo"),
                        alt.Tooltip("condicao:N", title="Condição"),
                        alt.Tooltip("total:Q", title="Quantidade"),
                    ],
                )
                .properties(height=max(320, len(order_tipo) * 28))
            )
            st.altair_chart(esp_chart, use_container_width=True)
        except Exception as e:
            st.warning(f"Não foi possível gerar este gráfico: {e}")
    else:
        st.info("Dados geoespaciais não disponíveis ou PostGIS não acessível.")

    st.divider()

    # ---- 7.7 Acessibilidade do Entorno Escolar por Região Administrativa ----
    st.subheader("Acessibilidade do Entorno Escolar por Região Administrativa")
    st.caption(
        "Distância média (em metros) da escola até o equipamento mais próximo de cada categoria — "
        "saúde, segurança, parques, cultura, esporte/lazer, espaços comunitários e feiras livres. "
        "Diferente da contagem bruta de equipamentos, essa métrica reflete a proximidade real "
        "vivenciada por quem estuda em cada RA."
    )

    with st.spinner("Calculando distâncias via PostGIS…"):
        df_acess = load_acessibilidade_por_ra()

    if df_acess is not None and not df_acess.empty:
        try:
            label_map_acess = {
                "saude_m": "Saúde", "seguranca_m": "Segurança",
                "parques_m": "Parques", "cultura_m": "Cultura", "esporte_m": "Esporte/Lazer",
                "comunitario_m": "Espaços Comunitários", "feira_m": "Feiras Livres",
            }
            COLOR_SCALE_ACESS = alt.Scale(
                domain=list(label_map_acess.values()),
                range=["#B0E0E6", "#B22222", "#2E8B57", "#8A2BE2", "#E07B39", "#5fd819", "#F4D03F"],
            )

            visao_acess = st.radio(
                "Modo de visualização",
                ["Distância por categoria", "Índice de Acessibilidade (0–100)"],
                horizontal=True,
                key="visao_acessibilidade",
            )

            if visao_acess == "Distância por categoria":
                st.caption("Quanto menor a barra, mais próximo está, em média, o equipamento daquela categoria.")
                melted = df_acess.melt(
                    id_vars="ra_nome", value_vars=list(label_map_acess.keys()),
                    var_name="Categoria", value_name="Distância (m)",
                )
                melted["Categoria"] = melted["Categoria"].map(label_map_acess)
                order = df_acess.sort_values("distancia_media_m")["ra_nome"].tolist()

                chart = (
                    alt.Chart(melted)
                    .mark_bar()
                    .encode(
                        x=alt.X("Distância (m):Q", title="Distância média até o equipamento mais próximo (m)"),
                        y=alt.Y("ra_nome:N", sort=order, title="Região Administrativa", axis=alt.Axis(labelOverlap=False)),
                        color=alt.Color("Categoria:N", scale=COLOR_SCALE_ACESS),
                        tooltip=["ra_nome:N", "Categoria:N", alt.Tooltip("Distância (m):Q", format=",.0f")],
                    )
                    .properties(height=max(380, len(df_acess) * 22))
                )
                st.altair_chart(chart, use_container_width=True)

            else:  # Índice de Acessibilidade (0-100)
                st.caption(
                    "Índice **0–100** calculado via min-max sobre a distância média geral. "
                    "100 = RA com entorno mais acessível (menores distâncias); 0 = menos acessível."
                )
                order = df_acess.sort_values("indice_acessibilidade", ascending=False)["ra_nome"].tolist()

                chart = (
                    alt.Chart(df_acess)
                    .mark_bar()
                    .encode(
                        x=alt.X(
                            "indice_acessibilidade:Q",
                            scale=alt.Scale(domain=[0, 100]),
                            title="Índice de Acessibilidade (0–100)",
                        ),
                        y=alt.Y("ra_nome:N", sort=order, title="Região Administrativa", axis=alt.Axis(labelOverlap=False)),
                        color=alt.Color(
                            "indice_acessibilidade:Q",
                            scale=alt.Scale(scheme="redyellowgreen"),
                            legend=None,
                        ),
                        tooltip=[
                            "ra_nome:N",
                            alt.Tooltip("indice_acessibilidade:Q", title="Índice", format=".1f"),
                            alt.Tooltip("distancia_media_m:Q", title="Distância média (m)", format=",.0f"),
                            alt.Tooltip("n_escolas:Q", title="Escolas na RA", format=","),
                        ],
                    )
                    .properties(height=max(380, len(df_acess) * 22))
                )
                st.altair_chart(chart, use_container_width=True)

        except Exception as e:
            st.warning(f"Não foi possível gerar este gráfico: {e}")
    else:
        st.info("Dados geoespaciais não disponíveis ou PostGIS não acessível.")

    st.divider()

    # ---- 7.8 Oferta de Capacidade Estimada por RA ----
    st.subheader("Oferta de Capacidade Estimada por Região Administrativa")
    st.caption(
        "Soma da capacidade máxima estimada de matrícula das escolas de cada RA, e a capacidade "
        "média por escola — um proxy do porte/escala da rede pública e privada na região. "
        "Não representa demanda real de matrículas (a base de matrículas 2023 disponível não permite "
        "agregação confiável por escola/RA)."
    )

    with st.spinner("Calculando capacidade estimada via PostGIS…"):
        df_cap = load_capacidade_por_ra()

    if df_cap is not None and not df_cap.empty:
        try:
            visao_cap = st.radio(
                "Modo de visualização",
                ["Capacidade total", "Capacidade média por escola"],
                horizontal=True,
                key="visao_capacidade",
            )

            if visao_cap == "Capacidade total":
                st.caption("Soma da capacidade estimada de matrícula de todas as escolas da RA.")
                col_x = "capacidade_total"
                x_title = "Capacidade total estimada (vagas)"
            else:
                st.caption("Capacidade estimada média por escola — indica o porte típico das escolas da RA.")
                col_x = "capacidade_por_escola"
                x_title = "Capacidade média por escola (vagas)"

            order = df_cap.sort_values(col_x, ascending=False)["ra_nome"].tolist()
            chart = (
                alt.Chart(df_cap)
                .mark_bar(color="#1F5D8D")
                .encode(
                    x=alt.X(f"{col_x}:Q", title=x_title),
                    y=alt.Y("ra_nome:N", sort=order, title="Região Administrativa", axis=alt.Axis(labelOverlap=False)),
                    tooltip=[
                        "ra_nome:N",
                        alt.Tooltip("capacidade_total:Q", title="Capacidade total", format=",.0f"),
                        alt.Tooltip("capacidade_por_escola:Q", title="Capacidade/escola", format=",.0f"),
                        alt.Tooltip("n_escolas:Q", title="Escolas na RA", format=","),
                    ],
                )
                .properties(height=max(380, len(df_cap) * 22))
            )
            st.altair_chart(chart, use_container_width=True)
        except Exception as e:
            st.warning(f"Não foi possível gerar este gráfico: {e}")
    else:
        st.info("Dados geoespaciais não disponíveis ou PostGIS não acessível.")

    st.divider()

    # ---- 7.9 Índice de Qualidade do Entorno Escolar (combinado) ----
    st.subheader("Índice de Qualidade do Entorno Escolar por Região Administrativa")
    st.caption(
        "Combina, em uma média simples, o Índice de Infraestrutura (quantidade de equipamentos por "
        "escola) e o Índice de Acessibilidade (proximidade real até o equipamento mais próximo). "
        "Uma RA com nota alta reúne tanto fartura quanto proximidade de equipamentos no entorno escolar; "
        "uma nota baixa indica carência em ambas as dimensões — ou compensação parcial entre elas."
    )

    with st.spinner("Combinando índices de infraestrutura e acessibilidade…"):
        df_qualidade = load_qualidade_entorno_por_ra()

    if df_qualidade is not None and not df_qualidade.empty:
        try:
            order = df_qualidade.sort_values("indice_qualidade_entorno", ascending=False)["ra_nome"].tolist()
            chart = (
                alt.Chart(df_qualidade)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "indice_qualidade_entorno:Q",
                        scale=alt.Scale(domain=[0, 100]),
                        title="Índice de Qualidade do Entorno (0–100)",
                    ),
                    y=alt.Y("ra_nome:N", sort=order, title="Região Administrativa", axis=alt.Axis(labelOverlap=False)),
                    color=alt.Color(
                        "indice_qualidade_entorno:Q",
                        scale=alt.Scale(scheme="redyellowgreen"),
                        legend=None,
                    ),
                    tooltip=[
                        "ra_nome:N",
                        alt.Tooltip("indice_qualidade_entorno:Q", title="Índice combinado", format=".1f"),
                        alt.Tooltip("indice_infraestrutura:Q", title="Índice de Infraestrutura", format=".1f"),
                        alt.Tooltip("indice_acessibilidade:Q", title="Índice de Acessibilidade", format=".1f"),
                    ],
                )
                .properties(height=max(380, len(df_qualidade) * 22))
            )
            st.altair_chart(chart, use_container_width=True)
        except Exception as e:
            st.warning(f"Não foi possível gerar este gráfico: {e}")
    else:
        st.info("Dados geoespaciais não disponíveis ou PostGIS não acessível.")

    st.divider()

    # ---- 7.10 Acesso ao Transporte Público por RA (paradas de ônibus OSM) ----
    st.subheader("Acesso ao Transporte Público por Região Administrativa")
    st.caption(
        "Cruza, por Região Administrativa, o número de **paradas/plataformas de ônibus** "
        "mapeadas no OpenStreetMap (extrato Overpass API — malha de transporte coletivo "
        "convencional, bem mais densa que as estações estruturantes) localizadas na região "
        "com a distância média que as escolas dessa RA precisam percorrer até a parada de "
        "ônibus mais próxima (esteja ela dentro ou fora da própria RA)."
    )
    with st.spinner("Calculando acesso das escolas às paradas de ônibus (OSM) via PostGIS…"):
        df_transp = load_onibus_osm_por_ra()
    if df_transp is not None and not df_transp.empty:
        try:
            order_transp = df_transp.sort_values("distancia_media_onibus_m")["ra_nome"].tolist()
            base_transp = alt.Chart(df_transp).encode(
                y=alt.Y("ra_nome:N", sort=order_transp, title="Região Administrativa", axis=alt.Axis(labelOverlap=False)),
            )
            barras_transp = base_transp.mark_bar(color="#2b83ba").encode(
                x=alt.X("distancia_media_onibus_m:Q", title="Distância média até a parada de ônibus mais próxima (m)"),
                tooltip=[
                    "ra_nome:N",
                    alt.Tooltip("distancia_media_onibus_m:Q", title="Distância média (m)", format=",.0f"),
                    alt.Tooltip("n_paradas:Q", title="Nº de paradas de ônibus na RA"),
                ],
            )
            pontos_transp = base_transp.mark_circle(size=90, color="#d7191c").encode(
                x=alt.X("n_paradas:Q", title="Nº de paradas de ônibus na RA"),
                tooltip=[
                    "ra_nome:N",
                    alt.Tooltip("n_paradas:Q", title="Nº de paradas de ônibus"),
                ],
            )
            st.altair_chart(
                alt.layer(barras_transp, pontos_transp)
                .resolve_scale(x="independent")
                .properties(height=max(380, len(df_transp) * 22)),
                use_container_width=True,
            )
            st.caption(
                "Barras azuis = distância média das escolas até a parada de ônibus mais próxima (eixo inferior) "
                "· Pontos vermelhos = nº de paradas de ônibus mapeadas dentro da própria RA (eixo superior). "
                "RAs com pontos próximos da origem e barras longas concentram poucas paradas e exigem deslocamentos maiores."
            )
        except Exception as e:
            st.warning(f"Não foi possível gerar este gráfico: {e}")
    else:
        st.info("Dados não disponíveis ou PostGIS não acessível.")

    st.divider()

    # ---- 7.11 Sessão Transporte: acesso ao ônibus × qualidade do entorno ----
    st.markdown("<h3 class='section-header'>Transporte</h3>", unsafe_allow_html=True)

    QUADRANTE_CORES = {
        "Bom acesso + bom entorno": "#1a9641",
        "Bom acesso + entorno carente": "#8856a7",
        "Acesso ruim + bom entorno": "#fdae61",
        "Dupla desvantagem (acesso ruim + entorno carente)": "#d7191c",
    }

    with st.spinner("Calculando classificação de acesso ao ônibus × qualidade do entorno via PostGIS…"):
        df_quadrante = load_quadrante_acesso_onibus_entorno()

    if df_quadrante is not None and not df_quadrante.empty:
        st.subheader("Transporte e educação: o acesso ao ônibus reflete a qualidade do entorno escolar?")
        correlacao = df_quadrante["distancia_onibus_m"].corr(df_quadrante["indice_qualidade_entorno"])
        st.caption(
            "Cruza, para cada escola, a **distância até a parada de ônibus mais próxima** "
            "(quanto menor, melhor o acesso ao transporte coletivo) com o seu **Índice de "
            "Qualidade do Entorno** (0–100, calculado pela proximidade a saúde, segurança, "
            "cultura, lazer e outros equipamentos públicos). Se escolas mal servidas por "
            "transporte também tendem a ter pior entorno, isso indica uma **dupla "
            "desvantagem geográfica**: dificuldade de chegar à escola somada à carência de "
            "equipamentos ao redor dela — ambas com potencial de afetar a frequência e o "
            f"desempenho escolar. Correlação observada nesta base: **{correlacao:.2f}** "
            + ("(negativa — escolas mais distantes do ônibus tendem a ter pior entorno)."
               if correlacao < -0.1 else
               "(positiva — escolas mais distantes do ônibus tendem a ter melhor entorno)."
               if correlacao > 0.1 else
               "(fraca — não há relação clara entre as duas variáveis nesta base).")
        )

        scatter = (
            alt.Chart(df_quadrante)
            .mark_circle(size=55, opacity=0.55, color="#2b83ba")
            .encode(
                x=alt.X("distancia_onibus_m:Q", title="Distância até a parada de ônibus mais próxima (m)"),
                y=alt.Y("indice_qualidade_entorno:Q", title="Índice de Qualidade do Entorno (0–100)"),
                tooltip=[
                    alt.Tooltip("nome_escola:N", title="Escola"),
                    alt.Tooltip("distancia_onibus_m:Q", title="Distância ao ônibus (m)"),
                    alt.Tooltip("indice_qualidade_entorno:Q", title="Índice de Qualidade do Entorno"),
                ],
            )
        )
        linha_tendencia = scatter.transform_regression(
            "distancia_onibus_m", "indice_qualidade_entorno"
        ).mark_line(color="#d7191c", strokeDash=[6, 3])

        st.altair_chart((scatter + linha_tendencia).properties(height=420), use_container_width=True)

        st.markdown(
            "**Escolas em situação de dupla desvantagem** "
            "(entre as 25% mais distantes da parada de ônibus mais próxima *e* "
            "entre as 25% com pior Índice de Qualidade do Entorno):"
        )
        limiar_dist = df_quadrante["distancia_onibus_m"].quantile(0.75)
        limiar_indice = df_quadrante["indice_qualidade_entorno"].quantile(0.25)
        df_dupla = df_quadrante[
            (df_quadrante["distancia_onibus_m"] >= limiar_dist)
            & (df_quadrante["indice_qualidade_entorno"] <= limiar_indice)
        ].copy()
        if df_dupla.empty:
            st.info("Nenhuma escola se enquadra simultaneamente nos dois critérios nesta base.")
        else:
            df_dupla["Escola"] = df_dupla["nome_escola"].where(
                df_dupla["nome_escola"].notna() & (df_dupla["nome_escola"].str.strip() != ""),
                "Escola " + df_dupla["id_escola"].astype(str),
            )
            st.dataframe(
                df_dupla[["Escola", "distancia_onibus_m", "indice_qualidade_entorno"]]
                .rename(columns={
                    "distancia_onibus_m": "Distância ao ônibus (m)",
                    "indice_qualidade_entorno": "Índice de Qualidade do Entorno",
                })
                .sort_values("Distância ao ônibus (m)", ascending=False),
                use_container_width=True,
                hide_index=True,
            )

        st.divider()
        st.subheader("Quantidade de escolas por classificação de acesso ao ônibus × qualidade do entorno")
        st.caption(
            "Cada escola é classificada cruzando sua **distância até a parada de ônibus (OSM) "
            "mais próxima** com seu **Índice de Qualidade do Entorno**, em relação às medianas "
            "do DF — a mesma classificação usada para colorir as escolas no mapa "
            "'Transporte Coletivo (Paradas e Linhas de Ônibus - OSM)'. Visão geral de quantas "
            "escolas do DF se encaixam em cada uma das quatro combinações."
        )
        df_contagem_quadrante = (
            df_quadrante["quadrante"].value_counts().reindex(QUADRANTES_ACESSO_ENTORNO).reset_index()
        )
        df_contagem_quadrante.columns = ["quadrante", "n_escolas"]
        grafico_quadrante = (
            alt.Chart(df_contagem_quadrante)
            .mark_bar()
            .encode(
                x=alt.X("n_escolas:Q", title="Nº de escolas"),
                y=alt.Y("quadrante:N", title=None, sort=QUADRANTES_ACESSO_ENTORNO,
                        axis=alt.Axis(labelLimit=280)),
                color=alt.Color(
                    "quadrante:N",
                    scale=alt.Scale(domain=QUADRANTES_ACESSO_ENTORNO, range=list(QUADRANTE_CORES.values())),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("quadrante:N", title="Classificação"),
                    alt.Tooltip("n_escolas:Q", title="Nº de escolas"),
                ],
            )
            .properties(height=220)
        )
        st.altair_chart(grafico_quadrante, use_container_width=True)

        st.divider()
        st.subheader("Proporção dessas classificações por Região Administrativa")
        st.caption(
            "Para cada Região Administrativa, mostra a **proporção relativa** de escolas em "
            "cada uma das quatro classificações — revela em quais regiões a 'dupla "
            "desvantagem' (acesso ruim ao ônibus + entorno carente, em vermelho) é "
            "proporcionalmente mais comum, independentemente do tamanho da rede local."
        )
        df_prop = (
            df_quadrante.groupby(["ra_nome", "quadrante"]).size().reset_index(name="n_escolas")
        )
        ordem_ra = (
            df_prop.groupby("ra_nome")
            .apply(lambda g: g.loc[g["quadrante"] == QUADRANTES_ACESSO_ENTORNO[3], "n_escolas"].sum() / g["n_escolas"].sum())
            .sort_values(ascending=False)
            .index.tolist()
        )
        grafico_prop_ra = (
            alt.Chart(df_prop)
            .mark_bar()
            .encode(
                y=alt.Y("ra_nome:N", title="Região Administrativa", sort=ordem_ra,
                        axis=alt.Axis(labelOverlap=False)),
                x=alt.X("n_escolas:Q", title="Proporção de escolas", stack="normalize",
                        axis=alt.Axis(format="%")),
                color=alt.Color(
                    "quadrante:N",
                    title="Classificação",
                    scale=alt.Scale(domain=QUADRANTES_ACESSO_ENTORNO, range=list(QUADRANTE_CORES.values())),
                ),
                order=alt.Order("quadrante:N", sort="ascending"),
                tooltip=[
                    alt.Tooltip("ra_nome:N", title="Região Administrativa"),
                    alt.Tooltip("quadrante:N", title="Classificação"),
                    alt.Tooltip("n_escolas:Q", title="Nº de escolas"),
                ],
            )
            .properties(height=max(380, df_prop["ra_nome"].nunique() * 22))
        )
        st.altair_chart(grafico_prop_ra, use_container_width=True)
    else:
        st.info("Dados não disponíveis ou PostGIS não acessível.")

    st.divider()

    # ------------------------------------------------------------------
    # 8. Exploração tabular (mantida intacta)
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
