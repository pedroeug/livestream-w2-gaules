import threading
from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from capture.recorder import start_capture
from pipeline.worker import worker_loop
import download_models  # Baixa os modelos se ainda não existirem

# Importa rota adicional para integração com o frontend
from routes.dub_route import router as dub_router

app = FastAPI()

class StreamRequest(BaseModel):
    channel: str

# Rota API para uso direto (ex: via Postman, testes)
@app.post("/api/start-dub")
def start_dub(req: StreamRequest, bg: BackgroundTasks):
    bg.add_task(start_capture, req.channel)
    threading.Thread(target=worker_loop, daemon=True).start()
    return {"message": f"Dublagem com voz clone iniciada para {req.channel}"}

# Rota extra usada pelo frontend
app.include_router(dub_router)

# Monta os arquivos de saída da dublagem
app.mount("/dub_hls", StaticFiles(directory="capture/dub_hls"), name="dub_hls")

# Monta o frontend (React build)
app.mount("/", StaticFiles(directory="frontend/build", html=True), name="frontend")
