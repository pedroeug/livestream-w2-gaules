import threading
from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from capture.recorder import start_capture
from pipeline.worker import worker_loop
import download_models  # Baixa os modelos na inicialização, se ainda não existirem

app = FastAPI()

class StreamRequest(BaseModel):
    channel: str
    target_lang: str = "EN"   # padrão Inglês

@app.post("/api/start-dub")
def start_dub(req: StreamRequest, bg: BackgroundTasks):
    # garante que os modelos estão disponíveis
    download_models.main()

    # inicia captura de vídeo+áudio
    bg.add_task(start_capture, req.channel)

    # inicia o worker de tradução/dublagem com o idioma escolhido
    threading.Thread(
        target=worker_loop,
        args=(req.target_lang,),
        daemon=True
    ).start()

    return {
        "message": f"Dublagem iniciada para canal {req.channel} em {req.target_lang}"
    }

# serve os segmentos HLS dublados
app.mount("/dub_hls", StaticFiles(directory="capture/dub_hls"), name="dub_hls")

# serve o frontend React build
app.mount("/", StaticFiles(directory="frontend/build", html=True), name="frontend")
