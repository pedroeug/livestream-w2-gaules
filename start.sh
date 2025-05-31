# Conteúdo completo do start.sh
#!/usr/bin/env bash

# Faz o build do frontend (se necessário)
# (Se você já executou o build no Dockerfile, essa etapa pode ser omitida. 
# Caso queira rebuildar aqui, descomente as linhas abaixo:)
# cd frontend && npm install && npm run build && cd ..

# Inicia o backend com Uvicorn na porta definida
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
