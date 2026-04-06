import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd
from folium.plugins import MarkerCluster
from branca.element import Template, MacroElement

st.set_page_config(layout="wide", page_title="EducaMap")

st.markdown("""
    <style>
    .block-container {
        padding-top: 0rem;
        padding-bottom: 0rem;
        padding-left: 0rem;
        padding-right: 0rem;
    }
    </style>
    """, unsafe_allow_html=True)

template = """
{% macro html(this, kwargs) %}
<div id='maplegend' class='maplegend' 
    style='position: fixed; z-index:9999; border:2px solid grey; background-color:rgba(255, 255, 255, 0.9);
     border-radius:6px; padding: 10px; font-size:14px; right: 20px; bottom: 20px; color: black;'>
     
<div class='legend-title' style='color: black; font-weight: bold; margin-bottom: 5px;'>Legenda de Cobertura</div>
<div class='legend-scale'>
  <ul class='legend-labels' style='list-style: none; padding: 0; margin: 0;'>
    <li style='margin-bottom: 5px; color: black;'>
        <span style='display: inline-block; width: 16px; height: 16px; margin-right: 5px; vertical-align: middle; background: blue; opacity: 0.3; border: 1px solid black;'></span>
        Raio Interno (300m)
    </li>
    <li style='margin-bottom: 5px; color: black;'>
        <span style='display: inline-block; width: 16px; height: 16px; margin-right: 5px; vertical-align: middle; background: blue; opacity: 0.1; border: 1px solid black;'></span>
        Raio Externo (500m)
    </li>
    <hr style='margin: 5px 0; border: 0; border-top: 1px solid #ccc;'>
    <li style='margin-bottom: 5px; color: black;'>
        <span style='display: inline-block; width: 16px; height: 16px; margin-right: 5px; vertical-align: middle; background: gray; border: 1px solid black;'></span>
        Escola Privada
    </li>
    <li style='margin-bottom: 5px; color: black;'>
        <span style='display: inline-block; width: 16px; height: 16px; margin-right: 5px; vertical-align: middle; background: blue; border: 1px solid black;'></span>
        Escola Pública
    </li>
  </ul>
</div>
</div>
{% endmacro %}
"""

st.title("EducaMap - Visualização de Escolas")

@st.cache_data # Cache para não ler o arquivo toda hora que interagir com o mapa
def load_data():
    df = pd.read_csv('Analise-Tabela_da_lista_das_escolas-Detalhado.csv')
    
    for col in ['Latitude', 'Longitude']:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    df_clean = df.dropna(subset=['Latitude', 'Longitude'st.sidebar.button("Limpar Filtros", on_click=limpar_filtros)])
    return df, df_clean

df_completo, df_escola = load_data()

location_brl = [-15.793889, -47.8828]
m = folium.Map(location=location_brl, zoom_start=11, tiles="OpenStreetMap")
folium.Marker(
    location=location_brl,
    popup="Brasília",
    tooltip="Clique aqui",
    icon=folium.Icon(color="red", icon="home", prefix="fa")
).add_to(m)

st.sidebar.header("Filtros")

categorias_selecionadas = st.sidebar.multiselect(
    "Categoria Administrativa",
    options=df_escola['Categoria Administrativa'].unique(),
    default=[]
)

localizacoes_selecionadas = st.sidebar.multiselect(
    "Localização (Urbana/Rural)",
    options=df_escola['Localização'].unique(),
    default=[]
)

df_filtrado = df_escola.copy()

if categorias_selecionadas:
    df_filtrado = df_filtrado[df_filtrado['Categoria Administrativa'].isin(categorias_selecionadas)]

if localizacoes_selecionadas:
    df_filtrado = df_filtrado[df_filtrado['Localização'].isin(localizacoes_selecionadas)]

if not categorias_selecionadas and not localizacoes_selecionadas:
    df_filtrado = pd.DataFrame(columns=df_escola.columns)
    st.info("💡 Selecione uma Categoria ou Localização na barra lateral para visualizar as escolas no mapa.")

marker_cluster = MarkerCluster().add_to(m)

for i, row in df_filtrado.iterrows():
    lat, lon = row['Latitude'], row['Longitude']

    is_rural = str(row['Localização']).strip().upper() == 'RURAL'
    is_privada = str(row['Categoria Administrativa']).strip().upper() == 'PRIVADA'

    if is_rural:
        cor_base = "darkgreen" if is_privada else "green" 
    else:
        cor_base = "gray" if is_privada else "blue"
    # opacidade = 0.1 if is_privada else 0.1

    # --- RAIO EXTERNO' (500m) ---
    folium.Circle(
        location=[lat, lon],
        radius=500,
        color=cor_base,
        fill=True,
        fill_color=cor_base,
        fill_opacity=0.1,
        weight=1,
        dash_array='5, 5' 
    ).add_to(m)

    # --- RAIO INTERNO (300m) ---
    folium.Circle(
        location=[lat, lon],
        radius=300,
        color=cor_base,
        fill=True,
        fill_color=cor_base,
        fill_opacity=0.2,
        weight=1
    ).add_to(m)

    folium.Marker(
        location=[row['Latitude'], row['Longitude']],
        popup=f"<b>{row['Escola']}</b><br>{row['Endereço']}",
        tooltip=row['Escola'],
        #icon=folium.Icon(color="blue", icon="graduation-cap", prefix="fa")
        icon=folium.Icon(color=cor_base, icon="university", prefix="fa")
    ).add_to(marker_cluster)

# para imprimir a legenta
macro = MacroElement()
macro._template = Template(template)
m.get_root().add_child(macro)
#para imprimir o mapa
st_folium(m, width=1500, height=700, use_container_width=True)

with st.expander("Ver base de dados completa"):
    st.write(df_completo)

with st.expander("Ver base de dados limpos"):
    st.write(df_escola)

with st.expander("Ver Latitude e Longitude"):
    st.write(df_escola[['Escola','Latitude', 'Longitude']])

"""
Para estimar os raios de influência ou de atendimento de uma escola, geralmente consideramos a distância de caminhada 
(walkability) ou a densidade demográfica da região. No contexto urbano brasileiro, podemos usar referências do urbanismo 
e de políticas públicas de educação.

Proposta de Estimativa de Raios

Porte da Escola	Raio Estimado	Justificativa Urbanística
PEQUENO	300m a 500m	Equivale a uma caminhada de 5 a 7 minutos. Ideal para escolas de educação infantil ou bairros muito densos.
MÉDIO	800m a 1000m	Cerca de 10 a 12 minutos de caminhada. É o padrão comum para o atendimento de Ensino Fundamental I em áreas urbanas.
GRANDE	1500m a 2000m	Abrange um bairro inteiro ou áreas adjacentes. Comum para Ensino Médio ou escolas com grande oferta de vagas.
ESPECIAL	3000m+	Escolas de referência técnica ou integral que atraem alunos de regiões mais distantes (uso de transporte público/escolar).
    """
