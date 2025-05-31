# --- Estágio 1: Construção do Frontend com Vite ---
FROM node:18 AS frontend

WORKDIR /app

# 1) Copia apenas package.json (sem package-lock.json)
#    e limpa o cache do npm para evitar checksums corrompidos
COPY frontend/package.json ./
RUN npm cache clean --force

# 2) Instala dependências do frontend sem gerar package-lock.json
#    (skip do lockfile evita falhas EINTEGRITY)
RUN npm install --legacy-peer-deps --no-package-lock

# 3) Copia TODO o código do frontend (inclui index.html, src/, vite.config.js, etc.)
COPY frontend/ ./

# 4) Executa o build do Vite (gera /app/dist/)
RUN npm run build

# --- Estágio 2: Imagem Final com Backend Python ---
FROM python:3.11-slim

WORKDIR /app

# 1) Instala dependências de SO (FFmpeg, Git, Curl, compiladores básicos)
RUN apt-get update && \
    apt-get install -y \
      ffmpeg \
      git \
      curl \
      build-essential && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 2) Copia e instala as dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 3) Copia todo o código do backend e pipeline
COPY backend/ ./backend/
COPY pipeline/ ./pipeline/

# 4) Copia o frontend compilado do estágio anterior (pasta /app/dist)
COPY --from=frontend /app/dist ./frontend/dist

# 5) Copia o script de inicialização e garante permissão
COPY start.sh ./
RUN chmod +x start.sh

# 6) Define variável de ambiente e expõe a porta
ENV PORT=$PORT
EXPOSE $PORT

# 7) Comando padrão ao iniciar o contêiner
CMD ["bash", "start.sh"]
