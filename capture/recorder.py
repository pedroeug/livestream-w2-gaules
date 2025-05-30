import os, subprocess
from dotenv import load_dotenv
import numpy as np
from encoder import inference as encoder

load_dotenv()
SAMPLE_DURATION = int(os.getenv("SAMPLE_DURATION", 60))
out = "capture"
os.makedirs(f"{out}/raw_hls", exist_ok=True)
os.makedirs(f"{out}/audio_chunks", exist_ok=True)

def start_capture(channel: str):
    # grava amostra de voz do Gaules
    sample_wav = f"{out}/speaker_sample.wav"
    cmd_sample = (
        f"streamlink twitch.tv/{channel} best -O | "
        f"ffmpeg -i pipe:0 -map 0:a -ac 1 -ar 16000 -t {SAMPLE_DURATION} {sample_wav}"
    )
    subprocess.run(cmd_sample, shell=True)

    # gera embedding
    encoder.load_model("encoder/saved_models/pretrained.pt")
    wav, sr = encoder.preprocess_wav(sample_wav)
    embed = encoder.embed_utterance(wav)
    np.save(f"{out}/speaker_embedding.npy", embed)

    # inicia gravação HLS + chunks áudio
    cmd = (
        f"streamlink twitch.tv/{channel} best -O | "
        "ffmpeg -i pipe:0 "
        "-c:v copy -c:a copy "
        "-f hls "
        "-hls_time 5 -hls_list_size 6 -hls_flags delete_segments "
        f"{out}/raw_hls/index.m3u8 "
        "-map 0:a -ac 1 -ar 16000 "
        "-f segment -segment_time 5 "
        f"{out}/audio_chunks/chunk_%05d.wav"
    )
    subprocess.Popen(cmd, shell=True)