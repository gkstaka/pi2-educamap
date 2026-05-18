## Definição de containers docker
Criação de containers para manter o projeto python e o banco de dados.
Estudo do Docker Composer para manutenção dos containers.

## Estrutura de pastas
```
EducaMap/
├── app/
│   ├── main.py          # Seu código Streamlit/Python
│   └── requirements.txt # Dependências (adicione 'psycopg2-binary' ou 'sqlalchemy')
├── Dockerfile           # Instruções para o container Python
└── docker-compose.yml   # Orquestrador dos containers
```
## Uso do PostGreSQL como fonte de dados.
Tratar os dados dos arquivos fonte e utilizados no banco.
Fazer modelagem do banco de dados conforme as tabelas definidas

## Definir o Interface do Usuário
Cada interface deve conter seus filtros apropriados que deverão ser estudados previamente, evitando redundância e discrepâncias.
As telas deverão mostrar informações claras, o mapa deverá ocupar toda tela e ver se tem como os filtros e botões sobreporem o mapa. Como acontece no google mapas.

## Inteligência Geográfica
Implementar cálculo de raio de atendimento de cada escola de acordo com suas variáveis de ambiente.
Implementar instrumental para identificação dos desertos de matrículas por meio do cruzamento de dados educacionais.

## Documentação do sistema
Documentar toda estrutura do sistema, deixando claro o que cada componente faz.
Criar um arquivo .md dentro de cada pasta elucidando o comportamento do conteúdo.

## Elaboração do Relatório
A partir da documentação do sistema, criar o relatório de apresentação para o Professor.

## Apresentação Inicial do Sistema
Criar página de apresentação inicial para o Usuário ficar encantado e ter vontade de usar nosso sistema.

## Relatórios
Implementar funcionalidade de elaboração de relatório a partir dos dados contidos no banco de dados. (ver se dá pra fazer até o fim do semestre).

## Justificativa Urbanística para cálculo dos raios.
Para estimar os raios de influência ou de atendimento de uma escola, geralmente consideramos a distância de caminhada 
(walkability) ou a densidade demográfica da região. No contexto urbano brasileiro, podemos usar referências do urbanismo 
e de políticas públicas de educação.

Proposta de Estimativa de Raios

Porte da Escola	Raio Estimado	Justificativa Urbanística

- PEQUENO	300m a 500m	Equivale a uma caminhada de 5 a 7 minutos. Ideal para escolas de educação infantil ou bairros muito densos.

- MÉDIO	800m a 1000m	Cerca de 10 a 12 minutos de caminhada. É o padrão comum para o atendimento de Ensino Fundamental I em áreas urbanas.

- GRANDE	1500m a 2000m	Abrange um bairro inteiro ou áreas adjacentes. Comum para Ensino Médio ou escolas com grande oferta de vagas.

- ESPECIAL	3000m+	Escolas de referência técnica ou integral que atraem alunos de regiões mais distantes (uso de transporte público/escolar).
