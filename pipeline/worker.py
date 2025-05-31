import os
import time
import logging
import subprocess
import whisper
import deepl
from TTS.api import TTS

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("worker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("worker")

# Carrega o modelo Whisper
def load_whisper_model():
    logger.info("Carregando modelo Whisper...")
    model = whisper.load_model("base")
    logger.info("Modelo Whisper carregado com sucesso")
    return model

# Carrega o modelo TTS
def load_tts_model():
    logger.info("Carregando modelo Coqui TTS...")
    
    # Verifica se existe um arquivo de voz para clonagem
    voice_sample = "assets/voices/gaules_sample.wav"
    if os.path.exists(voice_sample):
        logger.info(f"Arquivo de voz para clonagem encontrado: {voice_sample}")
    
    # Carrega o modelo XTTS para clonagem de voz
    model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
    
    logger.info("Modelo Coqui TTS carregado com sucesso")
    return model

# Transcreve o áudio usando Whisper
def transcribe_audio(model, audio_file):
    logger.info(f"Transcrevendo {audio_file} com idioma forçado para português...")
    result = model.transcribe(audio_file, language="pt")
    text = result["text"].strip()
    logger.info(f"Transcrição: {text}")
    return text

# Traduz o texto usando DeepL
def translate_text(text, target_lang):
    logger.info(f"Traduzindo para {target_lang} ...")
    
    try:
        # Usa a API DeepL para tradução
        api_key = os.environ.get("DEEPL_API_KEY", "6403a834-79ed-4d72-ac3e-079417477805:fx")
        translator = deepl.Translator(api_key)
        result = translator.translate_text(text, target_lang=target_lang.upper())
        translated_text = str(result)
        logger.info(f"Tradução: {translated_text}")
        return translated_text
    except Exception as e:
        logger.error(f"Erro na tradução: {e}")
        # Fallback para caso de erro na tradução
        return text

# Sintetiza o texto usando Coqui TTS
def synthesize_speech(model, text, output_file, lang):
    logger.info(f"Sintetizando texto traduzido com Coqui TTS ...")
    
    try:
        # Usa clonagem de voz se disponível
        voice_sample = "assets/voices/gaules_sample.wav"
        
        if os.path.exists(voice_sample):
            logger.info(f"Usando voice cloning para {lang}")
            
            # Mapeia o código de idioma para o formato esperado pelo XTTS
            lang_map = {
                "en": "en",
                "pt": "pt",
                "es": "es"
            }
            
            tts_lang = lang_map.get(lang, "en")
            
            # Sintetiza o áudio com clonagem de voz
            model.tts_to_file(
                text=text,
                file_path=output_file,
                speaker_wav=voice_sample,
                language=tts_lang
            )
        else:
            logger.info("Voice cloning não disponível, usando voz padrão")
            model.tts_to_file(text=text, file_path=output_file)
            
        logger.info(f"Áudio sintetizado salvo em {output_file}")
        return True
    except Exception as e:
        logger.error(f"Erro na síntese de voz: {e}")
        return False

# Converte WAV para MP3
def convert_to_mp3(wav_file, mp3_file):
    logger.info(f"Convertendo WAV para MP3: {wav_file} -> {mp3_file}")
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", wav_file,
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            mp3_file
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"Arquivo convertido para MP3: {mp3_file}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao converter para MP3: {e}")
        logger.error(f"Saída de erro: {e.stderr.decode()}")
        return False

# Concatena arquivos MP3 usando método de lista de arquivos
def concatenate_mp3(concat_file, new_file):
    logger.info(f"Adicionando segmento ao arquivo contínuo: {concat_file}")
    
    try:
        # Método alternativo usando lista de arquivos
        temp_list = "temp_file_list.txt"
        
        # Se o arquivo de concatenação não existe, apenas copie o novo arquivo
        if not os.path.exists(concat_file):
            cmd = ["cp", new_file, concat_file]
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Primeiro segmento copiado para {concat_file}")
            return True
        
        # Cria um arquivo de lista para ffmpeg
        with open(temp_list, "w") as f:
            f.write(f"file '{concat_file}'\n")
            f.write(f"file '{new_file}'\n")
        
        # Usa o método de concatenação com arquivo de lista
        output_file = concat_file + ".new"
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", temp_list,
            "-c", "copy",
            output_file
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Substitui o arquivo original pelo novo
        os.replace(output_file, concat_file)
        
        # Remove o arquivo de lista temporário
        if os.path.exists(temp_list):
            os.remove(temp_list)
            
        logger.info(f"Segmento adicionado com sucesso ao arquivo contínuo")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao executar ffmpeg: {e}")
        logger.error(f"Saída de erro: {e.stderr.decode()}")
        return False
    except Exception as e:
        logger.error(f"Erro ao concatenar arquivos: {e}")
        return False

