# livestream-w2-gaules/pipeline/worker.py

import os
import time
import logging
import whisper
import requests
import subprocess
import base64

from deep_translator import DeeplTranslator

logger = logging.getLogger("worker")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)


def worker_loop(audio_dir: str, processed_dir: str, lang: str, hls_dir: str):
    """
    Loop contínuo que:
      1. Monitora novos arquivos .wav em audio_dir.
      2. Transcreve usando Whisper (forçando português se o canal falar PT).
      3. Traduz a transcrição (DeepL).
      4. Faz TTS com Coqui (voz clonada se lang == "en"; voz padrão se outro lang).
      5. Concatena MP3 em processed_dir/concat.mp3.
      6. Empacota em HLS (.ts + index.m3u8) em hls_dir.

    Args:
      audio_dir (str): p.ex. "audio_segments/gaules"
      processed_dir (str): p.ex. "audio_segments/gaules/processed"
      lang (str): "en" ou "pt" (ou "es")
      hls_dir (str): p.ex. "hls/gaules/en"
    """

    # 1) Carrega o modelo Whisper ("base"), que ficará em CPU
    logger.info("Carregando modelo Whisper 'base' (pode demorar no primeiro uso)...")
    model = whisper.load_model("base")
    logger.info("Modelo Whisper carregado.")

    # 2) Descobre credenciais Coqui (se existir)
    coqui_api_key = os.getenv("COQUI_API_KEY")
    speaker_wav_path = os.getenv("SPEAKER_WAV_PATH", "assets/voices/gaules_sample.wav")
    if not coqui_api_key:
        logger.warning("COQUI_API_KEY não definido. O pipeline irá pular TTS (Coqui).")

    # 3) Cria o arquivo inicial de concatenação (um MP3 em branco) em processed_dir:
    concat_mp3 = os.path.join(processed_dir, "concat.mp3")
    if not os.path.isfile(concat_mp3):
        # Gera um MP3 vazio usando ffmpeg + anullsrc para poder concatenar depois.
        cmd_init = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", "0.1",  # duração quase zero
            "-q:a", "9",  # qualidade baixa, apenas placeholder
            concat_mp3
        ]
        try:
            subprocess.run(cmd_init, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info(f"Arquivo inicial de concat.mp3 criado em {concat_mp3}")
        except Exception as e:
            logger.error(f"Falha ao criar concat.mp3 inicial: {e}")
            return

    processed_files = set()  # nomes de arquivos WAV que já processamos

    while True:
        # 4) Escaneia continuamente todos os arquivos WAV novos em audio_dir
        for filename in sorted(os.listdir(audio_dir)):
            if not filename.lower().endswith(".wav"):
                continue
            if filename in processed_files:
                continue

            wav_path = os.path.join(audio_dir, filename)
            logger.info(f"Processando segmento: {wav_path}")

            try:
                # —————————————
                # a) Transcrição com Whisper (forçando língua se for PT/br)
                # —————————————
                whisper_options = {}
                # Se for áudio em Português (language code PT), forçamos idioma:
                if lang == "pt":
                    whisper_options["language"] = "pt"
                    whisper_options["task"] = "transcribe"
                    logger.info(f"Transcrevendo {wav_path} (forçando português)...")
                    result = model.transcribe(wav_path, **whisper_options)
                else:
                    # Para qualquer outra língua, deixa Whisper detectar auto
                    logger.info(f"Transcrevendo {wav_path} (auto)...")
                    result = model.transcribe(wav_path)

                text = result["text"].strip()
                logger.info(f"Transcrição: {text}")

                # —————————————
                # b) Tradução usando DeepL
                # —————————————
                logger.info(f"Traduzindo para '{lang}' ...")
                translator = DeeplTranslator(source="auto", target=lang)
                try:
                    translated = translator.translate(text)
                except Exception as e:
                    logger.error(f"Erro na tradução DeepL: {e}")
                    translated = text  # se fracassar, mantém texto original
                logger.info(f"Tradução: {translated}")

                # —————————————
                # c) TTS com Coqui
                # —————————————
                #    Se não houver COQUI_API_KEY, será pulado.
                #    Se lang == "en", usa voz clonada (speaker_wav_path)
                #    Caso contrário, usa um modelo mono-língue padrão.
                dubbed_wav = None
                if coqui_api_key:
                    logger.info("Iniciando TTS (Coqui)...")
                    coqui_endpoint = "https://api.coqui.ai/v1/tts"
                    headers = {
                        "Authorization": f"Bearer {coqui_api_key}",
                        "Content-Type": "application/json"
                    }

                    payload = {
                        "text": translated,
                        # Se quisermos voz clonada para EN:
                        **(
                            {"voice": "en/tts_models/en/vctk/vits", "speaker_wav": speaker_wav_path}
                            if lang == "en"
                            else {"voice": f"{lang}/tts_models/{lang}_standard/vits"}
                        )
                    }

                    resp = requests.post(coqui_endpoint, json=payload, headers=headers, timeout=60)
                    if resp.status_code == 200:
                        # Coqui retorna áudio RAW WAV no body (tipo.bytes). Salvamos em WAV.
                        dubbed_wav = os.path.join(processed_dir, filename.replace(".wav", f"_{lang}.wav"))
                        with open(dubbed_wav, "wb") as f:
                            f.write(resp.content)
                        logger.info(f"Áudio sintetizado salvo em {dubbed_wav}")
                    else:
                        logger.error(f"Coqui TTS falhou ({resp.status_code}): {resp.text}")
                        processed_files.add(filename)
                        continue
                else:
                    logger.info("Pulando TTS (sem COQUI_API_KEY).")
                    processed_files.add(filename)
                    continue

                # —————————————
                # d) Converte o WAV sintetizado para MP3 (para concatenar fáceis)
                # —————————————
                dubbed_mp3 = dubbed_wav.replace(".wav", ".mp3")
                logger.info(f"Convertendo WAV para MP3: {dubbed_wav} → {dubbed_mp3}")
                cmd_mp3 = [
                    "ffmpeg", "-y",
                    "-i", dubbed_wav,
                    "-codec:a", "libmp3lame",
                    "-qscale:a", "4",
                    dubbed_mp3
                ]
                subprocess.run(cmd_mp3, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info(f"Arquivo convertido para MP3: {dubbed_mp3}")

                # —————————————
                # e) Concatena no concat.mp3
                # —————————————
                logger.info(f"Adicionando {dubbed_mp3} ao concat.mp3 acumulado...")
                temp_concat = concat_mp3 + ".temp"
                cmd_concat = [
                    "ffmpeg", "-y",
                    "-i", f"concat:{concat_mp3}|{dubbed_mp3}",
                    "-acodec", "copy",
                    temp_concat
                ]
                try:
                    subprocess.run(cmd_concat, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                    # Se deu certo, substitui o antigo concat.mp3
                    os.replace(temp_concat, concat_mp3)
                    logger.info(f"Concat.mp3 atualizado com sucesso em {concat_mp3}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Erro ao executar ffmpeg (concat): {e.stderr.decode(errors='ignore')}")
                    if os.path.isfile(temp_concat):
                        os.remove(temp_concat)
                    processed_files.add(filename)
                    continue

                # —————————————
                # f) Gera HLS (m3u8 + segmentos .ts) a partir do concat.mp3
                # —————————————
                #    Atenção: toda vez que um novo segmento é concatenado, re‐gera a playlist HLS.
                #    Em um cenário real, você poderia otimizar gerando apenas o segmento .ts mais recente e
                #    atualizando o index.m3u8 incrementalmente. Mas, aqui, simplificamos:
                hls_output = os.path.join(hls_dir, "index.m3u8")
                ts_pattern = os.path.join(hls_dir, "%03d.ts")
                logger.info(f"Convertendo {concat_mp3} → HLS em {hls_output} ...")
                cmd_hls = [
                    "ffmpeg", "-y",
                    "-i", concat_mp3,
                    "-c:a", "aac", "-b:a", "128k",
                    "-vn",
                    "-hls_time", "10",
                    "-hls_playlist_type", "event",
                    "-hls_segment_filename", ts_pattern,
                    hls_output
                ]
                subprocess.run(cmd_hls, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info(f"HLS (index.m3u8 + .ts) gerado em {hls_output}")

                # —————————————
                # Marca este WAV como processado
                # —————————————
                processed_files.add(filename)

            except Exception as exc:
                logger.error(f"Erro ao processar {wav_path}: {exc}")
                processed_files.add(filename)

        # Aguarda um segundo antes de varrer novamente
        time.sleep(1)
