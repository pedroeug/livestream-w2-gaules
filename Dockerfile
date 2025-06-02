# ############################################
# 1) Estágio “frontend”: build do React + Vite
# ############################################

FROM node:18 AS frontend

WORKDIR /app

# 1.1) Copia apenas package.json e package-lock.json (se existir) PARA instalar dependências
COPY frontend/package.json ./package.json
# Se você mantiver um package-lock.json, copie também:
# COPY frontend/package-lock.json ./package-lock.json

# 1.2) Instala dependências do frontend
RUN npm install --legacy-peer-deps --no-package-lock

# 1.3) Copia o restante do código do frontend (incluindo index.html, src/, etc.)
COPY frontend/ ./

# 1.4) Executa o build do Vite
RUN npm run build

# ############################################
# 2) Estágio “backend”: imagem final com Python + front compilado
# ############################################

FROM python:3.11-slim

WORKDIR /app

# 2.1) Instala dependências de SO para FFmpeg, build tools, streamlink etc.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ffmpeg \
      git \
      curl \
      build-essential \
      streamlink && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 2.2) Copia e instala dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 2.3) Copia todo o código do backend, capture e pipeline
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# 2.4) Copia o front compilado (saído em /app/dist) para dentro desta imagem
COPY --from=frontend /app/dist ./frontend/dist

# 2.5) Copia script de inicialização (start.sh) e dá permissão
COPY start.sh ./
RUN chmod +x start.sh

# 2.6) Expõe a porta
ENV PORT=$PORT
EXPOSE $PORT

# 2.7) Comando final
CMD ["bash", "start.sh"]
