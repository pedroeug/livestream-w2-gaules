# --- Estágio 1: Build do frontend React com Vite ---
FROM node:18 AS frontend

WORKDIR /app

# 1) Copia só package.json (sem lockfile)
COPY frontend/package.json ./

# 2) Instala as dependências do frontend
RUN npm install --legacy-peer-deps --no-package-lock

# 3) Copia todo o código do frontend e gera build
COPY frontend/ ./
RUN npm run build

# --- Estágio 2: Imagem final com Backend Python ---
FROM python:3.11-slim

WORKDIR /app

# 1) Instala dependências de SO (FFmpeg, Git, Curl, compiladores, Streamlink)
RUN apt-get update && \
    apt-get install -y \
      ffmpeg \
      git \
      curl \
      build-essential \
      streamlink \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 2) Copia requirements e instala dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 3) Copia o código do backend, capture e pipeline
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# 4) Copia o build do frontend gerado no estágio anterior
COPY --from=frontend /app/dist ./frontend/dist

# 5) Copia script de inicialização e dá permissão
COPY start.sh ./
RUN chmod +x start.sh

# 6) Expõe a porta (por padrão: 8000)
ENV PORT=${PORT:-8000}
EXPOSE ${PORT}

# 7) Comando final: executa o start.sh
CMD ["bash", "start.sh"]
