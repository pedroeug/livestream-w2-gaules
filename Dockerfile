# Etapa 1: constrói o frontend
FROM node:18 AS frontend

WORKDIR /frontend

# Copia apenas o package.json para instalar dependências
COPY frontend/package.json ./
RUN npm install

# Copia o restante do frontend e constrói
COPY frontend/ .
RUN npm run build

# Etapa 2: imagem final com backend
FROM python:3.10-slim

WORKDIR /app

# Instala dependências do sistema (ex: ffmpeg, git, build tools)
RUN apt-get update && \
    apt-get install -y ffmpeg git curl build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python do projeto
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do backend
COPY backend/    ./backend
COPY capture/    ./capture
COPY pipeline/   ./pipeline

# Copia o frontend já buildado
COPY --from=frontend /frontend/build ./frontend/build

# Expõe a porta correta (Render usa a variável $PORT)
ENV PORT=10000
EXPOSE $PORT

# Comando para rodar o backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "10000"]
