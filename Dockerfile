FROM python:3.10-slim

# Instala dependencias do sistema: ffmpeg, curl, Node.js
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg curl xz-utils ca-certificates gnupg && \
    # Instala Node.js 20 LTS
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala o plugin bgutil-ytdlp-pot-provider (gera PO Token para bypassar bot detection do YouTube)
RUN pip install --no-cache-dir bgutil-ytdlp-pot-provider

# Copia o codigo da aplicacao
COPY main.py .
COPY static/ ./static/

# Expoe a porta
EXPOSE 8000

# Inicia o servidor bgutil em background e depois o uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
