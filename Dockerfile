# Etapa 1: build do React
FROM node:18 AS frontend

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --legacy-peer-deps --no-package-lock

COPY frontend/ ./
RUN npm run build

# Etapa final: backend Python
FROM python:3.11-slim

WORKDIR /app

# Instala pacotes de SO 
RUN apt-get update && \
    apt-get install -y ffmpeg git curl build-essential streamlink && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia requirements e instala
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Garante diretório hls
RUN mkdir -p hls

# Copia todo o código Python
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# Copia build estático do React
COPY --from=frontend /app/dist ./frontend/dist

# Expõe variável de porta e arranca
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
