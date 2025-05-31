# livestream-w2-gaules/pipeline/worker.py

import os
import time
import whisper
from deep_translator import DeeplTranslator
import requests
import subprocess
import shutil
import logging

# Configura logging simples
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("worker")


def worker_loop(audio_dir: str, lang: str):
    """
    Loop contínuo que:
      1. Monitora novos arquivos .wav em audio_dir.
      2. Transcreve usando Whisper.
      3. Traduz a transcrição (DeepL via deep_translator).
      4. Síntese de voz (Coqui TTS via REST).
      5. Concatena pedacinhos de MP3 em um único arquivo contínuo (concat.mp3).
      6. Empacota em HLS (.ts + index.m3u8) em hls/{channel}/{lang}/.
    """

    # 1) Carrega modelo Whisper
    model = whisper.load_model("base")
    processed = set()

    # PASTA onde colocamos os MP3s processados para concatenação
    processed_dir = os.path.join(audio_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    # Arquivo contínuo que vai somar todos os segmentos em MP3:
    concat_mp3_path = os.path.join(processed_dir, "concat.mp3")

    # Caminho fixo do sample para clonagem de voz no Coqui:
    coqui_speaker_wav = os.path.join("assets", "voices", "gaules_sample.wav")

    while True:
        for filename in sorted(os.listdir(audio_dir)):
            # só processa arquivos WAV originais (p. ex. segment_000.wav)
            if not filename.endswith(".wav") or filename in processed:
                continue

            wav_path = os.path.join(audio_dir, filename)
            logger.info(f"Processando segmento: {wav_path}")

            try:
                # 2) Transcrição
                logger.info(f"Transcrevendo {wav_path} com idioma forçado para português...")
                result = model.transcribe(wav_path, language="pt")
                text = result["text"].strip()
                logger.info(f"Transcrição: {text}")

                # 3) Tradução com DeepL (deep_translator)
                logger.info(f"Traduzindo para {lang} ...")
                translator = DeeplTranslator(source="auto", target=lang)
                translated = translator.translate(text)
                logger.info(f"Tradução: {translated}")

                # 4) Síntese de voz com Coqui TTS
                output_wav = wav_path.replace(".wav", f"_{lang}.wav")

                if lang == "en":
                    logger.info("Sintetizando texto traduzido com Coqui TTS (clonagem de voz)...")
                    coqui_endpoint = "https://app.coqui.ai/tts/inference"
                    headers = {
                        "Content-Type": "application/json",
                    }
                    payload = {
                        "text": translated,
                        "voice_cloning": True,
                        "speaker_wav": coqui_speaker_wav,
                    }
                    response = requests.post(coqui_endpoint, json=payload, headers=headers)
                    if response.status_code == 200:
                        with open(output_wav, "wb") as f:
                            f.write(response.content)
                        logger.info(f"Áudio sintetizado salvo em {output_wav}")
                    else:
                        logger.error(f"Erro Coqui TTS ({response.status_code}): {response.text}")
                        processed.add(filename)
                        continue

                else:
                    logger.info(f"Sintetizando texto traduzido com Coqui TTS (voz padrão) para idioma {lang} ...")
                    coqui_endpoint = "https://app.coqui.ai/tts/inference"
                    headers = {
                        "Content-Type": "application/json",
                    }
                    payload = {
                        "text": translated,
                        "voice": "multi-lingual",
                    }
                    response = requests.post(coqui_endpoint, json=payload, headers=headers)
                    if response.status_code == 200:
                        with open(output_wav, "wb") as f:
                            f.write(response.content)
                        logger.info(f"Áudio sintetizado salvo em {output_wav}")
                    else:
                        logger.error(f"Erro Coqui TTS ({response.status_code}): {response.text}")
                        processed.add(filename)
                        continue

                # 5) Converte o WAV sintetizado para MP3
                dubbed_mp3 = output_wav.replace(".wav", ".mp3")  # ex: segment_000_en.mp3
                logger.info(f"Convertendo WAV para MP3: {output_wav} -> {dubbed_mp3}")
                ffmpeg_to_mp3 = [
                    "ffmpeg", "-y",
                    "-i", output_wav,
                    "-codec:a", "libmp3lame",
                    "-b:a", "128k",
                    dubbed_mp3
                ]
                subprocess.run(ffmpeg_to_mp3, check=True)
                logger.info(f"Arquivo convertido para MP3: {dubbed_mp3}")

                # Move o MP3 recém-gerado para a pasta `processed_dir`
                target_dubbed_mp3 = os.path.join(processed_dir, os.path.basename(dubbed_mp3))
                shutil.move(dubbed_mp3, target_dubbed_mp3)
                logger.info(f"Movido para pasta processed: {target_dubbed_mp3}")

                # 6) Concatena ao arquivo contínuo concat.mp3
                if not os.path.exists(concat_mp3_path):
                    # Se não existir ainda, basta renomear este primeiro MP3 para concat.mp3
                    os.replace(target_dubbed_mp3, concat_mp3_path)
                    logger.info(f"Criado arquivo contínuo inicial: {concat_mp3_path}")
                else:
                    # Se já existir concat.mp3, faz concat adequado:
                    temp_concat = os.path.join(processed_dir, "concat_tmp.mp3")
                    concat_input = f"concat:{concat_mp3_path}|{target_dubbed_mp3}"
                    logger.info(f"Adicionando segmento ao arquivo contínuo: {concat_mp3_path}")
                    ffmpeg_concat = [
                        "ffmpeg", "-y",
                        "-i", concat_input,
                        "-acodec", "copy",
                        temp_concat
                    ]
                    try:
                        subprocess.run(ffmpeg_concat, check=True)
                        # Se tudo der certo, substitui o antigo concat.mp3
                        os.replace(temp_concat, concat_mp3_path)
                        logger.info(f"Arquivo contínuo atualizado em: {concat_mp3_path}")
                    except subprocess.CalledProcessError as cpe:
                        logger.error(f"Erro ao executar ffmpeg concat: {cpe}")
                        # Se o temp_concat foi criado parcialmente, remove-o
                        if os.path.exists(temp_concat):
                            os.remove(temp_concat)
                        processed.add(filename)
                        continue

                # 7) Empacotar em HLS via ffmpeg usando o MP3 isolado (target_dubbed_mp3)
                channel = os.path.basename(audio_dir)
                hls_dir = os.path.join("hls", channel, lang)
                os.makedirs(hls_dir, exist_ok=True)

                # Use o arquivo MP3 recém-gerado para criar segmentos HLS de 10s:
                input_for_hls = target_dubbed_mp3
                ts_pattern = os.path.join(hls_dir, "%03d.ts")
                output_index = os.path.join(hls_dir, "index.m3u8")

                logger.info(f"Convertendo {input_for_hls} para HLS em {output_index} ...")
                ffmpeg_hls = [
                    "ffmpeg", "-y",
                    "-i", input_for_hls,
                    "-c:a", "aac", "-b:a", "128k",
                    "-vn",
                    "-hls_time", "10",
                    "-hls_playlist_type", "event",
                    "-hls_segment_filename", ts_pattern,
                    output_index
                ]
                subprocess.run(ffmpeg_hls, check=True)
                logger.info(f"HLS gerado em {output_index}")

                # Finalmente, marca este segmento como processado
                processed.add(filename)

            except Exception as e:
                logger.error(f"Erro ao processar {wav_path}: {e}")
                processed.add(filename)

        # Aguarda um segundo antes de checar novamente novos WAVs
        time.sleep(1)
