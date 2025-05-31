# livestream-w2-gaules/pipeline/worker.py

import os
import time
import whisper
from deep_translator import DeeplTranslator
import subprocess

# Importamos o Coqui TTS
from TTS.api import TTS


def worker_loop(audio_dir: str, lang: str):
    """
    Loop contínuo que:
      1. Monitora novos arquivos .wav em audio_dir.
      2. Transcreve usando Whisper.
      3. Traduz a transcrição (DeepL).
      4. Síntese de voz (Coqui TTS).
      5. Empacota em HLS (.ts + index.m3u8) em hls/{channel}/{lang}/.
    """

    # 1) Carrega o modelo Whisper
    model = whisper.load_model("base")

    # 2) Inicializa o Coqui TTS de acordo com a língua desejada
    #    Mapeamos 'lang' para um modelo Coqui. Por exemplo:
    #    - 'en' ou 'en-US' → tts_models/en/vctk/vits
    #    - 'pt' ou 'pt-BR' → tts_models/pt/mai/tacotron2-DDC
    #    Caso contrário, usa um modelo default (em inglês).
    TTS_MODEL_MAP = {
        "en": "tts_models/en/vctk/vits",
        "en-US": "tts_models/en/vctk/vits",
        "pt": "tts_models/pt/mai/tacotron2-DDC",
        "pt-BR": "tts_models/pt/mai/tacotron2-DDC",
    }
    chosen_model = TTS_MODEL_MAP.get(lang, "tts_models/en/vctk/vits")

    print(f"[worker] Carregando Coqui TTS modelo '{chosen_model}' para linguagem '{lang}' ...")
    tts = TTS(model_name=chosen_model, progress_bar=False, gpu=False)
    print("[worker] Coqui TTS carregado com sucesso.")

    processed = set()

    while True:
        # Lista todos os arquivos .wav ainda não processados
        for filename in sorted(os.listdir(audio_dir)):
            if not filename.endswith(".wav") or filename in processed:
                continue

            wav_path = os.path.join(audio_dir, filename)
            print(f"[worker] Encontrou novo segmento: {wav_path}")

            try:
                # 1) Transcrição com Whisper
                print(f"[worker] Transcrevendo {wav_path} ...")
                result = model.transcribe(wav_path)
                text = result["text"].strip()
                print(f"[worker] Transcrição: {text}")

                # 2) Tradução com DeepL (ou mantém texto original, se lang='en')
                if lang != "en":
                    print(f"[worker] Traduzindo para '{lang}' ...")
                    translator = DeeplTranslator(source="auto", target=lang)
                    translated = translator.translate(text)
                    print(f"[worker] Tradução: {translated}")
                else:
                    translated = text
                    print("[worker] Idioma 'en' selecionado, pulando tradução.")

                # 3) Síntese de voz com Coqui TTS
                print(f"[worker] Sintetizando texto com Coqui TTS ...")
                # Definimos o arquivo de saída TTS (WAV) no mesmo diretório que o .wav original
                output_wav = wav_path.replace(".wav", f"_{lang}.wav")
                # Gera o TTS e grava diretamente em output_wav
                tts.tts_to_file(text=translated, file_path=output_wav)
                print(f"[worker] Áudio sintetizado salvo em {output_wav}")

                # 4) Empacotar em HLS via ffmpeg
                channel = os.path.basename(audio_dir)
                hls_dir = os.path.join("hls", channel, lang)
                os.makedirs(hls_dir, exist_ok=True)

                ts_pattern = os.path.join(hls_dir, "%03d.ts")
                output_index = os.path.join(hls_dir, "index.m3u8")

                print(f"[worker] Convertendo {output_wav} para HLS em {output_index} ...")
                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-i", output_wav,
                    "-c:a", "aac", "-b:a", "128k",
                    "-vn",
                    "-hls_time", "10",
                    "-hls_playlist_type", "event",
                    "-hls_segment_filename", ts_pattern,
                    output_index
                ]
                subprocess.run(ffmpeg_cmd, check=True)
                print(f"[worker] HLS gerado em {output_index}")

                # Marca este segmento como processado
                processed.add(filename)

            except Exception as e:
                # Em caso de erro, marca como processado para não travar em loop infinito
                print(f"[worker] Erro ao processar {wav_path}: {e}")
                processed.add(filename)

        time.sleep(1)  # Espera 1 segundo antes de checar novamente
