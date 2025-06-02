# --- Estágio 1: Build do Frontend com Vite ---
FROM node:18 AS frontend

WORKDIR /app

# 1) Copia apenas package.json e instala dependências (sem exigir package-lock.json)
COPY frontend/package.json ./
# Ajuste “npm install” para não falhar se não houver package-lock.json
RUN npm install --legacy-peer-deps --no-package-lock

# 2) Copia TODO o código do frontend e executa o build
COPY frontend/ ./
RUN npm run build

# --- Estágio 2: Imagem Final com Backend Python ---
FROM python:3.11-slim

WORKDIR /app

# Instala pacotes de SO (ffmpeg, git, curl, compiladores e streamlink)
RUN apt-get update && \
    apt-get install -y ffmpeg git curl build-essential streamlink && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia código do backend, capture e pipeline
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# Copia frontend compilado do estágio anterior
COPY --from=frontend /app/dist ./frontend/dist

# Copia script de inicialização e torna executável
COPY start.sh ./
RUN chmod +x start.sh

# Porta padrão que o uvicorn usará
ENV PORT=8000
EXPOSE 8000

CMD ["bash", "start.sh"]
