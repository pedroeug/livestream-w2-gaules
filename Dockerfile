# livestre­am-w2-gaules/Dockerfile

# --- Estágio 1: Construção do Frontend com Vite ---
FROM node:18 AS frontend

WORKDIR /app

# Copia apenas o package.json e instala dependências (não copiamos package-lock.json porque não existe)
COPY frontend/package.json ./
RUN npm install --legacy-peer-deps --no-package-lock

# Copia todo o código-fonte do frontend e gera o build
COPY frontend/ ./
RUN npm run build

# --- Estágio 2: Imagem Final com Backend Python ---
FROM python:3.11-slim

WORKDIR /app

# Instala dependências de SO: FFmpeg, Git, Curl, compiladores básicos e Streamlink
RUN apt-get update && \
    apt-get install -y ffmpeg git curl build-essential streamlink && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código-fonte do backend, capture e pipeline
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# Copia o build do frontend gerado no estágio anterior
COPY --from=frontend /app/dist ./frontend/dist

# Garante que a pasta "hls" exista para a montagem do StaticFiles
RUN mkdir -p /app/hls

# Copia o script de inicialização e garante permissão
COPY start.sh ./
RUN chmod +x start.sh

# Expõe a porta que o Render definirá (geralmente $PORT)
ENV PORT=$PORT
EXPOSE $PORT

# Comando padrão ao iniciar o contêiner
CMD ["bash", "start.sh"]
