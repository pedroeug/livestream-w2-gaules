# livestream-w2-gaules/pipeline/worker.py

import os
import time
import whisper
from deep_translator import DeeplTranslator
import requests
import subprocess
from speechify_sws import SpeechifyClient  # Supondo que speechify-sws esteja instalado

def worker_loop(channel: str, lang: str):
    """
    Loop que:
      1) Monitora audio_segments/{channel}/segment_XXX.wav
      2) Transcreve com Whisper
      3) Traduz com DeepL
      4) Sintetiza com Speechify SWS
      5) Concatena MP3 e gera HLS em hls/{channel}/{lang}
    """

    # 0) Carrega Whisper e Speechify Client
    model = whisper.load_model("base")
    speechify_api_key = os.getenv("SPEECHIFY_API_KEY")
    voice_id = os.getenv("SPEECHIFY_VOICE_ID")  # ex: "3af44bf3-439e-4e9d-a6ff-4870d437ef7a"
    if not speechify_api_key or not voice_id:
        print("[worker] AVISO: SPEECHIFY_API_KEY ou SPEECHIFY_VOICE_ID não definido.")
    client = None
    if speechify_api_key and voice_id:
        client = SpeechifyClient(api_key=speechify_api_key)

    processed = set()
    audio_dir = os.path.join("audio_segments", channel)
    hls_dir = os.path.join("hls", channel, lang)
    proc_dir = os.path.join(audio_dir, "processed")
    os.makedirs(proc_dir, exist_ok=True)

    # 1) Cria o arquivo concat.mp3 inicial (silêncio) em processed/
    concat_mp3 = os.path.join(proc_dir, "concat.mp3")
    if not os.path.exists(concat_mp3):
        os.system(
            f"ffmpeg -y -f lavfi -i anullsrc=r=16000:cl=mono -t 1 "
            f"-c:a libmp3lame -b:a 64k "
            f"{concat_mp3}"
        )
        print(f"[worker] Arquivo inicial de concat.mp3 criado em {concat_mp3}")

    while True:
        for filename in sorted(os.listdir(audio_dir)):
            if not filename.endswith(".wav") or filename in processed:
                continue

            wav_path = os.path.join(audio_dir, filename)
            print(f"[worker] Processando arquivo: {wav_path}")

            try:
                # 2) Transcrever com Whisper (forçado para pt se quiser)
                print(f"[worker] Transcrevendo {wav_path} ...")
                result = model.transcribe(wav_path, language="pt")  # se o canal fala português
                text = result["text"].strip()
                print(f"[worker] Transcrição: {text}")

                # 3) Traduzir com DeepL para ‘lang’
                print(f"[worker] Traduzindo para {lang} ...")
                translator = DeeplTranslator(source="auto", target=lang)
                translated = translator.translate(text)
                print(f"[worker] Tradução: {translated}")

                # 4) Sintetizar texto com Speechify SWS
                dubbed_wav = os.path.join(proc_dir, filename.replace(".wav", f"_{lang}.wav"))
                if client:
                    print("[worker] Sintetizando com Speechify SWS ...")
                    # Exemplo usando a SDK fake (ajuste conforme speechify-sws real)
                    resp = client.text_to_speech(
                        text=translated,
                        voice_id=voice_id,
                        output= dubbed_wav  # salva o .wav
                    )
                    if not os.path.exists(dubbed_wav):
                        print(f"[worker] Erro ao gerar TTS Speechify para {filename}")
                        processed.add(filename)
                        continue
                    print(f"[worker] Áudio sintetizado salvo em {dubbed_wav}")
                else:
                    print("[worker] Pulando síntese: Speechify não configurado.")
                    processed.add(filename)
                    continue

                # 5) Converter esse WAV para MP3
                mp3_path = dubbed_wav.replace(".wav", ".mp3")
                print(f"[worker] Convertendo WAV para MP3: {dubbed_wav} -> {mp3_path}")
                subprocess.run(
                    ["ffmpeg", "-y", "-i", dubbed_wav, "-codec:a", "libmp3lame", "-b:a", "128k", mp3_path],
                    check=True,
                )
                print(f"[worker] MP3 gerado em {mp3_path}")

                # 6) Concatena no concat.mp3 atual
                tmp_concat = concat_mp3 + ".temp"
                print(f"[worker] Adicionando {mp3_path} ao {concat_mp3}")
                subprocess.run(
                    ["ffmpeg", "-y", "-i", f"concat:{concat_mp3}|{mp3_path}", "-c", "copy", tmp_concat],
                    check=True,
                )
                os.replace(tmp_concat, concat_mp3)
                print(f"[worker] concat.mp3 atualizado.")

                # 7) Gerar HLS (recria o index.m3u8 e .ts) usando o concat.mp3
                output_index = os.path.join(hls_dir, "index.m3u8")
                ts_pattern = os.path.join(hls_dir, "%03d.ts")
                print(f"[worker] Gerando HLS em {output_index} ...")
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        concat_mp3,
                        "-c:a",
                        "aac",
                        "-b:a",
                        "128k",
                        "-vn",
                        "-hls_time",
                        "10",
                        "-hls_playlist_type",
                        "event",
                        "-hls_segment_filename",
                        ts_pattern,
                        output_index,
                    ],
                    check=True,
                )
                print(f"[worker] HLS atualizado em {output_index}")

                processed.add(filename)

            except Exception as e:
                print(f"[worker] Erro ao processar {wav_path}: {e}")
                processed.add(filename)

        time.sleep(1)
