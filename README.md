# EduMapa
O __Edumapa__ é uma ferramenta de inteligência geográfica voltada para o planejamento educacional no Distrito Federal. Utilizando os dados do INEP e do INGE, o projeto permite visualizar a densidade escolar e a abrangência de atendimento de cada unidade.

Os locais que tenha falta de abrangência, visualizadas pelo mapa, devem ser possíveis focos de atencao para o planejamento e desenvolvimento. 
### Funcionalidades
- Cálculo de abrangência baseado na quantidade de matrículas possíveis para gerar um raio decabrangencia a partir da escola.

- Filtros dinâmicos baseado no tipo de escola rural ou urbana para modificar o raio de abrangência. 

- Observações sobre escolas públicas e privadas para uma visão geral mais objetiva.

- ... TBD

## 01 - Rodar ambiente virtual
Após clonar o repositório, navegue para a pasta principal do projeto e crie o ambiente virtual em sua máquina com o comando:
`python -m venv venv`

Rodar o comando abaixo para ativar o ambiente virtual:
- Para Windows: `.\venv\Scripts\activate`
- BASH: `source venv/Scripts/activate `

## 02 - Requesitos
[adicionar pyenv para gerenciamento de versao python wio

pyenv --version para verificar ae tem instalado]

Se for necessário atualizar os imports do projeto, use:
`pip install -r requirements.txt`

Caso tenha instalado um pacote que ainda não estava no projeto, utilize o comando para adicioná-lo as dependencias:
`pip freeze > requirements.txt`

## 03 - Ferramentas
No momento, estamos usando Pandas do Python para leitura de dados.
Para a geolocalização, estamos sondando usar o StreamLit por suas bibliotecas pre-definitas.

A ser definido como usar banco de dados - [Container Docker citado como uma das opções]

## 04 - Links úteis
Instituto de Estudos e Pesquisas Educacionais - [INEP](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/inep-data)
 
Instituto Brasileiro de Geografia e Estatística - [IBGE](https://www.ibge.gov.br/estatisticas/sociais/educacao.html)
