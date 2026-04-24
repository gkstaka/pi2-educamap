# 1. Imagem Python leve
FROM python:3.11-slim

# 2. Instala dependências para o PostgreSQL e o netcat para o healthcheck
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    netcat-openbsd \
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
# CMD ["sh", "-c", "until nc -z db 5432; do echo 'Aguardando banco de dados...'; sleep 2; done; python -c 'from app.modules.data_utils import load_inicial_data; load_inicial_data()' && streamlit run main.py"]

CMD ["sh", "-c", "until nc -z db 5432; do echo 'Aguardando banco de dados...'; sleep 2; done; python3 -m app.modules.data_utils && streamlit run main.py"]
