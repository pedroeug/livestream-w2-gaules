#!/usr/bin/env bash
# livestream-w2-gaules/start.sh

if [ -z "$PORT" ]; then
  export PORT=8000
fi

exec uvicorn backend.main:app --host 0.0.0.0 --port $PORT
