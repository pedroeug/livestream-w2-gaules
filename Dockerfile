# --- Etapa 1: Build do Frontend via Vite ---
FROM node:18 AS frontend

WORKDIR /app

# Copia apenas package.json e package-lock.json (se existir) para instalar depêndencias
COPY frontend/package.json ./ 
# Não há package-lock.json, mas copiá-lo assim evita erro no build
# Se não existir, ignore com cuidado (nada adicional precisa ser feito)

RUN npm install --legacy-peer-deps --no-package-lock

# Copia todo o frontend e faz o build
COPY frontend/ ./
RUN npm run build


# --- Etapa 2: Imagem final com Backend Python ---
FROM python:3.11-slim

WORKDIR /app

# Instala libs de SO (FFmpeg, build-essential, streamlink, etc.)
RUN apt-get update && \
    apt-get install -y ffmpeg git curl build-essential streamlink && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia código (backend/pipeline/capture) e o build do frontend
COPY backend/ ./backend/
COPY capture/ ./capture/
COPY pipeline/ ./pipeline/

COPY --from=frontend /app/dist ./frontend/dist

# Define variáveis de ambiente e expõe a porta padrão
ENV PORT=8000
EXPOSE 8000

# Comando de inicialização
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
