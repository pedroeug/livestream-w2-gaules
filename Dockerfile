# ──── etapa‐1: build do React com Vite ────
FROM node:18 AS frontend

WORKDIR /app

# 1) Copia apenas o package.json (não há package-lock.json)
COPY frontend/package.json ./

# 2) Instala as dependências sem gerar package-lock.json
RUN npm install --legacy-peer-deps --no-package-lock

# 3) Copia todo o código do frontend e roda o build
COPY frontend/ ./
RUN npm run build


# ──── etapa‐2: imagem final com Python (FastAPI + Whisper + Speechify) ────
FROM python:3.11-slim

WORKDIR /app

# 1) Instala pacotes de sistema (FFmpeg, git, curl, compiladores e streamlink)
RUN apt-get update && \
    apt-get install -y \
      ffmpeg \
      git \
      curl \
      build-essential \
      streamlink && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 2) Copia e instala dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 3) Garante que a pasta hls exista (para não quebrar o app.mount lá no FastAPI)
RUN mkdir -p hls

# 4) Copia todo o código do backend, do capture e do pipeline
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# 5) Copia o build estático do React gerado na etapa-1
COPY --from=frontend /app/dist ./frontend/dist

# 6) Expõe a porta padrão do uvicorn e define o CMD
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
