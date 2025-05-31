# livestream-w2-gaules/pipeline/worker.py

import os
import time
import re
import whisper
from deep_translator import DeeplTranslator
import subprocess
import glob
import shutil
import traceback
import logging
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

# Configuração da chave DeepL
DEEPL_API_KEY = "6403a834-79ed-4d72-ac3e-079417477805:fx"
os.environ["DEEPL_API_KEY"] = DEEPL_API_KEY

def worker_loop(audio_dir: str, lang: str):
    """
    Loop contínuo que:
      1. Monitora novos arquivos .wav em audio_dir.
      2. Transcreve usando Whisper.
      3. Traduz a transcrição (DeepL).
      4. Síntese de voz (Coqui TTS).
      5. Empacota em HLS (.ts + index.m3u8) em hls/{channel}/{lang}/.
    """
    try:
        logger.info(f"Iniciando worker_loop para {audio_dir} e idioma {lang}")
        
        # Usar caminhos absolutos para evitar problemas de contexto
        audio_dir_abs = os.path.abspath(audio_dir)
        logger.info(f"Caminho absoluto para diretório de áudio: {audio_dir_abs}")
        
        if not os.path.exists(audio_dir_abs):
            logger.error(f"ERRO: Diretório {audio_dir_abs} não existe!")
            os.makedirs(audio_dir_abs, exist_ok=True)
            logger.info(f"Diretório {audio_dir_abs} criado")

        # Verificar permissões do diretório
        logger.info(f"Verificando permissões do diretório {audio_dir_abs}")
        try:
            test_file = os.path.join(audio_dir_abs, "test_permission.tmp")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            logger.info(f"Permissões de escrita OK para {audio_dir_abs}")
        except Exception as e:
            logger.error(f"ERRO de permissão no diretório {audio_dir_abs}: {e}")

        # Carrega o modelo Whisper
        logger.info("Carregando modelo Whisper...")
        model = whisper.load_model("base")
        logger.info("Modelo Whisper carregado com sucesso")

        # Carrega o modelo Coqui TTS
        logger.info("Carregando modelo Coqui TTS...")
        try:
            # Configura Coqui TTS:
            # Para inglês com clonagem de voz, usamos "tts_models/multilingual/multi-dataset/your_tts"
            # e passamos speaker_wav="assets/voices/gaules_sample.wav".
            tts_clone = TTS(
                model_name="tts_models/multilingual/multi-dataset/your_tts",
                progress_bar=False,
                gpu=False
            )
            speaker_wav = "assets/voices/gaules_sample.wav"
            if not os.path.isfile(speaker_wav):
                logger.warning(f"AVISO: speaker_wav não encontrado em {speaker_wav}. Voice‐cloning pode falhar.")
            else:
                logger.info(f"Arquivo de voz para clonagem encontrado: {speaker_wav}")
            
            logger.info("Modelo Coqui TTS carregado com sucesso")
        except Exception as e:
            logger.error(f"ERRO ao carregar modelo Coqui TTS: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return

        processed = set()
        
        # Padrão para identificar apenas segmentos originais (segment_XXX.wav)
        original_segment_pattern = re.compile(r'^segment_\d+\.wav$')
        
        # Configuração para o streaming contínuo
        channel = os.path.basename(audio_dir_abs)
        hls_dir = os.path.abspath(os.path.join("hls", channel, lang))
        logger.info(f"Diretório HLS: {hls_dir}")
        
        os.makedirs(hls_dir, exist_ok=True)
        
        # Diretório para armazenar os arquivos de áudio processados
        processed_dir = os.path.join(audio_dir_abs, "processed")
        os.makedirs(processed_dir, exist_ok=True)
        
        # Arquivo para concatenar todos os segmentos de áudio processados
        concat_file = os.path.join(processed_dir, "concat.mp3")
        
        # Inicializar o HLS
        initialize_hls(hls_dir)
        
        # Contador para segmentos HLS
        segment_counter = 0
        
        # Contador de falhas consecutivas
        consecutive_failures = 0
        
        logger.info(f"Iniciando loop de monitoramento em {audio_dir_abs}")
        
        while True:
            try:
                # Lista todos os arquivos .wav ainda não processados
                all_files = os.listdir(audio_dir_abs)
                wav_files = [f for f in all_files if f.endswith(".wav")]
                
                # Filtra apenas os segmentos originais usando regex
                original_segments = [f for f in wav_files if original_segment_pattern.match(f)]
                
                # Filtra os segmentos que ainda não foram processados
                unprocessed_segments = [f for f in original_segments if f not in processed]
                
                if unprocessed_segments:
                    logger.info(f"Encontrados {len(unprocessed_segments)} segmentos não processados")
                    
                    # Processa os segmentos em ordem
                    for filename in sorted(unprocessed_segments):
                        wav_path = os.path.join(audio_dir_abs, filename)
                        logger.info(f"Processando segmento: {filename}")
                        
                        try:
                            # Verificar tamanho do arquivo para evitar arquivos corrompidos
                            file_size = os.path.getsize(wav_path)
                            if file_size < 1000:  # Menos de 1KB provavelmente é um arquivo corrompido
                                logger.warning(f"Arquivo muito pequeno ({file_size} bytes), provavelmente corrompido. Pulando.")
                                processed.add(filename)
                                continue
                            
                            # 1) Transcrição com Whisper - forçando idioma português
                            logger.info(f"Transcrevendo {wav_path} com idioma forçado para português...")
                            
                            # Usar configurações mais robustas para evitar texto repetitivo
                            result = model.transcribe(
                                wav_path, 
                                language="pt", 
                                fp16=False,
                                temperature=0.0,  # Reduzir aleatoriedade
                                compression_ratio_threshold=2.0,  # Mais tolerante a repetições
                                no_speech_threshold=0.6  # Mais sensível a silêncio
                            )
                            
                            text = result["text"].strip()
                            
                            # Limitar texto repetitivo
                            if len(text) > 100 and (text.count(" o que é") > 5 or text.count(" que é o") > 5):
                                text = "Sem fala clara detectada neste segmento."
                                logger.warning(f"Texto repetitivo detectado, usando texto padrão")
                            
                            logger.info(f"Transcrição: {text}")
                            
                            # Se a transcrição estiver vazia, adicione um texto padrão
                            if not text:
                                text = "Sem fala detectada neste segmento."
                                logger.info(f"Transcrição vazia, usando texto padrão: {text}")
                            
                            # 2) Tradução com DeepL
                            translated = text
                            if text and text != "Sem fala detectada neste segmento.":
                                logger.info(f"Traduzindo para {lang} ...")
                                try:
                                    # Usar a chave DeepL fornecida
                                    translator = DeeplTranslator(source="pt", target=lang, api_key=DEEPL_API_KEY)
                                    translated = translator.translate(text)
                                    logger.info(f"Tradução: {translated}")
                                except Exception as e:
                                    logger.error(f"Erro na tradução DeepL: {e}")
                                    logger.info("Usando texto original como fallback")
                                    translated = text
                            else:
                                logger.info("Pulando tradução: texto vazio.")
                            
                            # 3) Síntese de voz com Coqui TTS
                            output_wav = os.path.join(processed_dir, f"dubbed_{segment_counter}.wav")
                            
                            try:
                                if translated and translated != "Sem fala detectada neste segmento.":
                                    logger.info(f"Sintetizando texto traduzido com Coqui TTS ...")
                                    
                                    if lang.lower() == "en":
                                        # Gera WAV clonando a voz usando o sample speaker_wav
                                        # Adicionando o parâmetro language explicitamente
                                        logger.info("Usando voice cloning para inglês")
                                        tts_clone.tts_to_file(
                                            text=translated,
                                            speaker_wav=speaker_wav,
                                            language=lang.lower(),  # Adicionado parâmetro language
                                            file_path=output_wav
                                        )
                                    else:
                                        # Gera WAV sem clonagem (modelo multilingual)
                                        # Adicionando o parâmetro language explicitamente
                                        logger.info(f"Usando modelo multilingual para {lang}")
                                        tts_clone.tts_to_file(
                                            text=translated,
                                            language=lang.lower(),  # Adicionado parâmetro language
                                            file_path=output_wav
                                        )
                                    
                                    logger.info(f"Áudio sintetizado salvo em {output_wav}")
                                else:
                                    # Fallback para síntese de voz local
                                    create_fallback_audio(output_wav, translated)
                            except Exception as e:
                                logger.error(f"Erro na síntese de voz: {e}")
                                logger.error(f"Traceback: {traceback.format_exc()}")
                                # Criar um arquivo de áudio vazio para manter o fluxo
                                create_fallback_audio(output_wav, translated)
                            
                            # 4) Converter o segmento para MP3
                            output_mp3 = os.path.join(processed_dir, f"dubbed_{segment_counter}.mp3")
                            logger.info(f"Convertendo WAV para MP3: {output_wav} -> {output_mp3}")
                            
                            try:
                                ffmpeg_cmd = [
                                    "ffmpeg", "-y",
                                    "-i", output_wav,
                                    "-c:a", "libmp3lame", 
                                    "-b:a", "128k",
                                    output_mp3
                                ]
                                result = subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
                                logger.info(f"Arquivo convertido para MP3: {output_mp3}")
                                
                                # 5) Adicionar ao arquivo de áudio contínuo
                                logger.info(f"Adicionando segmento ao arquivo contínuo: {concat_file}")
                                
                                if not os.path.exists(concat_file):
                                    # Se o arquivo não existir, apenas copie o primeiro segmento
                                    shutil.copy(output_mp3, concat_file)
                                    logger.info(f"Arquivo contínuo iniciado com {output_mp3}")
                                else:
                                    # Se já existir, concatene usando ffmpeg
                                    temp_file = concat_file + ".temp"
                                    concat_cmd = [
                                        "ffmpeg", "-y",
                                        "-i", "concat:" + concat_file + "|" + output_mp3,
                                        "-acodec", "copy",
                                        temp_file
                                    ]
                                    subprocess.run(concat_cmd, check=True, capture_output=True)
                                    
                                    # Substitui o arquivo original pelo temporário
                                    shutil.move(temp_file, concat_file)
                                    logger.info(f"Segmento {output_mp3} adicionado ao arquivo contínuo")
                                
                                # 6) Atualizar o HLS com o novo conteúdo
                                logger.info(f"Atualizando HLS com o arquivo contínuo: {concat_file}")
                                
                                # Padrão para os segmentos HLS
                                ts_pattern = os.path.join(hls_dir, "%03d.ts")
                                output_index = os.path.join(hls_dir, "index.m3u8")
                                
                                # Converte o arquivo MP3 para HLS
                                hls_cmd = [
                                    "ffmpeg", "-y",
                                    "-i", concat_file,
                                    "-c:a", "aac", 
                                    "-b:a", "128k",
                                    "-vn",
                                    "-hls_time", "10",
                                    "-hls_playlist_type", "event",
                                    "-hls_segment_filename", ts_pattern,
                                    output_index
                                ]
                                subprocess.run(hls_cmd, check=True, capture_output=True)
                                logger.info(f"HLS atualizado em {output_index}")
                                
                            except subprocess.CalledProcessError as e:
                                logger.error(f"Erro ao executar ffmpeg: {e}")
                                logger.error(f"Saída de erro: {e.stderr.decode() if e.stderr else 'Nenhuma'}")
                            except Exception as e:
                                logger.error(f"Erro ao processar áudio: {e}")
                                logger.error(f"Traceback: {traceback.format_exc()}")
                            
                            # Marcar como processado e incrementar contador
                            processed.add(filename)
                            segment_counter += 1
                            consecutive_failures = 0
                            
                        except Exception as e:
                            logger.error(f"Erro ao processar segmento {filename}: {e}")
                            logger.error(f"Traceback: {traceback.format_exc()}")
                            consecutive_failures += 1
                            
                            # Se houver muitas falhas consecutivas, pular este segmento
                            if consecutive_failures > 3:
                                logger.warning(f"Muitas falhas consecutivas, pulando segmento {filename}")
                                processed.add(filename)
                                consecutive_failures = 0
                
                # Aguardar um pouco antes de verificar novamente
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Erro no loop principal: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                time.sleep(5)  # Aguardar um pouco mais em caso de erro
    
    except Exception as e:
        logger.error(f"ERRO CRÍTICO no worker_loop: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")


def initialize_hls(hls_dir):
    """Inicializa o diretório HLS com um arquivo index.m3u8 vazio"""
    index_path = os.path.join(hls_dir, "index.m3u8")
    with open(index_path, "w") as f:
        f.write("#EXTM3U\n")
        f.write("#EXT-X-VERSION:3\n")
        f.write("#EXT-X-TARGETDURATION:10\n")
        f.write("#EXT-X-MEDIA-SEQUENCE:0\n")
        f.write("#EXT-X-PLAYLIST-TYPE:EVENT\n")
    logger.info(f"Arquivo HLS inicial criado em {index_path}")


def create_fallback_audio(output_path, text):
    """Cria um arquivo de áudio de fallback usando ffmpeg"""
    logger.info(f"Criando áudio de fallback para: {text}")
    
    # Criar arquivo de texto temporário
    temp_dir = os.path.dirname(output_path)
    temp_txt = os.path.join(temp_dir, "temp_text.txt")
    with open(temp_txt, "w") as f:
        f.write(text if text else "No speech detected")
    
    # Gerar áudio com ffmpeg
    try:
        # Usar uma duração proporcional ao tamanho do texto
        duration = max(3, min(10, len(text) / 20))
        
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", 
            "-i", f"sine=frequency=440:duration={duration}",
            "-c:a", "pcm_s16le",
            "-ar", "48000",
            "-ac", "2",
            output_path
        ]
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        logger.info(f"Áudio de fallback gerado em {output_path}")
    except Exception as e:
        logger.error(f"Erro ao criar áudio de fallback: {e}")
        # Criar um arquivo de áudio vazio como último recurso
        try:
            ffmpeg_empty_cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", 
                "-i", "anullsrc=r=48000:cl=stereo:d=3",
                "-c:a", "pcm_s16le",
                output_path
            ]
            subprocess.run(ffmpeg_empty_cmd, check=True, capture_output=True)
            logger.info(f"Áudio vazio gerado em {output_path}")
        except Exception as e2:
            logger.error(f"Erro ao criar áudio vazio: {e2}")
    
    # Limpar arquivo temporário
    if os.path.exists(temp_txt):
        os.remove(temp_txt)
