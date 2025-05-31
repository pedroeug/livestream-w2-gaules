# livestream-w2-gaules/Dockerfile

# --- Estágio 1: Construção do Frontend com Vite ---
FROM node:18 AS frontend

WORKDIR /app

# 1) Copia apenas package.json e limpa cache para garantir install limpo
COPY frontend/package.json ./
RUN npm cache clean --force

# 2) Instala dependências do frontend (sem criar package-lock.json)
RUN npm install --legacy-peer-deps --no-package-lock

# 3) Copia todo o código do frontend e executa o build
COPY frontend/ ./
RUN npm run build


# --- Estágio 2: Imagem Final com Backend Python ---
FROM python:3.11-slim

WORKDIR /app

# 4) Instala dependências de sistema: FFmpeg, Git, Curl, compiladores e Streamlink
RUN apt-get update && \
    apt-get install -y \
      ffmpeg \
      git \
      curl \
      build-essential \
      streamlink && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 5) Copia e instala dependências Python (requirements.txt está na raiz do repositório)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 6) Cria a pasta 'hls/' para o StaticFiles do FastAPI
RUN mkdir -p hls

# 7) Copia todo o código do backend, da pasta capture e da pasta pipeline
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# 8) Copia o build do frontend gerado no estágio anterior para ser servido como estático
COPY --from=frontend /app/dist ./frontend/dist

# 9) Copia o script de inicialização e dá permissão de execução
COPY start.sh ./
RUN chmod +x start.sh

# 10) Expõe a porta padrão (o Uvicorn usará 8000) e define variável de ambiente
ENV PORT=8000
EXPOSE 8000

# 11) Comando padrão ao iniciar o contêiner
CMD ["bash", "start.sh"]
