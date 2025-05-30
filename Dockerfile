# Stage 1: build do frontend
FROM node:18 AS frontend
WORKDIR /frontend

# 1) copia package.json e instala dependências
COPY frontend/package*.json ./
RUN npm install

# 2) coloca o index.html na raiz (necessário para Rollup/Vite)
COPY frontend/public/index.html ./

# 3) copia todo o resto do frontend
COPY frontend/ ./

# 4) build
RUN npm run build

# Stage 2: imagem final
FROM python:3.10-slim
WORKDIR /app

# instala dependências do sistema
RUN apt-get update && \
    apt-get install -y ffmpeg streamlink git libsndfile1 build-essential && \
    rm -rf /var/lib/apt/lists/*

# copia e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install python-dotenv tensorflow-cpu gdown

# clona Voice-Cloning
RUN git clone https://github.com/CorentinJ/Real-Time-Voice-Cloning.git /app/Real-Time-Voice-Cloning
ENV PYTHONPATH="/app/Real-Time-Voice-Cloning:${PYTHONPATH}"

# copia o código
COPY backend/    ./backend
COPY capture/    ./capture
COPY pipeline/   ./pipeline

# copia o frontend buildado
COPY --from=frontend /frontend/build ./frontend/build

# expõe a porta e define o start command
ENV PORT=8000
EXPOSE $PORT
CMD ["sh", "-c", "python -c 'import download_models; download_models.main()' && uvicorn backend.main:app --host 0.0.0.0 --port $PORT"]
