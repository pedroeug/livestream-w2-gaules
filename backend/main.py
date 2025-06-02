import os
import multiprocessing
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.download_models import download_all_models
from capture.recorder import start_capture
from pipeline.worker import worker_loop

app = FastAPI()

# 1) Habilita CORS (caso queira chamar de outro domínio)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2) Baixa/verifica o modelo Whisper ao iniciar
download_all_models()

# 3) Garante as pastas base
os.makedirs("audio_segments", exist_ok=True)
os.makedirs("hls", exist_ok=True)

# 4) Define rota POST /start/{channel}/{lang}
@app.post("/start/{channel}/{lang}")
async def start_stream(channel: str, lang: str):
    """
    Ao chamar /start/{channel}/{lang}:
    - Cria pasta audio_segments/{channel}
    - Cria pasta hls/{channel}/{lang}
    - Lança start_capture e worker_loop em processos separados
    """
    audio_dir = os.path.join("audio_segments", channel)
    os.makedirs(audio_dir, exist_ok=True)

    hls_dir = os.path.join("hls", channel, lang)
    os.makedirs(hls_dir, exist_ok=True)

    # 5) Cria um HLS inicial de 1s de silêncio para não dar 404 imediato
    initial_index = os.path.join(hls_dir, "index.m3u8")
    if not os.path.exists(initial_index):
        os.system(
            f"ffmpeg -y -f lavfi -i anullsrc=r=16000:cl=mono -t 1 "
            f"-c:a aac -b:a 64k -hls_time 1 "
            f"-hls_playlist_type event "
            f"-hls_segment_filename {hls_dir}/%03d.ts "
            f"{initial_index}"
        )

    # 6) Lança captura e worker em processos independentes
    p1 = multiprocessing.Process(target=start_capture, args=(channel, audio_dir))
    p1.daemon = True
    p1.start()

    p2 = multiprocessing.Process(target=worker_loop, args=(channel, lang))
    p2.daemon = True
    p2.start()

    return {"status": "iniciado", "channel": channel, "lang": lang}


# 7) Monta diretório hls para servir .m3u8 e .ts
app.mount("/hls", StaticFiles(directory="hls"), name="hls")

# 8) Monta frontend estático em /
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
