# livestream-w2-gaules/Dockerfile

# --- Etapa 1: Build do frontend com Vite/React ---
FROM node:18 AS frontend

WORKDIR /app

# Copia apenas package.json e package-lock.json (se existir) e instala dependências
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --legacy-peer-deps --no-package-lock

# Copia todo o código do frontend e faz o build
COPY frontend/ ./
RUN npm run build

# --- Etapa 2: Imagem final com backend Python ---
FROM python:3.11-slim

WORKDIR /app

# Instala dependências de SO (FFmpeg, Git, Curl, compiladores e Streamlink)
RUN apt-get update && \
    apt-get install -y ffmpeg git curl build-essential streamlink && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do backend, capture e pipeline
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# Copia o frontend compilado do estágio anterior
COPY --from=frontend /app/dist ./frontend/dist

# Cria pastas iniciais (para StaticFiles não falhar)
RUN mkdir -p hls \
    && mkdir -p audio_segments

# Define variável de ambiente e expõe a porta
ENV PORT=8000
EXPOSE 8000

# Comando padrão ao iniciar o contêiner
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
