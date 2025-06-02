# Etapa 1: build do frontend
FROM node:18 AS frontend

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Etapa 2: imagem final com Python
FROM python:3.11-slim

WORKDIR /app

# 1) Instala pacotes de sistema
RUN apt-get update && \
    apt-get install -y ffmpeg git curl build-essential streamlink && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 2) Copia requirements e instala dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 3) Copia o backend, capture e pipeline
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# 4) Copia o build do frontend (após npm run build)
COPY --from=frontend /app/dist ./frontend/dist

# 5) Expor porta usada pelo Render
ENV PORT=8000
EXPOSE 8000

# 6) Comando padrão
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
