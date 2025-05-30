# Dockerfile

# Stage 1: build do frontend
FROM node:16 AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .
RUN npm run build

# Stage 2: build da aplicação
FROM python:3.10-slim
WORKDIR /app

# Instala dependências de sistema (incluindo libsndfile para librosa)
RUN apt-get update && \
    apt-get install -y ffmpeg streamlink git libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

# Copia e instala as dependências Python do projeto
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala TensorFlow CPU (necessário para o Voice-Cloning)
RUN pip install --no-cache-dir tensorflow-cpu

# Clona o repositório de Voice-Cloning (somente código)
RUN git clone https://github.com/CorentinJ/Real-Time-Voice-Cloning.git /app/Real-Time-Voice-Cloning

# Ajusta PYTHONPATH para incluir o código do Voice-Cloning
ENV PYTHONPATH="/app/Real-Time-Voice-Cloning:${PYTHONPATH}"

# Copia aplicação e build do frontend
COPY backend/    ./backend
COPY capture/    ./capture
COPY pipeline/   ./pipeline
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Expõe a porta da aplicação
EXPOSE 8000

# Comando de inicialização
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
