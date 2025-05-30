import os
import urllib.request
from pathlib import Path

def download_file(url, destination):
    if not os.path.exists(destination):
        print(f"Baixando {destination}...")
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        urllib.request.urlretrieve(url, destination)
        print(f"{destination} baixado com sucesso.")
    else:
        print(f"{destination} já existe. Pulando o download.")

# URLs dos modelos pré-treinados
models = {
    "encoder/saved_models/pretrained.pt": "https://github.com/CorentinJ/Real-Time-Voice-Cloning/releases/download/pretrained/encoder.pt",
    "synthesizer/saved_models/pretrained/pretrained.pt": "https://github.com/CorentinJ/Real-Time-Voice-Cloning/releases/download/pretrained/synthesizer.pt",
    "vocoder/saved_models/pretrained/pretrained.pt": "https://github.com/CorentinJ/Real-Time-Voice-Cloning/releases/download/pretrained/vocoder.pt"
}

for path, url in models.items():
    download_file(url, path)
