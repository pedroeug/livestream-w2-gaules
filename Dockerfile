# --- Estágio 1: Construção do Frontend ---
FROM node:18 AS frontend

WORKDIR /app

# Copia apenas package.json (sem package-lock.json) e limpa o cache
COPY frontend/package.json ./
RUN npm cache clean --force

# Instala dependências sem usar package-lock.json (sem checagem de integridade fixa)
RUN npm install --legacy-peer-deps --no-package-lock

# Copia todo o código do frontend (inclui index.html) e executa o build
COPY frontend/ ./
RUN npm run build

# --- Estágio 2: Imagem Final com Backend ---
FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema operacional e FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg git curl build-essential && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do backend e pipeline
COPY backend/ ./backend/
COPY pipeline/ ./pipeline/

# Copia a pasta dist do frontend (gerada na etapa anterior)
COPY --from=frontend /app/dist ./frontend/dist

# Copia o script de inicialização
COPY start.sh ./
RUN chmod +x start.sh

# Define variável de ambiente e expõe porta
ENV PORT=$PORT
EXPOSE $PORT

# Comando padrão de inicialização
CMD ["bash", "start.sh"]
