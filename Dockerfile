FROM python:3.9-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Instalar streamlink
RUN pip install --no-cache-dir streamlink

# Copiar arquivos do projeto
COPY backend/ /app/backend/
COPY capture/ /app/capture/
COPY pipeline/ /app/pipeline/
COPY frontend/ /app/frontend/
COPY requirements.txt /app/

# Criar diretórios necessários
RUN mkdir -p /app/hls/gaules/en
RUN mkdir -p /app/audio_segments/gaules

# Construir o frontend
WORKDIR /app/frontend
RUN npm install && npm run build

# Voltar para o diretório principal
WORKDIR /app

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Expor porta
EXPOSE 8000

# Comando para iniciar a aplicação
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
