# 1. Imagem Python leve
FROM python:3.11-slim

# # 2. Instala dependências para o PostgreSQL e o netcat para o healthcheck
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     libpq-dev \
#     netcat-openbsd \
#     && rm -rf /var/lib/apt/lists/*

# 2. Instala dependências do PostgreSQL, netcat e ferramentas geoespaciais nativas do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    netcat-openbsd \
    binutils \
    libgdal-dev \
    gdal-bin \
    libproj-dev \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Define diretório de trabalho
WORKDIR /EducaMap

# 4. Instala bibliotecas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copia o projeto inteiro
COPY . .

# 6. Define o PATH para o Python enxergar a pasta 'app'
ENV PYTHONPATH=/EducaMap

# 7. Expõe o Streamlit
EXPOSE 8501

# 8. Comando de inicialização: Aguarda o banco, popula e sobe o app
CMD ["sh", "-c", "until nc -z db 5432; do echo 'Aguardando banco de dados...'; sleep 2; done; python3 -m app.modules.data_utils && streamlit run app/main.py"]
