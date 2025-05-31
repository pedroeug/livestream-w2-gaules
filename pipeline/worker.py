# livestream-w2-gaules/pipeline/worker.py

import os
import time
import whisper
from deep_translator import DeeplTranslator
import subprocess
import torch
from TTS.api import TTS
import logging

logger = logging.getLogger("worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def worker_loop(audio_dir: str, lang: str):
    """
    Loop contínuo que:
      1. Monitora novos arquivos .wav em audio_dir.
      2. Transcreve usando Whisper.
      3. Traduz a transcrição (DeepL).
      4. Síntese de voz (Coqui TTS).
      5. Empacota em HLS (.ts + index.m3u8) em hls/{channel}/{lang}/.
    """

    # Carrega o modelo Whisper (você pode passar explicitamente device="cpu" ou "cuda")
    model = whisper.load_model("base")

    # Inicializa Coqui TTS apenas se precisar de clonagem de voz ou TTS single‐speaker
    device = "cuda" if torch.cuda.is_available() else "cpu"
    coqui_model_en = None
    if lang == "en":
        # Para clonagem de voz em inglês, usa o modelo xtts_v2 (ou outro de sua escolha)
        logger.info("Inicializando Coqui TTS (modelo: tts_models/multilingual/multi-dataset/xtts_v2) para clonagem de voz em inglês.")
        coqui_model_en = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

    processed = set()
    processed_dir = os.path.join(audio_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    # Cria um MP3 vazio para fazer concatenação se ainda não existir
    concat_mp3 = os.path.join(processed_dir, "concat.mp3")
    if not os.path.exists(concat_mp3):
        # Gera um arquivo MP3 vazio de 1 segundo (silêncio) para iniciar a concatenação
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", "1",
            "-q:a", "9",
            "-acodec", "libmp3lame",
            concat_mp3
        ], check=True)
        logger.info(f"Arquivo inicial de concat.mp3 criado em {concat_mp3}")

    while True:
        for filename in sorted(os.listdir(audio_dir)):
            if not filename.endswith(".wav") or filename in processed:
                continue

            wav_path = os.path.join(audio_dir, filename)
            logger.info(f"Processando segmento: {wav_path}")

            try:
                # 1) Transcrição com Whisper (forçando português para entender o gaúcho)
                logger.info(f"Transcrevendo {wav_path} com idioma forçado para português...")
                result = model.transcribe(wav_path, language="pt")
                text = result["text"].strip()
                logger.info(f"Transcrição: {text}")

                # 2) Tradução com DeepL (para target=lang)
                logger.info(f"Traduzindo para {lang} ...")
                translator = DeeplTranslator(source="auto", target=lang)
                translated = translator.translate(text)
                logger.info(f"Tradução: {translated}")

                # 3) Síntese de voz com Coqui TTS
                if lang == "en" and coqui_model_en:
                    # Exemplo: usa um arquivo de amostra (speaker wav) para clonagem
                    speaker_wav = "assets/voices/gaules_sample.wav"
                    logger.info("Sintetizando texto traduzido com Coqui TTS (voice cloning)...")
                    output_wav = wav_path.replace(".wav", f"_cloned_{lang}.wav")
                    coqui_model_en.tts_to_file(
                        text=translated,
                        speaker_wav=speaker_wav,
                        language="en",
                        file_path=output_wav
                    )
                    logger.info(f"Áudio sintetizado salvo em {output_wav}")

                    # 4) Converte WAV para MP3
                    output_mp3 = output_wav.replace(".wav", ".mp3")
                    logger.info(f"Convertendo WAV para MP3: {output_wav} -> {output_mp3}")
                    subprocess.run([
                        "ffmpeg", "-y",
                        "-i", output_wav,
                        "-q:a", "4",  # ajustar qualidade se quiser
                        output_mp3
                    ], check=True)
                    logger.info(f"Arquivo convertido para MP3: {output_mp3}")

                    # 5) Concatena no arquivo contínuo (concat.mp3)
                    #    Usamos concat protocol do ffmpeg: “concat:file1.mp3|file2.mp3” → temp, depois mv.
                    temp_concat = concat_mp3 + ".temp"
                    cmd_concat = [
                        "ffmpeg", "-y",
                        "-i", f"concat:{concat_mp3}|{output_mp3}",
                        "-acodec", "copy",
                        temp_concat
                    ]
                    logger.info(f"Adicionando segmento ao arquivo contínuo: {concat_mp3}")
                    try:
                        subprocess.run(cmd_concat, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                        os.replace(temp_concat, concat_mp3)
                    except subprocess.CalledProcessError as e:
                        logger.error(f"Erro ao executar ffmpeg: {e}")
                        logger.error(f"Saída de erro: {e.stderr.decode('utf-8', errors='ignore')}")
                        # continua mesmo se der erro na concat
                    # -----------------------------------------------------

                else:
                    # Se for outro idioma (por ex. pt), você pode escolher usar um TTS single‐speaker:
                    # Exemplo: tts = TTS("tts_models/pt/brazilian/your_tts_or_another").to(device)
                    # Aqui, apenas salvamos a transcrição pura como texto, sem TTS.
                    logger.info(f"Pulando Coqui TTS para lang={lang} (sem clonagem ou sem voz definida).")

                processed.add(filename)

            except Exception as e:
                logger.error(f"Erro ao processar {wav_path}: {e}")
                processed.add(filename)

        time.sleep(1)
