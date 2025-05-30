# Usar imagem base com Python
FROM python:3.10-slim

# Variável de ambiente para a porta usada pela Render
ENV PORT=10000

# Instalar dependências de sistema necessárias
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    espeak-ng \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório da aplicação
WORKDIR /app

# Copiar arquivos
COPY . /app

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Expor a porta para Render detectar
EXPOSE $PORT

# Comando para iniciar o servidor
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "10000"]
