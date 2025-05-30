# Dockerfile

# Stage 1: build do frontend
FROM node:16 AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .
RUN npm run build

# Stage 2: build da aplicação
FROM python:3.10-slim
WORKDIR /app

# Instala dependências de SO
RUN apt-get update && \
    apt-get install -y ffmpeg streamlink git && \
    rm -rf /var/lib/apt/lists/*

# Instala python-dotenv e scikit-learn
RUN pip install --no-cache-dir python-dotenv scikit-learn

# Copia e instala dependências do projeto
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala TensorFlow CPU (necessário para o Voice-Cloning)
RUN pip install --no-cache-dir tensorflow-cpu

# Clona o repositório de Voice-Cloning (sem instalar via pip)
RUN git clone https://github.com/CorentinJ/Real-Time-Voice-Cloning.git /app/Real-Time-Voice-Cloning

# Ajusta PYTHONPATH para incluir o código do Voice-Cloning
ENV PYTHONPATH="/app/Real-Time-Voice-Cloning:${PYTHONPATH}"

# Copia código da aplicação e build do frontend
COPY backend/    ./backend
COPY capture/    ./capture
COPY pipeline/   ./pipeline
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Exponha a porta do serviço
EXPOSE 8000

# Comando de startup
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
