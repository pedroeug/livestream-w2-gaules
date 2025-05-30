import os
import urllib.request

MODELS = {
    "Real-Time-Voice-Cloning/encoder/saved_models/pretrained.pt":
        "https://drive.google.com/uc?export=download&id=1f6YOa2Hrx5pKx68jDqzv3OrO18lJv7Yd",
    "Real-Time-Voice-Cloning/synthesizer/saved_models/pretrained/pretrained.pt":
        "https://drive.google.com/uc?export=download&id=1RPw5FvC6SOq2ogMZ1zknbaZt4A9y0bYy",
    "Real-Time-Voice-Cloning/vocoder/saved_models/pretrained.pt":
        "https://drive.google.com/uc?export=download&id=1uFPl3fF3HHgjg7I0kNv4a9U-kW5NBMZQ"
}

def download_file(target_path, url):
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    if not os.path.isfile(target_path):
        print(f"Downloading {target_path}...")
        urllib.request.urlretrieve(url, target_path)
        print(f"Downloaded {target_path}")
    else:
        print(f"{target_path} already exists, skipping.")

for path, url in MODELS.items():
    download_file(path, url)
