# Dockerfile

# 1) build do frontend
FROM node:16 AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# 2) build da aplicação
FROM python:3.10-slim
WORKDIR /app

# instala sistema / git / ffmpeg / streamlink
RUN apt-get update && \
    apt-get install -y ffmpeg streamlink git && \
    rm -rf /var/lib/apt/lists/*

# instala python-dotenv
RUN pip install python-dotenv

# copia e instala as dependências do seu projeto
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Voice-Cloning: clona o repositório e instala deps ---
RUN git clone https://github.com/CorentinJ/Real-Time-Voice-Cloning.git && \
    pip install --no-cache-dir -r Real-Time-Voice-Cloning/requirements.txt

# garante que o Python veja o código do Voice-Cloning
ENV PYTHONPATH="/app/Real-Time-Voice-Cloning:${PYTHONPATH}"

# copia código da aplicação e o build do frontend
COPY backend/    ./backend
COPY capture/    ./capture
COPY pipeline/   ./pipeline
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# expõe a porta da aplicação
EXPOSE 8000

# comando de startup
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
