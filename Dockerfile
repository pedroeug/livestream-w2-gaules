# ----------- Stage 1: Build do Frontend -----------
FROM node:18-alpine AS frontend

# Diretório de trabalho para o build do frontend
WORKDIR /app/frontend

# Copia apenas o package.json (sem package-lock.json) e instala dependências
COPY frontend/package.json ./
RUN npm install --legacy-peer-deps --no-package-lock

# Copia todo o código do frontend e executa o build de produção
COPY frontend/ ./
RUN npm run build


# ----------- Stage 2: Backend + Assets Estáticos -----------
FROM python:3.11-slim

# Diretório de trabalho do backend
WORKDIR /app

# Instala dependências do sistema (ffmpeg, streamlink etc.)
RUN apt-get update && \
    apt-get install -y \
      ffmpeg \
      git \
      curl \
      build-essential \
      streamlink && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de requirements e instala as dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Cria as pastas vazias necessárias à execução
RUN mkdir -p audio_segments hls

# Copia o código-fonte do backend e pipeline
COPY backend/ ./backend
COPY pipeline/ ./pipeline
COPY capture/ ./capture

# Se você tiver um arquivo .env, descomente a linha abaixo:
# COPY .env ./

# Copia os arquivos estáticos gerados no frontend para dentro do contêiner
COPY --from=frontend /app/frontend/dist ./frontend/dist

# Expõe a porta usada pelo Uvicorn (opcional, pois o Render detecta automaticamente)
EXPOSE 8000

# Comando padrão para iniciar a aplicação
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
