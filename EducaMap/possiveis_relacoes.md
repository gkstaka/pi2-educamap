Possíveis cruzamentos (inputs)

Escolas ↔ Regiões administrativas: use listaEscolasDFInep.csv + regioes_administrativas.shp. Objetivo: saber em que RA cada escola está; agregações por RA.
Escolas ↔ Limite do DF: validação espacial usando limite_do_distrito_federal.shp.
Escolas ↔ Equipamentos públicos (saúde, parques, etc.): cruzar pontos de escolas com equipamentos_de_saude.shp, parques_urbanos.shp, espacos_comunitarios.shp para análises de acessibilidade e co-ocorrência.
Escolas ↔ Censos / indicadores socioeconômicos: use arquivos em EducaMap/data/raw/Censo_2022_IBGE/... para correlacionar desempenho/indicadores com características da área.
Escolas ↔ GeoJSON/shape de zonas (dissolver): calcular taxas por área (ex.: número de escolas por 1k habitantes).


Análises que você pode gerar (alto impacto)

Contagens por área: número de escolas por RA, por bairro, por 1000 hab.
Densidade / Heatmap: KDE ou mapa de calor de pontos de escolas.
Acessibilidade / distância: distância média da escola ao equipamento de saúde mais próximo; contagem de equipamentos dentro de 500m/1km (buffers).
Serviço/Buffer analysis: percentagem de escolas dentro de 500m de um parque ou unidade de saúde.
Spatial join + agregação: somar matrículas por região administrativa e calcular indicadores (média, mediana).
Nearest / sjoin_nearest: identificar o equipamento mais próximo para cada escola.
Clustering espacial: DBSCAN ou clustering hierárquico para identificar aglomerações de escolas.
Hotspot / Análise de sinais espaciais: Getis-Ord Gi* ou Moran's I (dependendo de bibliotecas).
Mapas e dashboards: choropleth por RA, mapas com pins agrupados, mapas interativos com folium/streamlit-folium.
Cross-theme correlation: correlacionar indicadores do Censo com presença/abundância de equipamentos públicos.
