import os
import time
import subprocess
import whisper, requests
from dotenv import load_dotenv

load_dotenv()

DEEPL_KEY    = os.getenv("DEEPL_API_KEY")
ELEVEN_KEY   = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_VOICE = os.getenv("ELEVENLABS_VOICE_ID")

# Paths
CAP       = "capture"
RAW_HLS   = f"{CAP}/raw_hls"
AUDIO_DIR = f"{CAP}/audio_chunks"
DUB_HLS   = f"{CAP}/dub_hls"

os.makedirs(DUB_HLS, exist_ok=True)

# Model Whisper
model = whisper.load_model("base")

def translate_pt_to_en(text: str) -> str:
    r = requests.post(
        "https://api-free.deepl.com/v2/translate",
        data={"auth_key": DEEPL_KEY, "text": text, "target_lang": "EN"}
    )
    return r.json()["translations"][0]["text"]

def synthesize_elevenlabs(text: str, out_path: str):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE}"
    headers = {
        "xi-api-key": ELEVEN_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "voice_settings": {
            "stability": 0.7,
            "similarity_boost": 0.75
        }
    }
    # Streaming da resposta (bytes de áudio em PCM/WAV ou MP3, conforme sua config)
    resp = requests.post(url, json=payload, headers=headers, stream=True)
    resp.raise_for_status()
    # Grava em .mp3 ou .wav — aqui vamos supor MP3
    with open(out_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

def worker_loop():
    seen = set()
    while True:
        for fname in sorted(os.listdir(AUDIO_DIR)):
            if not fname.endswith(".wav") or fname in seen:
                continue
            seen.add(fname)
            wav_path = f"{AUDIO_DIR}/{fname}"
            # 1) transcrever PT
            res = model.transcribe(wav_path, language="pt")
            text_en = translate_pt_to_en(res["text"])
            # 2) sintetizar com ElevenLabs
            aac_path = wav_path.replace("audio_chunks", "dub_hls").replace(".wav", ".mp3")
            synthesize_elevenlabs(text_en, aac_path)
            # 3) remux vídeo TS + áudio MP3 → TS dublado
            seq    = fname.split("_")[-1].split(".")[0]
            raw_ts = f"{RAW_HLS}/segment{seq}.ts"
            dub_ts = f"{DUB_HLS}/segment{seq}.ts"
            subprocess.run([
                "ffmpeg", "-y",
                "-i", raw_ts,
                "-i", aac_path,
                "-c:v", "copy",
                "-c:a", "aac",
                dub_ts
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
