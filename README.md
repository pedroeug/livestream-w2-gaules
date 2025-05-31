# Livestream W2 Gaules - Instruções de Deploy

Este documento contém instruções detalhadas para implantar o projeto "livestream-w2-gaules" em um servidor de produção. O projeto permite a dublagem automática de streams da Twitch em tempo real, utilizando Whisper para transcrição, DeepL para tradução e ElevenLabs para síntese de voz.

## Requisitos de Sistema

- Ubuntu 20.04 LTS ou superior
- Python 3.8 ou superior
- Node.js 14 ou superior
- FFmpeg
- Streamlink
- 4GB RAM mínimo (recomendado 8GB)
- 2 vCPUs mínimo (recomendado 4 vCPUs)
- 20GB de espaço em disco

## Dependências

### Pacotes do Sistema
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv ffmpeg
pip install streamlink
```

### Dependências Python
```bash
pip install -r requirements.txt
```

### Dependências Frontend
```bash
cd frontend
npm install
npm run build
```

## Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```
PORT=8000
ELEVENLABS_API_KEY=sua_chave_elevenlabs
ELEVENLABS_VOICE_ID=id_da_voz_elevenlabs
DEEPL_API_KEY=sua_chave_deepl
```

## Estrutura de Diretórios

Certifique-se de que os seguintes diretórios existam:
```bash
mkdir -p hls/gaules/en
mkdir -p audio_segments/gaules
```

## Execução

### Método 1: Execução Direta

```bash
source .env
python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

### Método 2: Usando Systemd (Recomendado para Produção)

Crie um arquivo de serviço systemd:

```bash
sudo nano /etc/systemd/system/livestream-w2.service
```

Adicione o seguinte conteúdo:

```
[Unit]
Description=Livestream W2 Gaules
After=network.target

[Service]
User=seu_usuario
WorkingDirectory=/caminho/para/livestream-w2-gaules
Environment="PORT=8000"
Environment="ELEVENLABS_API_KEY=sua_chave_elevenlabs"
Environment="ELEVENLABS_VOICE_ID=id_da_voz_elevenlabs"
Environment="DEEPL_API_KEY=sua_chave_deepl"
ExecStart=/usr/bin/python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Ative e inicie o serviço:

```bash
sudo systemctl enable livestream-w2
sudo systemctl start livestream-w2
```

### Método 3: Usando Docker (Alternativa)

Se preferir usar Docker, um Dockerfile está disponível na pasta `deploy_package`. Para construir e executar:

```bash
docker build -t livestream-w2 .
docker run -p 8000:8000 \
  -e ELEVENLABS_API_KEY=sua_chave_elevenlabs \
  -e ELEVENLABS_VOICE_ID=id_da_voz_elevenlabs \
  -e DEEPL_API_KEY=sua_chave_deepl \
  livestream-w2
```

## Opções de Hospedagem Recomendadas

1. **VPS (Servidor Virtual Privado)**:
   - DigitalOcean: Droplet com 8GB RAM, 4 vCPUs
   - Linode: Plano de 8GB
   - Vultr: High Performance com 8GB

2. **Serviços Cloud**:
   - AWS EC2: t3.large ou superior
   - Google Cloud: e2-standard-4
   - Azure: Standard_D2s_v3

3. **Serviços PaaS**:
   - Heroku: Performance-M
   - Railway.app
   - Render.com

## Configuração de Proxy Reverso (Nginx)

Para expor o serviço com HTTPS, configure um proxy reverso com Nginx:

```
server {
    listen 80;
    server_name seu_dominio.com;
    
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name seu_dominio.com;
    
    ssl_certificate /etc/letsencrypt/live/seu_dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seu_dominio.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /hls/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # Configurações específicas para streaming HLS
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```

## Solução de Problemas

### Problema: Transcrição não reconhece fala em português
**Solução**: Verifique se o parâmetro `language="pt"` está definido na chamada do Whisper no arquivo `pipeline/worker.py`.

### Problema: Erro na API do DeepL
**Solução**: Verifique se a chave API do DeepL está correta e se tem saldo suficiente.

### Problema: Erro na captura do stream da Twitch
**Solução**: Verifique se o streamlink está instalado e se o canal está online. Teste manualmente com `streamlink twitch.tv/gaules best --stream-url`.

### Problema: Arquivos HLS não são gerados
**Solução**: Verifique se os diretórios `hls/gaules/en` existem e têm permissões de escrita.

## Monitoramento

Para monitorar o serviço em produção, recomendamos:

1. **Logs**: `sudo journalctl -u livestream-w2 -f`
2. **Status**: `sudo systemctl status livestream-w2`
3. **Uso de recursos**: `htop` ou `top`

## Backup e Manutenção

Recomendamos fazer backup regular dos seguintes diretórios:
- `hls/`
- `audio_segments/`
- Arquivo `.env` com suas credenciais

## Suporte

Para suporte adicional, consulte a documentação original do projeto ou entre em contato com o desenvolvedor.
