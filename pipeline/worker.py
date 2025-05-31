# livestream-w2-gaules/pipeline/worker.py

import os
import time
import whisper
from deep_translator import DeeplTranslator
import subprocess
from TTS.api import TTS  # Usaremos o Coqui TTS local

import logging

logger = logging.getLogger("worker")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

def worker_loop(audio_dir: str, lang: str):
    """
    Loop contínuo que:
      1. Monitora novos arquivos .wav em audio_dir.
      2. Transcreve usando Whisper.
      3. Traduz a transcrição (DeepL).
      4. Síntese de voz (Coqui TTS local, com clonagem de voz se lang == "en").
      5. Empacota em HLS (.ts + index.m3u8) em hls/{channel}/{lang}/.
    """

    # 1) Carrega o modelo Whisper
    model = whisper.load_model("base")

    # 2) Inicializa o Coqui TTS (vamos instanciar depois, quando soubermos se precisa de clonagem ou não)
    #    Não precisamos de COQUI_API_KEY aqui; usamos os modelos locais.
    #    Vamos usar:
    #      - Para inglês com clonagem: modelo "tts_models/multilingual/multi-dataset/xtts_v2"
    #      - Para outros idiomas sem clonagem: um modelo simples, por ex. "tts_models/pt/mai/tacotron2-DDC"
    tts_multilingual = None
    tts_single = None

    # Carregamento sob demanda
    def get_tts_model(is_cloning: bool):
        nonlocal tts_multilingual, tts_single
        if is_cloning:
            if tts_multilingual is None:
                logger.info("[worker] Carregando Coqui TTS (multilíngue + clonagem)...")
                tts_multilingual = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cpu")
            return tts_multilingual
        else:
            if tts_single is None:
                # Exemplo: modelo para português sem clonagem
                model_name = "tts_models/pt/mai/tacotron2-DDC"
                logger.info(f"[worker] Carregando Coqui TTS (modelo single-speaker {model_name})...")
                tts_single = TTS(model_name, progress_bar=False).to("cpu")
            return tts_single

    processed = set()

    # 3) Garante diretório de `processed/` para cada canal
    channel = os.path.basename(audio_dir)
    processed_dir = os.path.join(audio_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    # 4) Cria um arquivo inicial de concatenação MP3 vazio usando um áudio nulo
    concat_mp3 = os.path.join(processed_dir, "concat.mp3")
    if not os.path.exists(concat_mp3):
        # Geramos um MP3 curto de áudio em silêncio para iniciar
        logger.info(f"[worker] Criando arquivo inicial de concatenação: {concat_mp3}")
        temp_silent_wav = os.path.join(processed_dir, "silent.wav")
        # gera 1 segundo de silêncio em WAV
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", "1",
            temp_silent_wav
        ], check=True)
        # converte para MP3
        subprocess.run([
            "ffmpeg", "-y",
            "-i", temp_silent_wav,
            "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1",
            concat_mp3
        ], check=True)
        os.remove(temp_silent_wav)
        logger.info(f"[worker] Arquivo inicial de concat.mp3 criado em {concat_mp3}")

    while True:
        # Percorre os arquivos WAV novos não processados
        for filename in sorted(os.listdir(audio_dir)):
            if not filename.endswith(".wav") or filename in processed:
                continue

            wav_path = os.path.join(audio_dir, filename)
            logger.info(f"[worker] Processando segmento: {wav_path}")

            try:
                # 1) Transcrição com Whisper
                logger.info(f"[worker] Transcrevendo {wav_path} com idioma forçado para português...")
                result = model.transcribe(wav_path, language="pt")
                text = result["text"].strip()
                logger.info(f"[worker] Transcrição: {text}")

                # 2) Tradução com DeepL
                logger.info(f"[worker] Traduzindo para {lang} ...")
                translator = DeeplTranslator(source="auto", target=lang)
                translated = translator.translate(text)
                logger.info(f"[worker] Tradução: {translated}")

                # 3) Síntese de voz com Coqui TTS local
                is_cloning = (lang == "en")
                tts_model = get_tts_model(is_cloning)

                if is_cloning:
                    # Clonagem de voz: buscamos um arquivo de exemplo para a voz do Gaules
                    # (supondo que você tenha feito upload de um WAV em assets/voices/gaules_sample.wav)
                    speaker_wav = os.path.join("assets", "voices", "gaules_sample.wav")
                    logger.info(f"[worker] Sintetizando com clonagem para inglês usando {speaker_wav} ...")
                    dubbed_wav = wav_path.replace(".wav", f"_{lang}.wav")
                    tts_model.tts_to_file(
                        text=translated,
                        speaker_wav=speaker_wav,
                        language="en",
                        file_path=dubbed_wav
                    )
                else:
                    # Sem clonagem: apenas falamos no idioma desejado (ex.: pt)
                    dubbed_wav = wav_path.replace(".wav", f"_{lang}.wav")
                    logger.info(f"[worker] Sintetizando texto traduzido com modelo single-speaker ...")
                    tts_model.tts_to_file(
                        text=translated,
                        file_path=dubbed_wav
                    )

                logger.info(f"[worker] Áudio sintetizado salvo em {dubbed_wav}")

                # 4) Converter WAV sintetizado para MP3
                dubbed_mp3 = dubbed_wav.replace(".wav", ".mp3")
                logger.info(f"[worker] Convertendo WAV para MP3: {dubbed_wav} -> {dubbed_mp3}")
                subprocess.run(
                    ["ffmpeg", "-y", "-i", dubbed_wav, "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1", dubbed_mp3],
                    check=True
                )
                logger.info(f"[worker] Arquivo convertido para MP3: {dubbed_mp3}")

                # 5) Adiciona esse MP3 ao arquivo contínuo de concatenação
                logger.info(f"[worker] Adicionando segmento ao arquivo contínuo: {concat_mp3}")
                temp_concat = concat_mp3 + ".temp"
                concat_input = f"concat:{concat_mp3}|{dubbed_mp3}"
                subprocess.run(
                    ["ffmpeg", "-y", "-i", concat_input, "-acodec", "copy", temp_concat],
                    check=True
                )
                # Substitui o concat antigo pelo novo
                os.replace(temp_concat, concat_mp3)

                # 6) Empacotar em HLS via ffmpeg
                hls_dir = os.path.join("hls", channel, lang)
                os.makedirs(hls_dir, exist_ok=True)

                ts_pattern = os.path.join(hls_dir, "%03d.ts")
                output_index = os.path.join(hls_dir, "index.m3u8")

                logger.info(f"[worker] Convertendo {concat_mp3} para HLS em {output_index} ...")
                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-i", concat_mp3,
                    "-c:a", "aac", "-b:a", "128k",
                    "-vn",
                    "-hls_time", "10",
                    "-hls_playlist_type", "event",
                    "-hls_segment_filename", ts_pattern,
                    output_index
                ]
                subprocess.run(ffmpeg_cmd, check=True)
                logger.info(f"[worker] HLS gerado em {output_index}")

                processed.add(filename)

            except Exception as e:
                logger.error(f"[worker] Erro ao processar {wav_path}: {e}")
                processed.add(filename)

        time.sleep(1)
