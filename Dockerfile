FROM python:3.10-slim

# Instala dependências do sistema (incluindo ffmpeg e ffprobe)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg xz-utils && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia os arquivos de dependência e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY . .

# Expõe a porta que o Uvicorn irá rodar
EXPOSE 8000

# Executa o servidor uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
