# --- Estágio 1: Construção do Frontend com Vite ---
FROM node:18 AS frontend

# 1) Definimos a pasta de trabalho para o frontend
WORKDIR /app

# 2) Copiamos apenas package.json (sem package-lock.json)
#    E limpamos o cache do npm para evitar checagem de lockfile corrompido
COPY frontend/package.json ./
RUN npm cache clean --force

# 3) Instalamos as dependências do frontend sem gerar package-lock.json
#    (skip do lockfile evita falha de checksum corrompido)
RUN npm install --legacy-peer-deps --no-package-lock

# 4) Copiamos tudo de frontend/ para /app (inclui index.html, src/, vite.config.js, etc.)
COPY frontend/ ./

# 5) Executamos o build do Vite (gera /app/dist/)
RUN npm run build

# --- Estágio 2: Imagem Final com Back-end Python ---
FROM python:3.11-slim

# 1) Definimos a pasta de trabalho para o backend
WORKDIR /app

# 2) Instalamos pacotes de SO necessários (FFmpeg, Git, etc.)
RUN apt-get update && \
    apt-get install -y \
      ffmpeg \
      git \
      curl \
      build-essential && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 3) Copiamos e instalamos as dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 4) Copiamos todo o código do backend e pipeline
COPY backend/ ./backend/
COPY pipeline/ ./pipeline/

# 5) Copiamos o frontend compilado (conteúdo de /app/dist do estágio anterior)
COPY --from=frontend /app/dist ./frontend/dist

# 6) Copiamos o script de inicialização e garantimos permissão de execução
COPY start.sh ./
RUN chmod +x start.sh

# 7) Definimos variável de ambiente e expomos porta
ENV PORT=$PORT
EXPOSE $PORT

# 8) Comando padrão ao iniciar o contêiner
CMD ["bash", "start.sh"]
