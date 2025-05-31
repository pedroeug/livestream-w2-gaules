# livestream-w2-gaules/pipeline/worker.py

import os
import time
import whisper
from deep_translator import DeeplTranslator
import subprocess

# Importa Coqui TTS
from TTS.api import TTS


def worker_loop(audio_dir: str, lang: str):
    """
    Loop contínuo que:
      1. Monitora novos arquivos .wav em audio_dir.
      2. Transcreve usando Whisper.
      3. Traduz a transcrição (DeepL).
      4. Sintetiza texto em áudio com Coqui TTS (voice-cloning em inglês).
      5. Converte em HLS (.ts + index.m3u8) em hls/{channel}/{lang}/.
    """

    # 1) Carrega o modelo Whisper
    model = whisper.load_model("base")

    # 2) Mapeia cada lang para um modelo Coqui diferente.
    #    Se for inglês, usamos o modelo multi-speaker "tts_models/en/vctk/vits",
    #    de modo a poder escolher um speaker_idx (voice-cloning).
    #    Para PT, usamos um modelo single-speaker (sem clonagem).
    TTS_MODEL_MAP = {
        "en":      "tts_models/en/vctk/vits",
        "en-US":   "tts_models/en/vctk/vits",
        "pt":      "tts_models/pt/mai/tacotron2-DDC",
        "pt-BR":   "tts_models/pt/mai/tacotron2-DDC",
    }
    chosen_model = TTS_MODEL_MAP.get(lang, "tts_models/en/vctk/vits")

    print(f"[worker] Carregando Coqui TTS modelo '{chosen_model}' para linguagem '{lang}' ...")
    # Desativa gpu se não estiver disponível
    tts = TTS(model_name=chosen_model, progress_bar=False, gpu=False)
    print("[worker] Coqui TTS carregado com sucesso.")

    # Caso estejamos usando o modelo VCTK (multi-speaker), podemos escolher
    # um speaker_idx fixo (0, 1, 2, ...) para fonacionar “voice-cloning”.
    # Aqui, simplesmente pegamos o speaker_idx = 0 (o primeiro no dataset VCTK).
    use_voice_cloning = chosen_model.startswith("tts_models/en/vctk/vits")
    speaker_idx = 0 if use_voice_cloning else None

    if use_voice_cloning:
        print(f"[worker] Modelo multi-speaker detectado. Usaremos speaker_idx = {speaker_idx} para clonagem de voz.")
        # (Opcional) listar todos os speakers disponíveis, se quiser inspecionar:
        # print(f"[worker] Lista de speakers disponíveis: {tts.speakers}")  

    processed = set()

    while True:
        # 3) Procura por novos segmentos .wav na pasta audio_dir
        for filename in sorted(os.listdir(audio_dir)):
            if not filename.endswith(".wav") or filename in processed:
                continue

            wav_path = os.path.join(audio_dir, filename)
            print(f"[worker] Encontrou novo segmento: {wav_path}")

            try:
                # 3.1) Transcrição com Whisper
                print(f"[worker] Transcrevendo {wav_path} ...")
                result = model.transcribe(wav_path)
                text = result["text"].strip()
                print(f"[worker] Transcrição: {text}")

                # 3.2) Tradução com DeepL (se lang != "en")
                if lang != "en":
                    print(f"[worker] Traduzindo para '{lang}' ...")
                    translator = DeeplTranslator(source="auto", target=lang)
                    translated = translator.translate(text)
                    print(f"[worker] Tradução: {translated}")
                else:
                    translated = text
                    print("[worker] Idioma 'en' selecionado; pulando tradução.")

                # 3.3) Síntese de voz com Coqui TTS
                print(f"[worker] Sintetizando texto com Coqui TTS ...")
                output_wav = wav_path.replace(".wav", f"_{lang}.wav")

                if use_voice_cloning:
                    # Se o modelo suporta multi-speaker (VCTK), passa speaker_idx
                    tts.tts_to_file(
                        text=translated,
                        file_path=output_wav,
                        speaker_idx=speaker_idx
                    )
                    print(f"[worker] (voice-cloning) Áudio sintetizado salvo em {output_wav} usando speaker_idx={speaker_idx}")
                else:
                    # Modelos single-speaker (ex: português) não precisam de speaker_idx
                    tts.tts_to_file(
                        text=translated,
                        file_path=output_wav
                    )
                    print(f"[worker] Áudio sintetizado salvo em {output_wav}")

                # 3.4) Empacotar em HLS via ffmpeg
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

                # Marca este segmento original como processado para não repetir
                processed.add(filename)

            except Exception as e:
                print(f"[worker] Erro ao processar {wav_path}: {e}")
                processed.add(filename)

        time.sleep(1)  # Espera 1 segundo antes de varrer novamente
