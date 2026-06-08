# Integração de Transporte Público — EducaMap

Resumo das alterações desta sessão, que adicionam uma nova dimensão de análise
ao app: **acesso ao transporte público e sua relação com a qualidade do
entorno escolar**.

## 0. Página "Mapa de Qualidade do Entorno Escolar"

A página `EducaMap/app/pages/5_Mapa_Qualidade_Entorno.py` reúne, num único
seletor "Tipo de mapa", todas as visualizações geoespaciais que cruzam a
localização das escolas com a infraestrutura urbana do DF. Com as adições
desta sessão, ela passa a contar com **8 visualizações**:

1. **Região Administrativa** — mapa coroplético do DF: cada RA é colorida
   pelo Índice de Qualidade do Entorno Escolar (0–100), que combina o Índice
   de Infraestrutura (quantidade de equipamentos públicos por escola) com o
   Índice de Acessibilidade (distância média até o equipamento mais
   próximo). Inclui ranking das RAs.
2. **Heatmap por escola** — versão granular do índice anterior: cada escola
   contribui individualmente com seu Índice de Acessibilidade (0–100),
   interpolado num heatmap que revela focos de boa/má cobertura mesmo dentro
   de uma mesma RA. Inclui ranking das escolas com melhor/pior entorno.
3. **Oferta × Qualidade do Entorno** — cruza a capacidade de
   matrícula/oferta das escolas por RA com o índice de qualidade do entorno,
   classificando as RAs em quadrantes (alta/baixa oferta × bom/mau entorno).
4. **Urbano × Rural (acessibilidade)** — compara a distância média aos
   equipamentos públicos entre escolas urbanas e rurais, evidenciando a
   disparidade de acesso conforme a localização.
5. **Rede de Ensino × Entorno** — compara o Índice de Qualidade do Entorno
   das RAs segmentado por rede de ensino (Estadual/Federal/Privada),
   colorindo as escolas conforme sua rede.
6. **Porte da Escola × Entorno** — relaciona o porte da escola (faixas de
   matrícula) com o índice de qualidade do entorno da RA onde está
   localizada.
7. **Transporte Público (Metrô/BRT/Terminais)** *(novo)* — estações
   estruturantes do Geoportal IDE-DF e distância das escolas até elas.
8. **Transporte Coletivo (Paradas e Linhas de Ônibus - OSM)** *(novo)* —
   malha de ônibus convencional do OpenStreetMap, com checkbox para
   sobrepor as escolas classificadas por quadrante (acesso ao ônibus ×
   qualidade do entorno). As análises cruzadas derivadas dessa
   classificação (dispersão, correlação, contagens e proporções por RA)
   foram centralizadas na aba **Gráficos**, na sessão "Transporte" — ver
   item 2 abaixo.

Todas as visualizações usam o helper `_nome_escola()` para exibir o nome
real da escola nos tooltips (com *fallback* para "Escola #id" quando o nome
não está disponível), e seguem o mesmo padrão visual: mapa Folium
interativo + legenda + tabela(s) de ranking/detalhamento abaixo.

## 1. Camada de estações estruturantes (Geoportal IDE-DF/SEDUH)

- **`carregar_camada_transporte_remota()` / `_garantir_camada_transporte()`**
  (`EducaMap/app/modules/data_utils.py`): busca, via serviço ArcGIS REST do
  Geoportal IDE-DF, a camada pública "Estações e Terminais" (estações de
  metrô, BRT e terminais DFTrans — 43 feições) e persiste como tabela PostGIS
  `estacoes_terminais_transporte`. Hooked no pipeline de carga
  (`load_shapefiles_data`), com checagem de idempotência.
- **`load_distancia_transporte_por_escola()`**: distância de cada escola até
  a estação/terminal estruturante mais próxima (KNN espacial via
  `JOIN LATERAL`).
- Novo mapa **"Transporte Público (Metrô/BRT/Terminais)"** em
  `5_Mapa_Qualidade_Entorno.py`: estações como losangos coloridos por tipo,
  escolas como círculos coloridos por distância (tercis), tabela de ranking
  das 10 escolas mais próximas/distantes.

> **Nota:** a função `load_transporte_por_ra()` (que agregava por RA o nº de
> estações estruturantes e a distância média das escolas até elas) foi
> **removida** — o gráfico "Acesso ao Transporte Público por Região
> Administrativa" em `6_Graficos.py` foi atualizado para usar a malha de
> **paradas de ônibus do OSM** (bem mais densa: 1.937 paradas vs. 43
> estações estruturantes), via a nova função `load_onibus_osm_por_ra()` —
> ver item 2 abaixo.

## 2. Camada de ônibus convencional (OpenStreetMap / Overpass API)

- Extrato local do OSM (`EducaMap/data/raw/OverpassAPI`, ~2,2 GB, formato
  XML) processado via *streaming parse* (`xml.etree.ElementTree.iterparse`)
  para extrair:
  - **1.937 paradas/plataformas de ônibus** (`highway=bus_stop`,
    `public_transport=platform|stop_position`)
  - **27 linhas de ônibus** com traçado geométrico montado a partir das
    *relations* `route=bus`
