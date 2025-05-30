import os, time, subprocess
import whisper, requests, boto3, numpy as np
from dotenv import load_dotenv
from synthesizer.inference import Synthesizer
from vocoder import inference as vocoder

load_dotenv()
DEEPL_KEY = os.getenv("DEEPL_API_KEY")
VOICE_EMBED = np.load("capture/speaker_embedding.npy")

# inicializa modelos
model = whisper.load_model("base")
synthesizer = Synthesizer("synthesizer/saved_models/pretrained.pt")
vocoder.load_model("vocoder/saved_models/pretrained.pt")
polly = boto3.client("polly",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION"),
)

CAP = "capture"
RAW_HLS   = f"{CAP}/raw_hls"
AUDIO_DIR = f"{CAP}/audio_chunks"
DUB_HLS   = f"{CAP}/dub_hls"
os.makedirs(DUB_HLS, exist_ok=True)

def translate_pt_to_en(text: str) -> str:
    r = requests.post(
        "https://api-free.deepl.com/v2/translate",
        data={"auth_key": DEEPL_KEY, "text": text, "target_lang": "EN"}
    )
    return r.json()["translations"][0]["text"]

def synthesize_clone(text: str, out_path: str):
    specs = synthesizer.synthesize_spectrograms([text], [VOICE_EMBED])
    wav_audio = vocoder.infer_waveform(specs[0])
    temp_wav = out_path.replace(".aac", ".wav")
    synthesizer.save_wav(wav_audio, temp_wav)
    subprocess.run([
        "ffmpeg", "-y", "-i", temp_wav,
        "-c:a aac", out_path
    ], shell=True)

def worker_loop():
    seen = set()
    while True:
        for fname in sorted(os.listdir(AUDIO_DIR)):
            if not fname.endswith(".wav") or fname in seen:
                continue
            seen.add(fname)
            wav = f"{AUDIO_DIR}/{fname}"
            # transcrição
            res = model.transcribe(wav, language="pt")
            text_en = translate_pt_to_en(res["text"])
            # síntese clonada
            aac_path = wav.replace("audio_chunks", "dub_hls").replace(".wav", ".aac")
            synthesize_clone(text_en, aac_path)
            # remux TS
            seq = fname.split("_")[-1].split(".")[0]
            raw_ts = f"{RAW_HLS}/segment{seq}.ts"
            dub_ts = f"{DUB_HLS}/segment{seq}.ts"
            subprocess.run([
                "ffmpeg", "-y",
                "-i", raw_ts,
                "-i", aac_path,
                "-c:v copy -c:a aac",
                dub_ts
            ], shell=True)
        time.sleep(1)