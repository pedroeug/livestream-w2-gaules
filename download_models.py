import os
import gdown

MODELS = {
    "Real-Time-Voice-Cloning/encoder/saved_models/pretrained.pt":
        "1f6YOa2Hrx5pKx68jDqzv3OrO18lJv7Yd",
    "Real-Time-Voice-Cloning/synthesizer/saved_models/pretrained/pretrained.pt":
        "1RPw5FvC6SOq2ogMZ1zknbaZt4A9y0bYy",
    "Real-Time-Voice-Cloning/vocoder/saved_models/pretrained.pt":
        "1uFPl3fF3HHgjg7I0kNv4a9U-kW5NBMZQ"
}

def download_file(target_path, file_id):
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    if not os.path.isfile(target_path):
        print(f"Downloading {target_path}...")
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, target_path, quiet=False)
        print(f"Downloaded {target_path}")
    else:
        print(f"{target_path} already exists, skipping.")

for path, file_id in MODELS.items():
    download_file(path, file_id)
