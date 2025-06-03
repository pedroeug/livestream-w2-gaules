# --- Estágio 1: Build do Frontend com Vite ---
FROM node:18 AS frontend

WORKDIR /app

# 1) Copia só o package.json (não há package-lock.json)
COPY frontend/package.json ./

# 2) Instala dependências do frontend
RUN npm install --legacy-peer-deps --no-package-lock

# 3) Copia o restante do frontend e executa o build
COPY frontend/ ./
RUN npm run build


# --- Estágio 2: Backend em Python ---
FROM python:3.11-slim

WORKDIR /app

# 4) Dependências de SO
RUN apt-get update && \
    apt-get install -y ffmpeg git curl build-essential streamlink && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 5) Copia e instala dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 6) Cria pasta hls antecipadamente
RUN mkdir -p /app/hls

# 7) Copia o código Python
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# 8) Copia o frontend compilado do “estágio frontend”
COPY --from=frontend /app/dist ./frontend/dist

# 9) Copia o script de startup
COPY start.sh ./
RUN chmod +x start.sh

EXPOSE 8000
ENV PORT 8000

CMD ["bash", "start.sh"]
