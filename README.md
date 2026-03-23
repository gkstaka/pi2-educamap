# EduMapa
O __Edumapa__ é uma ferramenta de inteligência geográfica voltada para o planejamento educacional no Distrito Federal. Utilizando os dados do INEP e do INGE, o projeto permite visualizar a densidade escolar e a abrangência de atendimento de cada unidade.

Os locais quw tenha falta de abranvrncia, visualizadas pelo mapa, devem ser possiveis focos de atencao parao. planejamento e desenvolvimwnto. 
### Funcionalidades
Calculo de abrangencia baseado na quantidade de matriculas possiveis para gefar um raio decabrangencia a partir da escola.

Filtros dinâmicos baseado no tipo de escola rurql ou urbana para modificar o raio de abrangencia. 

observacoes sobre escolas publicas e privadas para uma vidao geral maia objetiva.

## 01 - Rodar ambiente virtual
Criar o ambiente virtual em sua máquina com o comando:
> python -m venv venv

Rodar o comando abaixo para ativar o ambiente virtual:
> Para Windows: .\venv\Scripts\activate
>
> BASH: source venv/Scripts/activate

## 02 - Requesitos
Se for necessário atualizar os imports do projeto, use:
> pip install -r requirements.txt

Caso tenha instalado um pacote que ainda não estava no projeto, utilize o comando:
> pip freeze > requirements.txt

## 03 - Links úteis
Instituto de Estudos e Pesquisas Educacionais - [INEP](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/inep-data)
 
Instituto Brasileiro de Geografia e Estatística - [IBGE](https://www.ibge.gov.br/estatisticas/sociais/educacao.html)
