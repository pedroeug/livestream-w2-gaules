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

# instala dependências de sistema
RUN apt-get update && apt-get install -y ffmpeg streamlink git && rm -rf /var/lib/apt/lists/*

# instala python-dotenv
RUN pip install python-dotenv

# instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copia código
COPY backend/ ./backend
COPY capture/ ./capture
COPY pipeline/ ./pipeline
COPY --from=frontend-builder /app/frontend/build ./frontend/build

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]