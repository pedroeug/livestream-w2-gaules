# livestream-w2-gaules/Dockerfile

# --- Estágio 1: Build do Frontend com Vite ---
FROM node:18 AS frontend

WORKDIR /app

# 1) Copia package.json do frontend (remoção de comentários foi feita manualmente no package.json)
COPY frontend/package.json ./  
# (Não temos package-lock.json; o npm instalará com base em package.json)
RUN npm install --legacy-peer-deps --no-package-lock

# 2) Copia todo o código do frontend e faz o build
COPY frontend/ ./
RUN npm run build


# --- Estágio 2: Imagem final com Backend Python ---
FROM python:3.11-slim

WORKDIR /app

# 1) Instala dependências de SO: FFmpeg, Git, Curl, compiladores e Streamlink
RUN apt-get update && \
    apt-get install -y ffmpeg git curl build-essential streamlink && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 2) Copia e instala dependências Python (incluindo speechify-api)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 3) Cria a pasta hls de antemão (evita erro no mount)
RUN mkdir -p /app/hls

# 4) Copia o código do backend, capture e pipeline
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# 5) Copia o build do frontend gerado no estágio anterior
COPY --from=frontend /app/dist ./frontend/dist

# 6) Copia o script de inicialização e dá permissão de execução
COPY start.sh ./
RUN chmod +x start.sh

# 7) Expõe porta (o Render definirá ENV PORT)
ENV PORT=$PORT
EXPOSE $PORT

# 8) Comando padrão
CMD ["bash", "start.sh"]
