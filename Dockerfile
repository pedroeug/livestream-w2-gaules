# Etapa 1: Build do Frontend
FROM node:18 AS frontend
WORKDIR /app
COPY frontend/package.json ./
RUN npm install --legacy-peer-deps --no-package-lock
COPY frontend/ ./
RUN npm run build

# Etapa 2: Imagem final com backend Python
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

ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
