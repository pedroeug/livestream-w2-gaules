# download_models.py

"""
Este script garante que os modelos necessários para transcrição (Whisper) e TTS (ElevenLabs, se for o caso) sejam baixados 
antes de o backend iniciar. Basta importar e executar a função download_all_models() no começo do main.py.

No nosso caso, usamos o Whisper do OpenAI, que baixa o modelo automaticamente na primeira chamada a whisper.load_model().
Aqui escolhemos o tamanho “base” como exemplo, mas você pode ajustar para “small”, “medium” ou “large” conforme desejar.
"""

import whisper

def download_all_models():
    """
    Carrega (e portanto baixa) o modelo Whisper “base” para transcrição.
    Se precisar de outros modelos (por exemplo, de ElevenLabs ou de tradução offline),
    adicione aqui as respectivas chamadas de download.
    """
    try:
        # Ao chamar load_model, o Whisper faz o download local automático.
        whisper.load_model("base")
        print("Modelo Whisper 'base' baixado/com cache verificado com sucesso.")
    except Exception as e:
        print(f"Falha ao baixar/verificar o modelo Whisper: {e}")

# Se alguém executar este script diretamente, executamos o download para "pré-aquecer" o container.
if __name__ == "__main__":
    download_all_models()
