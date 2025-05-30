import threading
from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from capture.recorder import start_capture
from pipeline.worker import worker_loop
import download_models  # Baixa os modelos na inicialização

app = FastAPI()

class StreamRequest(BaseModel):
    channel: str

@app.post("/api/start-dub")
def start_dub(req: StreamRequest, bg: BackgroundTasks):
    bg.add_task(start_capture, req.channel)
    threading.Thread(target=worker_loop, daemon=True).start()
    return {"message": f"Dublagem com voz clone iniciada para {req.channel}"}

# Serve os arquivos da dublagem (segmentos HLS)
app.mount("/dub_hls", StaticFiles(directory="capture/dub_hls"), name="dub_hls")

# Serve o frontend React build (colocado via Dockerfile em frontend/build)
app.mount("/", StaticFiles(directory="frontend/build", html=True), name="frontend")
