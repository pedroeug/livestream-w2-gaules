# --- Estágio 1: Build do Frontend com Vite ---
FROM node:18 AS frontend

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# --- Estágio 2: Imagem Final com Python Backend ---
FROM python:3.11-slim

WORKDIR /app

# Instala pacotes de SO (ffmpeg, git, curl, compiladores, streamlink)
RUN apt-get update && \
    apt-get install -y ffmpeg git curl build-essential streamlink && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia código backend, capture e pipeline
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# Copia frontend compilado
COPY --from=frontend /app/dist ./frontend/dist

# Start script
COPY start.sh ./
RUN chmod +x start.sh

ENV PORT=8000
EXPOSE 8000

CMD ["bash", "start.sh"]
