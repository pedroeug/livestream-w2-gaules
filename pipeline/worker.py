# livestream-w2-gaules/pipeline/worker.py

import os
import time
import whisper
from deep_translator import DeeplTranslator
import subprocess
from TTS.api import TTS

def worker_loop(audio_dir: str, lang: str):
    """
    Loop contínuo que:
      1. Monitora novos arquivos .wav em audio_dir.
      2. Transcreve usando Whisper.
      3. Traduz a transcrição (DeepL).
      4. Sintetiza em voz usando Coqui TTS:
         - Se lang == "en", aplica voice‐cloning via speaker_wav.
         - Para outros idiomas, usa modelo multilingual sem clonagem.
      5. Empacota o áudio resultante em HLS (.ts + index.m3u8) em hls/{channel}/{lang}/.
    """

    # 1) Carrega o modelo Whisper (vai demorar um pouco na primeira vez)
    model = whisper.load_model("base")

    # 2) Configura Coqui TTS:
    #    - Para inglês com clonagem de voz, usamos "tts_models/multilingual/multi-dataset/your_tts"
    #      e passamos speaker_wav="assets/voices/gaules_sample.wav".
    #    - Para outros idiomas, usamos o mesmo modelo sem speaker_wav (single‐speaker padrão).
    #
    # OBSERVAÇÃO: substitua "tts_models/multilingual/multi-dataset/your_tts" pelo nome exato
    # do modelo que você treinou/baixou para voice‐cloning, se for diferente.
    tts_clone = TTS(
        model_name="tts_models/multilingual/multi-dataset/your_tts",
        progress_bar=False,
        gpu=False
    )
    tts_default = TTS(
        model_name="tts_models/multilingual/multi-dataset/your_tts",
        progress_bar=False,
        gpu=False
    )
    speaker_wav = "assets/voices/gaules_sample.wav"
    if not os.path.isfile(speaker_wav):
        print(f"[worker] AVISO: speaker_wav não encontrado em {speaker_wav}. Voice‐cloning pode falhar.")

    processed = set()

    while True:
        # Lista todos os arquivos .wav ainda não processados
        for filename in sorted(os.listdir(audio_dir)):
            if not filename.endswith(".wav") or filename in processed:
                continue

            wav_path = os.path.join(audio_dir, filename)
            print(f"[worker] Encontrou novo segmento: {wav_path}")

            try:
                # 3) Transcrição com Whisper
                print(f"[worker] Transcrevendo {wav_path} ...")
                result = model.transcribe(wav_path)
                text = result["text"].strip()
                print(f"[worker] Transcrição: {text}")

                # 4) Tradução com DeepL
                print(f"[worker] Traduzindo para '{lang}' ...")
                translator = DeeplTranslator(source="auto", target=lang)
                translated = translator.translate(text)
                print(f"[worker] Tradução: {translated}")

                # 5) Síntese de voz com Coqui TTS
                #    Geramos primeiro um WAV de saída, depois convertemos para MP3.
                base_name = filename.replace(".wav", f"_{lang}")
                tts_output_wav = os.path.join(audio_dir, base_name + ".wav")
                tts_output_mp3 = os.path.join(audio_dir, base_name + ".mp3")

                if lang.lower() == "en":
                    print(f"[worker] Sintetizando '{translated}' com Coqui TTS (voice‐cloning) ...")
                    # Gera WAV clonando a voz usando o sample speaker_wav
                    tts_clone.tts_to_file(
                        text=translated,
                        speaker_wav=speaker_wav,
                        file_path=tts_output_wav
                    )
                else:
                    print(f"[worker] Sintetizando '{translated}' com Coqui TTS (multilingual sem clonagem) ...")
                    # Gera WAV sem clonagem (modelo multilingual)
                    tts_default.tts_to_file(
                        text=translated,
                        file_path=tts_output_wav
                    )

                print(f"[worker] WAV sintetizado salvo em {tts_output_wav}")

                # 6) Converte o WAV sintetizado para MP3 via FFmpeg
                print(f"[worker] Convertendo {tts_output_wav} para MP3 ...")
                ffmpeg_mp3_cmd = [
                    "ffmpeg", "-y",
                    "-i", tts_output_wav,
                    "-codec:a", "libmp3lame",
                    "-qscale:a", "2",
                    tts_output_mp3
                ]
                subprocess.run(ffmpeg_mp3_cmd, check=True)
                print(f"[worker] MP3 gerado em {tts_output_mp3}")

                # 7) Empacota em HLS via FFmpeg (.ts segments + index.m3u8)
                channel = os.path.basename(audio_dir)
                hls_dir = os.path.join("hls", channel, lang)
                os.makedirs(hls_dir, exist_ok=True)

                ts_pattern = os.path.join(hls_dir, "%03d.ts")
                output_index = os.path.join(hls_dir, "index.m3u8")

                print(f"[worker] Convertendo {tts_output_mp3} para HLS em {output_index} ...")
                ffmpeg_hls_cmd = [
                    "ffmpeg", "-y",
                    "-i", tts_output_mp3,
                    "-c:a", "aac", "-b:a", "128k",
                    "-vn",
                    "-hls_time", "10",
                    "-hls_playlist_type", "event",
                    "-hls_segment_filename", ts_pattern,
                    output_index
                ]
                subprocess.run(ffmpeg_hls_cmd, check=True)
                print(f"[worker] HLS gerado em {output_index}")

                processed.add(filename)

            except Exception as e:
                print(f"[worker] Erro ao processar {wav_path}: {e}")
                processed.add(filename)

        time.sleep(1)  # Espera 1 segundo antes de checar novamente
