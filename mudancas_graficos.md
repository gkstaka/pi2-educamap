# Aba "Gráficos" — EducaMap

Descrição da estrutura atual da página `EducaMap/app/pages/6_Graficos.py`,
incluindo as adições/reorganizações feitas nesta sessão (sessão dedicada a
**Transporte** e atualização do gráfico de acesso ao transporte público).

A página reúne, em sessões temáticas, os principais painéis analíticos do
EducaMap — do perfil cadastral das escolas até cruzamentos avançados entre
infraestrutura urbana, qualidade do entorno e acesso ao transporte coletivo.

## 1. Visão Geral

KPIs e indicadores gerais da base de escolas do DF (contagens, filtros
globais aplicados ao restante da página).

## 2. Catálogo de Escolas — DF

Painel cadastral com 4 gráficos:
- **Distribuição por Localização** (Urbana/Rural)
- **Rede de Ensino** (Estadual/Federal/Privada — Dependência Administrativa)
- **Porte das Escolas** (faixas de matrícula)
- **Modalidades de Ensino Oferecidas** (top 10 mais frequentes)

## 3. Cruzamento: Rede de Ensino × Porte

Tabela/gráfico cruzando a rede de ensino com o porte das escolas, revelando
o perfil predominante de cada rede (ex.: concentração de escolas pequenas em
redes específicas).

## 4. Rede Pública — Matrículas 2023 (SEEDF + Federal)

Painel com dados de matrícula da rede pública, com 4 visões:
- **Escolas por Região Administrativa**
- **Distribuição por Nível de Ensino**
- **Distribuição por Raça/Cor**
- **Distribuição por Localização**

## 5. Painéis Analíticos Avançados

Conjunto de cruzamentos mais elaborados, a maioria agregada por Região
Administrativa (RA) e usando dados geoespaciais via PostGIS:

1. **Taxa Bruta de Frequência Escolar por Faixa Etária — Brasil (Censo 2022)**
   — curva de frequência escolar por idade, contextualizando o cenário
   nacional.
2. **Funil de Matrículas por Ano/Série Escolar — Rede Pública 2023** —
   funil de evasão ao longo do Ensino Fundamental e Médio.
3. **Composição Pública × Privada por Nível de Ensino** — proporção de
   matrículas públicas vs. privadas em cada nível de ensino.
4. **Índice de Infraestrutura de Entorno por Região Administrativa** —
   quantidade/diversidade de equipamentos públicos (saúde, segurança,
   cultura, lazer etc.) próximos às escolas de cada RA.
5. **Diversidade de Equipamentos Culturais por Região Administrativa** —
   variedade de tipos de equipamentos culturais disponíveis por RA.
6. **Condição dos Equipamentos de Esporte e Lazer** — estado de conservação
   dos equipamentos esportivos/de lazer do entorno escolar.
7. **Acessibilidade do Entorno Escolar por Região Administrativa** —
   distância média das escolas aos equipamentos públicos mais próximos,
   por RA.
8. **Oferta de Capacidade Estimada por Região Administrativa** — capacidade
   de matrícula/oferta agregada por RA.
9. **Índice de Qualidade do Entorno Escolar por Região Administrativa** —
   índice combinado (infraestrutura + acessibilidade), 0–100, por RA.
10. **Acesso ao Transporte Público por Região Administrativa** *(atualizado
    nesta sessão)* — combo chart (barras de distância média + pontos de
    contagem) cruzando, por RA, o número de **paradas de ônibus mapeadas no
    OpenStreetMap** com a distância média das escolas até a parada mais
    próxima. Substituiu a versão anterior, que usava as 43 estações
    estruturantes do Geoportal IDE-DF (`load_transporte_por_ra`, removida);
    a nova fonte (`load_onibus_osm_por_ra`) reflete uma malha de transporte
    coletivo muito mais densa (1.937 paradas).

## 6. Transporte *(nova sessão)*

Sessão dedicada a aprofundar a relação entre **acesso ao ônibus convencional
(OSM)** e **qualidade do entorno escolar**, consolidando análises que antes
estavam espalhadas na página "Mapa de Qualidade do Entorno" (mapa de ônibus
OSM). Todas reaproveitam a função compartilhada
`load_quadrante_acesso_onibus_entorno()`, que classifica cada escola em um
dos 4 quadrantes (acesso ao ônibus × Índice de Qualidade do Entorno, em
relação às medianas do DF):

- 🟢 Bom acesso + bom entorno
- 🟣 Bom acesso + entorno carente
- 🟠 Acesso ruim + bom entorno
- 🔴 Dupla desvantagem (acesso ruim + entorno carente)

Painéis da sessão:

1. **"Transporte e educação: o acesso ao ônibus reflete a qualidade do
   entorno escolar?"** — gráfico de dispersão (Altair, com linha de
   tendência) cruzando a distância de cada escola até a parada de ônibus
   mais próxima com seu Índice de Qualidade do Entorno; exibe a correlação
   calculada (≈ **-0,81** nos dados atuais — escolas mais distantes do
   ônibus tendem a ter pior entorno) e uma tabela com as escolas em **dupla
   desvantagem geográfica** (25% mais distantes do ônibus *e* 25% com pior
   índice de entorno — 154 escolas identificadas nesta base).
2. **"Quantidade de escolas por classificação de acesso ao ônibus ×
   qualidade do entorno"** — gráfico de barras horizontais com a contagem
   de escolas em cada um dos 4 quadrantes (372 / 212 / 226 / 356),
   coloridas com a mesma paleta usada no mapa de ônibus OSM.
3. **"Proporção dessas classificações por Região Administrativa"** —
   gráfico de barras empilhadas normalizado (100%) mostrando, para cada uma
   das 35 RAs, a proporção relativa das 4 classificações, ordenado pela
   proporção de escolas em situação de dupla desvantagem.

> Esses três painéis foram movidos da página "Mapa de Qualidade do Entorno"
> (mapa "Transporte Coletivo - OSM") para esta sessão, agrupando as análises
> de transporte num único lugar e evitando duplicar consultas pesadas ao
> PostGIS nas duas páginas.

## 7. Exploração de Dados

Tabela navegável/filtrável com busca textual pelo nome da escola e botão
para baixar os dados filtrados em CSV.

## Arquivos relacionados

- `EducaMap/app/pages/6_Graficos.py` — página em si; nova sessão
  "Transporte" e atualização do gráfico "Acesso ao Transporte Público por
  Região Administrativa"
- `EducaMap/app/modules/data_utils.py` — `load_onibus_osm_por_ra` (nova,
  substitui `load_transporte_por_ra`) e `load_quadrante_acesso_onibus_entorno`
  (reaproveitada da página de mapas) usadas pela nova sessão
