# livestream-w2-gaules/Dockerfile

# --- Estágio 1: Construção do Frontend com Vite ---
FROM node:18 AS frontend
WORKDIR /app

COPY frontend/package.json ./
RUN npm cache clean --force && npm install --legacy-peer-deps --no-package-lock

COPY frontend/ ./
RUN npm run build

# --- Estágio 2: Imagem Final com Backend Python ---
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && \
    apt-get install -y ffmpeg git curl build-essential streamlink && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

COPY --from=frontend /app/dist ./frontend/dist

COPY start.sh ./
RUN chmod +x start.sh

ENV PORT=8000
EXPOSE 8000

CMD ["bash", "start.sh"]
