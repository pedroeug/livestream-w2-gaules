import os
import gdown
from pathlib import Path

# Cria diretórios, se não existirem
Path("encoder/saved_models").mkdir(parents=True, exist_ok=True)
Path("vocoder/saved_models").mkdir(parents=True, exist_ok=True)
Path("synthesizer/saved_models/logs-pretrained/taco_pretrained").mkdir(parents=True, exist_ok=True)

def download_if_missing(target_path, gdrive_url):
    if not os.path.exists(target_path):
        print(f"Downloading {target_path}...")
        gdown.download(gdrive_url, target_path, quiet=False)
    else:
        print(f"Model {target_path} already exists.")

# 1. Encoder
download_if_missing(
    "encoder/saved_models/pretrained.pt",
    "https://drive.google.com/uc?id=1ExOFjsWzkEciECIRDKO5VNRoGW4978Hm"
)

# 2. Vocoder
download_if_missing(
    "vocoder/saved_models/pretrained.pt",
    "https://drive.google.com/uc?id=1Z1BO5j104CtHpwl3oVIvNRtbDqUXGdZ9"
)

# 3. Synthesizer (taco_pretrained)
# Baixa e extrai os três arquivos do modelo Tacotron
taco_files = {
    "checkpoint": "1l6pPeJNaF1Tt_s5xGyO3NQO-KXubnkfB",
    "tacotron_model.ckpt-278000.index": "1IwhpyIbKDTDBwD3E_TzZJXxU8Y_1V1Hz",
    "tacotron_model.ckpt-278000.meta": "1qg3MTZQrd7NLCYAEXV8n6YJErkGvmS9M",
    "tacotron_model.ckpt-278000.data-00000-of-00001": "1WQurqcwFgn8xspBpVjWfjFJbtmLqGySH"
}

for filename, file_id in taco_files.items():
    path = f"synthesizer/saved_models/logs-pretrained/taco_pretrained/{filename}"
    download_if_missing(path, f"https://drive.google.com/uc?id={file_id}")
