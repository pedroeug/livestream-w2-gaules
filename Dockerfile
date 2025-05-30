# Etapa 1: Build do Frontend
FROM node:18 AS frontend

WORKDIR /frontend

COPY COPY frontend/package.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# Etapa 2: Backend com Python
FROM python:3.10-slim

WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    gcc \
    libsndfile1 \
    && apt-get clean

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código-fonte
COPY backend/ ./backend
COPY capture/ ./capture
COPY pipeline/ ./pipeline
COPY --from=frontend /frontend/build ./frontend/build

# Define variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
