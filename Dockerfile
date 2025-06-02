# ─── ETAPA 1: BUILD DO FRONTEND ───
FROM node:18 AS frontend

WORKDIR /app

# Copia apenas o package.json do frontend (removemos a menção a package-lock.json, 
# já que ele não existe atualmente no repositório)
COPY frontend/package.json ./

# Instala dependências do frontend 
# (npm install é usado em vez de npm ci, pois não temos package-lock.json)
RUN npm install --legacy-peer-deps --no-package-lock

# Copia o restante do código do frontend
COPY frontend/ ./

# Gera o build estático
RUN npm run build


# ─── ETAPA 2: IMAGEM FINAL (BACKEND EM PYTHON) ───
FROM python:3.11-slim

WORKDIR /app

# 1) Instala pacotes do SO necessários (FFmpeg, streamlink etc.)
RUN apt-get update && \
    apt-get install -y \
      ffmpeg \
      git \
      curl \
      build-essential \
      streamlink \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 2) Copia e instala dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 3) Copia todo o código de backend, capture e pipeline
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

# 4) Copia o build estático do frontend (do estágio “frontend”)
COPY --from=frontend /app/dist ./frontend/dist

# 5) Exporta a porta que o Render vai usar
ENV PORT=8000
EXPOSE 8000

# 6) Comando padrão para rodar o FastAPI (backend/main.py)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
