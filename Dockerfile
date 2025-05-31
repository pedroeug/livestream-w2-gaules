# livestream-w2-gaules/Dockerfile

# --- Estágio 1: Construção do Frontend com Vite ---
FROM node:18 AS frontend

WORKDIR /app

# Copia package.json e limpa cache
COPY frontend/package.json ./
RUN npm cache clean --force

# Instala dependências do frontend sem gerar package-lock.json
RUN npm install --legacy-peer-deps --no-package-lock

# Copia todo o código do frontend e executa o build
COPY frontend/ ./
RUN npm run build

# --- Estágio 2: Imagem Final com Backend Python ---
FROM python:3.11-slim

WORKDIR /app

# Instala dependências de SO: FFmpeg, Git, Curl, compiladores básicos, Streamlink e as libs de TTS
RUN apt-get update && \
    apt-get install -y \
      ffmpeg \
      git \
      curl \
      build-essential \
      streamlink \
      libsndfile1 \
      libportaudio2 \
      libcurl4-openssl-dev \
      libatlas-base-dev \
      libblas-dev \
      libasound2-dev \
      libjack-jackd2-0 \
      && apt-get clean \
      && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Cria diretórios básicos
RUN mkdir -p audio_segments hls

# Copia todo o código do backend, capture e pipeline
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# Copia a pasta de assets (sample de voz) para dentro do container
COPY assets/voices/ ./assets/voices/

# Copia o frontend compilado do estágio anterior
COPY --from=frontend /app/dist ./frontend/dist

# Copia o script de inicialização e garante permissão
COPY start.sh ./
RUN chmod +x start.sh

# Define variável de ambiente e expõe a porta (padrão: 8000)
ENV PORT=8000
EXPOSE 8000

# Comando padrão ao iniciar o contêiner
CMD ["bash", "start.sh"]