- **`carregar_camada_onibus_osm()` / `_garantir_camada_onibus_osm()`**:
  ingestão única (≈ 85 s), persiste como tabelas PostGIS
  `paradas_onibus_osm` (pontos) e `linhas_onibus_osm` (linhas/multilinhas).
  Também hooked no pipeline de carga, com checagem de idempotência.
- **`load_paradas_onibus_osm()` / `load_linhas_onibus_osm()`**: loaders
  GeoDataFrame para exibição no mapa.
- **`load_distancia_onibus_osm_por_escola()`**: distância de cada escola até
  a parada de ônibus (OSM) mais próxima (KNN espacial via `JOIN LATERAL`).
- **`load_onibus_osm_por_ra()`** *(novo)*: nº de paradas de ônibus (OSM) e
  distância média das escolas até a parada mais próxima, agregados por
  Região Administrativa — substitui `load_transporte_por_ra()` como fonte do
  gráfico "Acesso ao Transporte Público por Região Administrativa".
- Novo mapa **"Transporte Coletivo (Paradas e Linhas de Ônibus - OSM)"** em
  `5_Mapa_Qualidade_Entorno.py`:
  - Paradas como pontos azuis e linhas de ônibus traçadas com paleta
    categórica (uma cor por linha).
  - Checkbox para sobrepor as escolas no mapa, **classificadas por quadrante**
    cruzando acesso ao ônibus × Índice de Qualidade do Entorno (em relação às
    medianas do DF):
    - 🟢 Bom acesso + bom entorno
    - 🟣 Bom acesso + entorno carente
    - 🟠 Acesso ruim + bom entorno
    - 🔴 Dupla desvantagem (acesso ruim + entorno carente)
  - A página exibe um aviso indicando que a análise cruzada derivada dessa
    classificação foi movida para a aba Gráficos (ver abaixo), evitando
    duplicar consultas pesadas ao PostGIS nas duas páginas.
- Nova sessão **"Transporte"** em `6_Graficos.py`, reunindo as análises que
  cruzam acesso ao transporte coletivo × qualidade do entorno (todas
  reaproveitando a função compartilhada
  `load_quadrante_acesso_onibus_entorno()`, que centraliza a lógica de
  classificação antes duplicada inline):
  - **"Transporte e educação: o acesso ao ônibus reflete a qualidade do
    entorno escolar?"** — gráfico de dispersão (Altair, com linha de
    tendência) cruzando distância ao ônibus × Índice de Qualidade do Entorno
    por escola, cálculo de correlação (≈ **-0,81** nos dados atuais —
    escolas mais distantes do ônibus tendem a ter pior entorno) e tabela das
    escolas em **dupla desvantagem geográfica** (25% mais distantes do
    ônibus *e* 25% com pior índice de entorno — 154 escolas identificadas).
  - **"Quantidade de escolas por classificação..."** — barras horizontais
    com a contagem de escolas em cada um dos 4 quadrantes (372 / 212 / 226
    / 356), coloridas com a mesma paleta do mapa.
  - **"Proporção dessas classificações por Região Administrativa"** —
    barras empilhadas normalizadas (100%) mostrando, para cada uma das 35
    RAs, a proporção relativa das 4 classificações, ordenadas pela
    proporção de escolas em dupla desvantagem.
  - Essas três visualizações estavam originalmente na página do mapa de
    ônibus OSM e foram movidas para cá para agrupar todas as análises de
    transporte num único lugar da aba Gráficos.

## 3. Outros ajustes pontuais

- Adicionado `e.nome_escola` ao SELECT de `load_escolas_contexto_entorno` e
  `load_distancia_transporte_por_escola`, e criado o helper `_nome_escola()`
  em `5_Mapa_Qualidade_Entorno.py` para exibir o nome real da escola nos
  tooltips dos mapas (em vez de "Escola #id").
- Correção de bug: `gpd.read_postgis(..., geom_col="geom")` retorna `Series`
  sem o atributo `.geometry` — uso de `row["geom"]` em vez de `row.geometry`
  ao desenhar marcadores das estações.

## Arquivos alterados

- `EducaMap/app/modules/data_utils.py` — novas funções de ingestão e loaders
  (`carregar_camada_onibus_osm`, `load_paradas_onibus_osm`,
  `load_linhas_onibus_osm`, `load_distancia_onibus_osm_por_escola`,
  `load_onibus_osm_por_ra`, `load_quadrante_acesso_onibus_entorno`); remoção
  de `load_transporte_por_ra` (substituída por `load_onibus_osm_por_ra`)
- `EducaMap/app/pages/5_Mapa_Qualidade_Entorno.py` — novos mapas de
  transporte (estações estruturantes e malha de ônibus OSM com
  classificação por quadrante)
- `EducaMap/app/pages/6_Graficos.py` — gráfico de acesso ao transporte por
  RA atualizado para a malha de ônibus OSM, e nova sessão "Transporte"
  reunindo a análise cruzada transporte × qualidade do entorno (dispersão,
  correlação, dupla desvantagem, contagem por classificação e proporção
  por RA)
