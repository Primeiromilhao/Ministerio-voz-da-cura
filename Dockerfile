FROM python:3.10-slim

# Instala ffmpeg (necessario para processamento de audio/video)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o codigo da aplicacao
COPY main.py .
COPY static/ ./static/
COPY cookies.txt .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
