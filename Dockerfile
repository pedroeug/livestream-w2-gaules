# --- Estágio 1: Build do Frontend com Vite ---
FROM node:18 AS frontend

WORKDIR /app

# 1) Copia package.json e package-lock.json (se existir) e instala
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --legacy-peer-deps --no-package-lock

# 2) Copia todo o código do frontend e faz build
COPY frontend/ ./
RUN npm run build

# --- Estágio 2: Imagem final com Backend Python ---
FROM python:3.11-slim

WORKDIR /app

# 3) Instala dependências de SO (FFmpeg, build-essential, streamlink etc.)
RUN apt-get update && \
    apt-get install -y ffmpeg git curl build-essential streamlink && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 4) Copia e instala requirements Python
COPY requirements.txt ./
# Caso speechify-sws não exista no PyPI, altere para instalar via Git:
# RUN pip install --no-cache-dir -r requirements.txt && \
#     pip install git+https://github.com/speechify/speechify-python-sdk.git
RUN pip install --no-cache-dir -r requirements.txt

# 5) Copia backend, capture e pipeline
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# 6) Copia o build estático do frontend do estágio anterior
COPY --from=frontend /app/dist ./frontend/dist

# 7) Cria as pastas base (audio_segments e hls)
RUN mkdir -p audio_segments && mkdir -p hls

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
