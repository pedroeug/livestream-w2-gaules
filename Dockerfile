# livestream-w2-gaules/Dockerfile

# --- Estágio 1: Build do Frontend (Vite) ---
FROM node:18 AS frontend

WORKDIR /app

# Copia package.json e limpa cache
COPY frontend/package.json ./
RUN npm cache clean --force

# Instala dependências sem gerar package-lock.json
RUN npm install --legacy-peer-deps --no-package-lock

# Copia todo o código do frontend e executa build
COPY frontend/ ./
RUN npm run build

# --- Estágio 2: Imagem Final com Backend Python ---
FROM python:3.11-slim

WORKDIR /app

# Instala dependências do SO: ffmpeg, streamlink, build-essential, etc.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ffmpeg \
      git \
      curl \
      build-essential \
      streamlink \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do backend, capture e pipeline
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# Copia o frontend compilado do estágio 1
COPY --from=frontend /app/dist ./frontend/dist

# Cria as pastas necessárias a frio para evitar erros de montagem
RUN mkdir -p hls \
    && mkdir -p audio_segments

# Define variável de ambiente e expõe a porta
ENV PORT=8000
EXPOSE 8000

# Copia um script de inicialização (por exemplo, start.sh) se você tiver um
# Se não tiver, podemos inicializar o uvicorn diretamente
# COPY start.sh ./
# RUN chmod +x start.sh

# Comando padrão para iniciar o uvicorn
# Ajuste "backend.main:app" conforme o path do seu main.py
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
