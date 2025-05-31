# livestream-w2-gaules/Dockerfile

# --- Estágio 1: Construção do Frontend com Vite ---
FROM node:18 AS frontend

WORKDIR /app

# Copia apenas package.json (sem package-lock.json) e limpa cache
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

# Instala dependências de SO (FFmpeg, Git, Curl, compiladores básicos)
RUN apt-get update && \
    apt-get install -y ffmpeg git curl build-essential && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do backend, capture e pipeline
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# Copia o frontend compilado do estágio anterior (pasta /app/dist)
COPY --from=frontend /app/dist ./frontend/dist

# Copia o script de inicialização e garante permissão
COPY start.sh ./
RUN chmod +x start.sh

# Define variável de ambiente e expõe a porta
ENV PORT=$PORT
EXPOSE $PORT

# Comando padrão ao iniciar o contêiner
CMD ["bash", "start.sh"]
