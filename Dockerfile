# --- Etapa 1: Building do Frontend com Vite ---
FROM node:18 AS frontend

WORKDIR /app

# Copia apenas o package.json (sem package-lock.json) e instala dependências
COPY frontend/package.json ./
RUN npm install --legacy-peer-deps --no-package-lock

# Copia todo o código do frontend e executa o build
COPY frontend/ ./
RUN npm run build


# --- Etapa 2: Imagem final com Backend Python ---
FROM python:3.11-slim

WORKDIR /app

# Instala dependências de SO: FFmpeg, git, curl, compiladores e streamlink
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
# Se speechify-sws não existir no PyPI, use a linha comentada abaixo para instalar via Git:
# RUN pip install --no-cache-dir -r requirements.txt && \
#     pip install git+https://github.com/speechify/speechify-python-sdk.git
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do backend, capture e pipeline
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# Copia o build estático do frontend produzido na etapa 1
COPY --from=frontend /app/dist ./frontend/dist

# Cria as pastas base necessárias (para evitar erro de “Directory 'hls' does not exist”)
RUN mkdir -p audio_segments && mkdir -p hls

# Exponha a porta que o FastAPI/uvicorn irá usar
EXPOSE 8000

# Comando padrão: inicia o Uvicorn apontando para backend.main:app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
