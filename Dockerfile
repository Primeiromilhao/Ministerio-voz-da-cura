FROM python:3.10-slim

# Instala dependências do sistema (incluindo ffmpeg, ffprobe e curl para instalar o Deno)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg xz-utils curl unzip && \
    rm -rf /var/lib/apt/lists/*

# Instala o Deno (runtime JS necessário pelo yt-dlp para extração do YouTube)
RUN curl -fsSL https://deno.land/install.sh | sh
ENV DENO_DIR="/root/.deno"
ENV PATH="/root/.deno/bin:${PATH}"

WORKDIR /app

# Copia os arquivos de dependência e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY main.py .
COPY static/ ./static/

# Expõe a porta que o Uvicorn irá rodar
EXPOSE 8000

# Executa o servidor uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
