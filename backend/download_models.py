# livestream-w2-gaules/backend/download_models.py

"""
Este script garante que os modelos necessários para transcrição (Whisper) sejam baixados 
antes de o backend iniciar. Basta importar e executar a função download_all_models() no começo de main.py.
"""

import whisper

def download_all_models():
    """
    Carrega (e portanto baixa) o modelo Whisper “base” para transcrição.
    """
    try:
        whisper.load_model("base")
        print("Modelo Whisper 'base' baixado/com cache verificado com sucesso.")
    except Exception as e:
        print(f"Falha ao baixar/verificar o modelo Whisper: {e}")
