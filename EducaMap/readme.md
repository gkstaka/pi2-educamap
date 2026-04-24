# Estrutura de pastas

EducaMap/
├── app/                      # Código fonte da aplicação
│   ├── main.py               # Script principal (Streamlit + Folium)
│   ├── pages/                # (Opcional) Para multi-páginas no Streamlit
│   ├── modules/              # Lógica de Inteligência Geográfica e cálculos
│   ├── utils/                # Conexão com DB e tratamentos de dados
│   └── requirements.txt      # Bibliotecas (pandas, sqlalchemy, psycopg2-binary, etc.)
├── data/                     # Arquivos fonte originais (CSVs/Planilhas)
│   └── raw/                  # Dados brutos antes de irem para o Postgres
├── db/                       # Scripts de inicialização do banco
│   └── init.sql              # Criação de tabelas e carga inicial (DML/DDL)
├── .env                      # Variáveis de ambiente (senhas e nomes do DB)
├── .gitignore                # Arquivos para o Git ignorar (venv, .env, __pycache__)
├── Dockerfile                # Receita da imagem do container Python
└── docker-compose.yml        # Orquestrador dos containers (App + DB)
