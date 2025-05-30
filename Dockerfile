# Dockerfile
FROM node:18 AS frontend

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build


FROM python:3.10-slim

ENV PORT=10000

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    espeak-ng \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia o backend
COPY backend/ /app/backend
COPY capture/ /app/capture
COPY encoder/ /app/encoder
COPY synthesizer/ /app/synthesizer
COPY vocoder/ /app/vocoder
COPY pipeline/ /app/pipeline
COPY requirements.txt /app/
COPY download_models.py /app/
COPY start.sh /app/

# Copia o frontend build do estágio anterior
COPY --from=frontend /frontend/build /app/frontend/build

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE $PORT

CMD ["bash", "start.sh"]
