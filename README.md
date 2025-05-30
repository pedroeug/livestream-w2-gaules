# Livestream W2 – Twitch Dubbing HLS (Voice Clone Gaules)

**Descrição:**
Conecta no canal da Twitch do Gaules, grava vídeo+áudio, gera embedding de voz do Gaules, dublagem (Whisper→DeepL→Voice Clone), e serve um HLS dublado com ~30 s de buffer.

## 1. Pré-requisitos

- Docker
- Conta DeepL (chave)
- Modelos de Voice-Cloning (baixados automaticamente)

## 2. Configuração

1. Copie `.env.example` → `.env` e preencha as chaves.
2. Faça `docker build -t livestream-w2-gaules .`

## 3. Deploy (Docker)

```bash
docker run --env-file .env -p 8000:8000 livestream-w2-gaules
```

Acesse `http://localhost:8000`

## 4. Deploy (Render.com)

1. Push no GitHub.
2. Crie Web Service no Render apontando para o Dockerfile.
3. Defina variáveis de ambiente a partir de `.env`.
4. Deploy e abra `https://<seu-app>.onrender.com`.

## 5. Uso

- Na UI, digite **gaules** e clique **“Assistir com Dublagem”**.
- O sistema grava 60 s de amostra de voz, depois gera embedding e dublagem contínua com voz do Gaules.