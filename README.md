# EduMapa
O __Edumapa__ é uma ferramenta de inteligência geográfica voltada para o planejamento educacional no Distrito Federal. Utilizando os dados do INEP e do INGE, o projeto permite visualizar a densidade escolar e a abrangência de atendimento de cada unidade.

## Problema
Muitas cidades brasileiras possuem "desertos educacionais" - regiões onde a oferta de escolas, biliotecas e equipamentos de educação é insuficiente ou inexistente. Esses territórios são difícies de identificar sem cruzamento de dados georreferenciados.

## Proposta de solução
Um mapa interativo que cruza dados públicos georreferenciados (localização de escolas, dados do Cenco, transporte público, renda) para identificar e visualizar áreas carentes de infraestrutura educacional, gerando alertas e relatórios para tomada de decisão.

## Público-alvo
Gestores públicos minicipais (Secretarias de Educação), ONGs que atuem em educação, pesquisadores urbanos e organizadores comunitários.

## Funcionalidades-chave
Mapa interativo com camadas de dados (escolas, população em idade escolar, transporte, renda); identificação automática de "desertos educacionais" por algoritmo de cruzamento; filtros por nível de ensino, faixa etária e tipo de equipamento; geração de relatórios por região; histórico temporal para acompanhar a evolução.

## Impacto esperado
Tornar visíveis as lacunas educacionais no território urbano, permitindo que gestores e ONGs direcionem recursos e açoes para onde são mais necessários, com base em evidências geográficas concretas.

## ODS 4 - Conexão
Meta 4.a - Construir e melhorar instalações físicas para educação apropriadas para crianças e sensíveis às deficiências e a gênero, proporcionando ambientes de aprendizagem seguros e inclusivos.

Os locais que tenha falta de abrangência, visualizadas pelo mapa, devem ser possíveis focos de atencao para o planejamento e desenvolvimento. 
### Funcionalidades
- Cálculo de abrangência baseado na quantidade de matrículas possíveis para gerar um raio decabrangencia a partir da escola.

- Filtros dinâmicos baseado no tipo de escola rural ou urbana para modificar o raio de abrangência. 

- Observações sobre escolas públicas e privadas para uma visão geral mais objetiva.

- ... TBD

# Na sua máquina

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

Para rodar os arquivos testes, utilize o comando `streamlit run `path_to_file/nome_arquivo.py`

# Na nuvem

Como Rodar o Projeto (Docker)

Esta seção descreve como clonar o repositório e colocar a aplicação em funcionamento utilizando Docker, o que garante que o ambiente seja idêntico em qualquer sistema operacional.
01 - Pré-requisitos

Antes de começar, você deve ter instalado em sua máquina:

    Git

    Docker Desktop (inclui o Docker Compose)

02 - Passo a Passo
1. Clonar o Repositório

Abra o seu terminal (PowerShell, Terminal do Mac ou Bash do Linux) e execute:
Bash

git clone https://github.com/SEU_USUARIO/EducaMap.git
cd EducaMap

2. Preparar o Arquivo de Dados

Certifique-se de que o arquivo listaEscolasDFInep.csv está na raiz da pasta EducaMap. O Docker irá ler este arquivo para popular o banco de dados automaticamente na primeira execução.
3. Subir a Aplicação

O comando é o mesmo para Windows, Mac e Linux:
Bash

docker-compose up --build

    O que este comando faz? Ele cria o banco de dados PostgreSQL, instala todas as bibliotecas do Python, popula as tabelas com o CSV e inicia o servidor do Streamlit.

4. Acessar o Mapa

Após o terminal mostrar a mensagem "You can now view your Streamlit app in your browser", acesse:

    Local: http://localhost:8501

03 - Comandos Específicos por Sistema Operacional

Embora o Docker padronize quase tudo, aqui estão algumas dicas para cada plataforma:
Sistema	Dica de Execução
Windows	Utilize o PowerShell ou Git Bash. Certifique-se de que o Docker Desktop está rodando no modo "Linux Containers" (padrão).
Mac (M1/M2/M3)	O Docker Desktop gerencia a arquitetura ARM automaticamente. Se houver erro de plataforma, o Docker usará a emulação linux/amd64.
Linux (Ubuntu)	Se não estiver usando o Docker Desktop, lembre-se de rodar com sudo caso o seu usuário não esteja no grupo docker: sudo docker-compose up --build.
04 - Manutenção e Limpeza

Se você precisar resetar o banco de dados para ler um CSV novo ou corrigir a estrutura das tabelas:
Bash

# Para parar e apagar os dados do banco (limpeza total)
docker-compose down -v

# Para subir novamente
docker-compose up --build

## 04 - Links úteis
Instituto de Estudos e Pesquisas Educacionais - [INEP](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/inep-data)
 
Instituto Brasileiro de Geografia e Estatística - [IBGE](https://www.ibge.gov.br/estatisticas/sociais/educacao.html)
https://paineis-ext.mpdft.mp.br/extensions/mashupeducacao/mashupeducacao.html
https://governancaeducadf.se.df.gov.br/portal-dados/

## Integrantes 
Antônio Alexandre Cavalcante Leite<br>
Carlos Eduardo Sousa Barcelos<br>
Gustavo Kooiti Silva Takahashi<br>
Lanay Guimarães de Paiva
