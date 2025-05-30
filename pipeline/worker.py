import os
import time
import subprocess
import whisper
import requests
from dotenv import load_dotenv

load_dotenv()

DEEPL_KEY    = os.getenv("DEEPL_API_KEY")
ELEVEN_KEY   = os.getenv("ELEVENLABS_API_KEY")
ELEVEN_VOICE = os.getenv("ELEVENLABS_VOICE_ID")

CAP       = "capture"
RAW_HLS   = f"{CAP}/raw_hls"
AUDIO_DIR = f"{CAP}/audio_chunks"
DUB_HLS   = f"{CAP}/dub_hls"
os.makedirs(DUB_HLS, exist_ok=True)

# carrega modelo Whisper (ASR)
model = whisper.load_model("base")

def translate(text: str, target_lang: str) -> str:
    resp = requests.post(
        "https://api-free.deepl.com/v2/translate",
        data={
          "auth_key": DEEPL_KEY,
          "text": text,
          "target_lang": target_lang
        }
    )
    resp.raise_for_status()
    return resp.json()["translations"][0]["text"]

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
    resp = requests.post(url, headers=headers, json=payload, stream=True)
    resp.raise_for_status()
    # grava MP3 direto
    with open(out_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

def worker_loop(target_lang: str):
    seen = set()
    while True:
        for fname in sorted(os.listdir(AUDIO_DIR)):
            if not fname.endswith(".wav") or fname in seen:
                continue
            seen.add(fname)

            wav_path = os.path.join(AUDIO_DIR, fname)
            # 1) Transcrição
            res = model.transcribe(wav_path, language="pt")
            text_tgt = translate(res["text"], target_lang)

            # 2) Síntese TTS (ElevenLabs)
            aac_path = wav_path.replace("audio_chunks", "dub_hls").replace(".wav", ".mp3")
            synthesize_elevenlabs(text_tgt, aac_path)

            # 3) Remux vídeo + áudio dublado
            seq    = os.path.splitext(fname)[0].split("_")[-1]
            raw_ts = os.path.join(RAW_HLS,   f"segment{seq}.ts")
            dub_ts = os.path.join(DUB_HLS,   f"segment{seq}.ts")
            subprocess.run([
                "ffmpeg", "-y",
                "-i", raw_ts,
                "-i", aac_path,
                "-c:v", "copy",
                "-c:a", "aac",
                dub_ts
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        time.sleep(0.5)