# Gera o streaming HLS
def generate_hls(input_file, output_dir):
    logger.info(f"Gerando streaming HLS para {input_file}")
    
    try:
        # Garante que o diretório de saída existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Gera o manifesto HLS e os segmentos
        cmd = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-c:a", "aac",
            "-b:a", "128k",
            "-vn",
            "-hls_time", "10",
            "-hls_playlist_type", "event",
            "-hls_segment_filename", f"{output_dir}/%03d.ts",
            f"{output_dir}/index.m3u8"
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"Streaming HLS gerado em {output_dir}/index.m3u8")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao gerar HLS: {e}")
        logger.error(f"Saída de erro: {e.stderr.decode()}")
        return False

# Loop principal do worker
def worker_loop(audio_dir, target_lang):
    # Verifica permissões do diretório
    logger.info(f"Verificando permissões do diretório {audio_dir}")
    if os.access(audio_dir, os.W_OK):
        logger.info(f"Permissões de escrita OK para {audio_dir}")
    else:
        logger.error(f"Sem permissão de escrita para {audio_dir}")
        return
    
    # Carrega os modelos
    whisper_model = load_whisper_model()
    tts_model = load_tts_model()
    
    # Cria diretórios necessários
    processed_dir = os.path.join(audio_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)
    
    # Diretório para streaming HLS
    hls_dir = os.path.join("hls", os.path.basename(audio_dir), target_lang)
    os.makedirs(hls_dir, exist_ok=True)
    
    # Cria um arquivo HLS inicial vazio
    with open(os.path.join(hls_dir, "index.m3u8"), "w") as f:
        f.write("#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n#EXT-X-MEDIA-SEQUENCE:0\n")
    
    logger.info(f"Diretório HLS: {hls_dir}")
    logger.info(f"Arquivo HLS inicial criado em {os.path.join(hls_dir, 'index.m3u8')}")
    
    # Arquivo de concatenação
    concat_file = os.path.join(processed_dir, "concat.mp3")
    
    # Contador para nomes de arquivos
    counter = 0
    processed_files = set()
    
    logger.info(f"Iniciando loop de monitoramento em {audio_dir}")
    
    while True:
        try:
            # Lista todos os arquivos WAV no diretório
            files = [f for f in os.listdir(audio_dir) if f.endswith(".wav") and not f.startswith(".")]
            
            # Ordena os arquivos por nome
            files.sort()
            
            # Filtra arquivos não processados
            new_files = [f for f in files if f not in processed_files]
            
            if new_files:
                logger.info(f"Encontrados {len(new_files)} segmentos não processados")
                
                for file in new_files:
                    try:
                        # Caminho completo do arquivo
                        file_path = os.path.join(audio_dir, file)
                        
                        logger.info(f"Processando segmento: {file}")
                        
                        # Transcreve o áudio
                        text = transcribe_audio(whisper_model, file_path)
                        
                        # Traduz o texto
                        translated_text = translate_text(text, target_lang)
                        
                        # Sintetiza a fala
                        output_wav = os.path.join(processed_dir, f"dubbed_{counter}.wav")
                        if synthesize_speech(tts_model, translated_text, output_wav, target_lang):
                            
                            # Converte para MP3
                            output_mp3 = os.path.join(processed_dir, f"dubbed_{counter}.mp3")
                            if convert_to_mp3(output_wav, output_mp3):
                                
                                # Concatena ao arquivo contínuo
                                if concatenate_mp3(concat_file, output_mp3):
                                    
                                    # Gera streaming HLS
                                    generate_hls(concat_file, hls_dir)
                                    
                                    # Marca como processado
                                    processed_files.add(file)
                                    counter += 1
                    
                    except Exception as e:
                        logger.error(f"Erro ao processar {file}: {e}")
            
            # Aguarda antes da próxima verificação
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Erro no loop principal: {e}")
            time.sleep(5)  # Aguarda mais tempo em caso de erro

# Função para iniciar o worker como processo separado
def start_worker(audio_dir, target_lang):
    worker_loop(audio_dir, target_lang)

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        worker_loop(sys.argv[1], sys.argv[2])
    else:
        print("Uso: python worker.py <audio_dir> <target_lang>")
