import os
import gdown

def download_if_missing(target_path, gdrive_url):
    if not os.path.exists(target_path):
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        print(f"Downloading {target_path}...")
        gdown.download(gdrive_url, target_path, quiet=False)

# encoder
download_if_missing(
    "encoder/saved_models/pretrained.pt",
    "https://drive.google.com/uc?id=1ExOFjsWzkEciECIRDKO5VNRoGW4978Hm"
)

# vocoder
download_if_missing(
    "vocoder/saved_models/pretrained.pt",
    "https://drive.google.com/uc?id=1Z1BO5j104CtHpwl3oVIvNRtbDqUXGdZ9"
)

# synthesizer (taco_pretrained)
download_if_missing(
    "synthesizer/saved_models/logs-pretrained/taco_pretrained/checkpoint",
    "https://drive.google.com/uc?id=1rSnF6oR-2MON_6-6oi0zlWU2vwkb9TPg"
)

download_if_missing(
    "synthesizer/saved_models/logs-pretrained/taco_pretrained/tacotron_model.ckpt-278000.data-00000-of-00001",
    "https://drive.google.com/uc?id=1GLWwh4K-5D4Gmy6e0TqbYZ8UWYsCtqSv"
)

download_if_missing(
    "synthesizer/saved_models/logs-pretrained/taco_pretrained/tacotron_model.ckpt-278000.index",
    "https://drive.google.com/uc?id=1kWyLxdJS-gJ7SoaWEo7n9qx8G-WoU62E"
)

download_if_missing(
    "synthesizer/saved_models/logs-pretrained/taco_pretrained/tacotron_model.ckpt-278000.meta",
    "https://drive.google.com/uc?id=1bJ1WgBekNp_8sMzz6J7sp_eFXco_N-TE"
)
