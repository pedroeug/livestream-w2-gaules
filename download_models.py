import os
import gdown

def ensure_dir_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)

def download_file(url_id, output_path):
    ensure_dir_exists(os.path.dirname(output_path))
    if not os.path.isfile(output_path):
        print(f"Downloading {output_path}...")
        gdown.download(f"https://drive.google.com/uc?id={url_id}", output_path, quiet=False)
    else:
        print(f"{output_path} already exists, skipping download.")

# Encoder
download_file("1ExOFjsWzkEciECIRDKO5VNRoGW4978Hm", "encoder/saved_models/pretrained.pt")

# Vocoder
download_file("1Z1BO5j104CtHpwl3oVIvNRtbDqUXGdZ9", "vocoder/saved_models/pretrained.pt")

# Synthesizer (TacoTron)
download_file("1rSnF6oR-2MON_6-6oi0zlWU2vwkb9TPg", "synthesizer/saved_models/logs-pretrained/taco_pretrained/checkpoint")
download_file("1GLWwh4K-5D4Gmy6e0TqbYZ8UWYsCtqSv", "synthesizer/saved_models/logs-pretrained/taco_pretrained/tacotron_model.ckpt-278000.data-00000-of-00001")
download_file("1kWyLxdJS-gJ7SoaWEo7n9qx8G-WoU62E", "synthesizer/saved_models/logs-pretrained/taco_pretrained/tacotron_model.ckpt-278000.index")
download_file("1bJ1WgBekNp_8sMzz6J7sp_eFXco_N-TE", "synthesizer/saved_models/logs-pretrained/taco_pretrained/tacotron_model.ckpt-278000.meta")
