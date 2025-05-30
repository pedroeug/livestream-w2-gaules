# Etapa 1: Build do frontend
FROM node:18 AS frontend-builder

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# Etapa 2: Build final com backend
FROM python:3.10-slim

WORKDIR /app

# Instala dependências de sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    gcc \
    libsndfile1 \
    curl \
    && apt-get clean

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código-fonte do projeto
COPY backend/    ./backend
COPY capture/    ./capture
COPY pipeline/   ./pipeline

# Copia frontend buildado
COPY --from=frontend-builder /frontend/build ./frontend/build

# Define variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expõe a porta para o Render detectar
EXPOSE $PORT

# Comando para iniciar o backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
