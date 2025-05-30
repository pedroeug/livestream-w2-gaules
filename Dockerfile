# Etapa 1: build do frontend
FROM node:18 AS frontend

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

COPY frontend/ .
RUN npm run build

# Etapa 2: build da imagem final com backend
FROM python:3.10-slim

ENV PORT=$PORT

WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    gcc \
    libsndfile1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia os diretórios da aplicação
COPY backend/ ./backend
COPY capture/ ./capture
COPY pipeline/ ./pipeline

# Copia o frontend buildado
COPY --from=frontend /frontend/build ./frontend/build

# Expõe a porta esperada pelo Render
EXPOSE $PORT

# Comando para iniciar a aplicação
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
