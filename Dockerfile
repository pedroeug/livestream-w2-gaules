# livestream-w2-gaules/Dockerfile

# --- Estágio 1: Build do Frontend (Vite) ---
FROM node:18 AS frontend

WORKDIR /app

# Copia apenas package.json (sem package-lock.json) e instala dependências
COPY frontend/package.json ./
RUN npm cache clean --force
RUN npm install --legacy-peer-deps --no-package-lock

# Copia todo o código do frontend e faz o build
COPY frontend/ ./
RUN npm run build

# --- Estágio 2: Imagem Final com Backend Python ---
FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema: FFmpeg, Git, Curl, build-essential e Streamlink
RUN apt-get update && \
    apt-get install -y \
      ffmpeg \
      git \
      curl \
      build-essential \
      streamlink && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia o backend / capture / pipeline
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# Copia o build estático do frontend (gerado no estágio 'frontend')
COPY --from=frontend /app/dist ./frontend/dist

# Copia o script de inicialização e dá permissão de execução
COPY start.sh ./
RUN chmod +x start.sh

# Expõe a porta que o Render atribuirá (sempre use VAR $PORT)
ENV PORT=$PORT
EXPOSE ${PORT:-8000}

# Comando padrão ao iniciar o container
CMD ["bash", "start.sh"]
