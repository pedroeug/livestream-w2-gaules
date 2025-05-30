# Etapa 1: construir o frontend
FROM node:18 AS frontend

# Define o diretório de trabalho
WORKDIR /frontend

# Copia os arquivos do frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .

# Constrói o frontend para produção
RUN npm run build

# Etapa 2: imagem final
FROM python:3.10-slim

# Instala dependências do sistema (ffmpeg, espeak-ng etc.)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    espeak-ng \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia os arquivos de backend
COPY backend/ /app/backend
COPY capture/ /app/capture
COPY pipeline/ /app/pipeline

# Copia os diretórios do Real-Time-Voice-Cloning
COPY Real-Time-Voice-Cloning/encoder/ /app/encoder
COPY Real-Time-Voice-Cloning/synthesizer/ /app/synthesizer
COPY Real-Time-Voice-Cloning/vocoder/ /app/vocoder

# Copia o frontend já construído
COPY --from=frontend /frontend/build /app/frontend/build

# Copia os arquivos de requirements e instala as dependências
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Instala gdown para baixar os modelos durante o startup
RUN pip install gdown

# Baixa os modelos ao iniciar
RUN python backend/utils/download_models.py

# Expõe a porta que será usada
ENV PORT=8000
EXPOSE $PORT

# Comando para iniciar o backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
