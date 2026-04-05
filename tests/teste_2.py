import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd

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

st.title("EducaMap - Visualização de Escolas")

# def load_data():
#     df = pd.read_csv('Analise-Tabela_da_lista_das_escolas-Detalhado.csv')
#     df_clean = df.dropna(subset=['Latitude', 'Longitude'])
#     return df, df_clean

@st.cache_data # Cache para não ler o arquivo toda hora que interagir com o mapa
def load_data():
    df = pd.read_csv('Analise-Tabela_da_lista_das_escolas-Detalhado.csv')
    
    for col in ['Latitude', 'Longitude']:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    df_clean = df.dropna(subset=['Latitude', 'Longitude'])
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

# WARNING: Carrega todas as escolas! ------------------------------------
# for i, row in df_escola.iterrows():
#     folium.Marker(
#         location=[row['Latitude'], row['Longitude']],
#         popup=f"<b>{row['Escola']}</b><br>{row['Endereço']}",
#         tooltip=row['Escola'],
#         icon=folium.Icon(color="blue", icon="graduation-cap", prefix="fa")
#     ).add_to(m)

# WARNING: Carrega apenas 50 escolas -------------------------------------
# TODO: Traduzir o campo Porte da Escola para um valor numérioco para 
# efetuação dos calculos do tamanho dos raios.
for i, row in df_escola.head(75).iterrows():
    is_privada = str(row['Categoria Administrativa']).strip().upper() == 'PRIVADA'

    cor_raio = "gray" if is_privada else "blue"
    cor_marker = "gray" if is_privada else "blue"
    # opacidade = 0.1 if is_privada else 0.1

    folium.Circle(
        location=[row['Latitude'], row['Longitude']],
        # TODO: Aqui deverá ter o raio calculado segundo o porte da escola.
        radius=500, # 500 metros
        color=cor_raio,
        fill=True,
        fill_color=cor_raio,
        fill_opacity=0.1,
        weight=1 # Espessura da linha
    ).add_to(m)

    folium.Marker(
        location=[row['Latitude'], row['Longitude']],
        popup=f"<b>{row['Escola']}</b><br>{row['Endereço']}",
        tooltip=row['Escola'],
        #icon=folium.Icon(color="blue", icon="graduation-cap", prefix="fa")
        icon=folium.Icon(color=cor_marker, icon="university", prefix="fa")
    ).add_to(m)

st_folium(m, width=1500, height=700, use_container_width=True)

with st.expander("Ver base de dados completa"):
    st.write(df_completo)

with st.expander("Ver base de dados limpos"):
    st.write(df_escola)

with st.expander("Ver Latitude e Longitude"):
    st.write(df_escola[['Escola','Latitude', 'Longitude']])
