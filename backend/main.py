import threading
import os
from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from Real-Time-Voice-Cloning.capture.recorder import start_capture
from Real-Time-Voice-Cloning.pipeline.worker import worker_loop
import Real-Time-Voice-Cloning.download_models  # Garante os modelos

app = FastAPI()

class StreamRequest(BaseModel):
    channel: str

@app.post("/api/start-dub")
def start_dub(req: StreamRequest, bg: BackgroundTasks):
    bg.add_task(start_capture, req.channel)
    threading.Thread(target=worker_loop, daemon=True).start()
    return {"message": f"Dublagem com voz clone iniciada para {req.channel}"}

# Serve os arquivos da dublagem (HLS)
app.mount("/dub_hls", StaticFiles(directory="Real-Time-Voice-Cloning/capture/dub_hls"), name="dub_hls")

# Serve o frontend React build
app.mount("/", StaticFiles(directory="frontend/build", html=True), name="frontend")
