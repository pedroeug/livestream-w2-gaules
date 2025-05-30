# 🎙️ LiveDub: Dublagem Automática de Lives da Twitch com Delay

Este projeto oferece uma solução **completa e automatizada** para dublar transmissões ao vivo da **Twitch** em tempo real com um delay de ~30 segundos. A solução utiliza:

- 🎧 **Whisper** para transcrição do áudio
- 🌐 **DeepL** para tradução simultânea
- 🗣️ **ElevenLabs** para gerar a voz dublada
- 🔁 Segmentação em HLS (.m3u8) para streaming da dublagem
- ⚡ Backend com FastAPI
- 🖥️ Frontend com React

---

## 🚀 Como funciona

1. O usuário acessa a aplicação e insere o nome do canal da Twitch (ex: `gaules`) e o idioma desejado para ouvir.
2. O backend inicia a captura do stream original da Twitch.
3. A cada trecho de ~10 segundos:
   - O áudio é transcrito com **Whisper**
   - O texto é traduzido com **DeepL**
   - A voz dublada é gerada via **ElevenLabs**
   - Os trechos são convertidos em vídeo e montados como um HLS stream
4. Após 30 segundos, o usuário começa a assistir à live dublada via player HLS.

---

## 📦 Estrutura do Projeto

