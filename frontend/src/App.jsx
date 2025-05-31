// livestream-w2-gaules/frontend/src/App.jsx

import React, { useState, useRef, useEffect } from 'react';
import Hls from 'hls.js';

const App = () => {
  // 1. Estados para canal e idioma
  const [channel, setChannel] = useState('gaules');
  const [lang, setLang] = useState('en');

  // 2. Referências para o <video> e para o objeto Hls.js
  const videoRef = useRef(null);
  const hlsRef = useRef(null);

  /**
   * Dispara o POST /start/{channel}/{lang} no backend
   */
  const startPipeline = async () => {
    try {
      const url = `${window.location.origin}/start/${encodeURIComponent(channel)}/${encodeURIComponent(lang)}`;
      const res = await fetch(url, { method: 'POST' }); // ⬅️ Método POST obrigatório!
      if (!res.ok) {
        console.error('Falha ao iniciar pipeline:', res.status, res.statusText);
      } else {
        console.log('Pipeline iniciado com sucesso para', channel, lang);
      }
    } catch (err) {
      console.error('Erro na chamada /start:', err);
    }
  };

  /**
   * Tenta carregar a playlist HLS repetidas vezes até existir
   */
  const attachHls = () => {
    const playlistUrl = `${window.location.origin}/hls/${encodeURIComponent(channel)}/${encodeURIComponent(lang)}/index.m3u8`;

    if (videoRef.current) {
      // Se já existe um Hls.js em execução, destruímos antes de recriar
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }

      const hls = new Hls();
      hlsRef.current = hls;
      hls.loadSource(playlistUrl);
      hls.attachMedia(videoRef.current);

      // Quando o manifest HLS for carregado, iniciamos o playback
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        console.log('HLS manifest carregado, iniciando playback');
        videoRef.current.play();
      });

      // Se der 404, aguardamos 3s e tentamos novamente
      hls.on(Hls.Events.ERROR, (event, data) => {
        if (
          data.type === Hls.ErrorTypes.NETWORK_ERROR &&
          data.response &&
          data.response.code === 404
        ) {
          console.warn('Playlist não encontrada ainda, tentando novamente em 3s...');
          setTimeout(attachHls, 3000);
        } else {
          console.error('Erro HLS.js:', data);
        }
      });
    }
  };

  // Sempre que o canal ou idioma mudar, pausamos o vídeo e destruímos o Hls.js anterior
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.pause();
    }
    if (hlsRef.current) {
      hlsRef.current.destroy();
      hlsRef.current = null;
    }
  }, [channel, lang]);

  return (
    <div style={{ padding: '1rem', fontFamily: 'sans-serif' }}>
      <h1>LiveDub para Twitch</h1>

      {/* 1) Input para nome do canal */}
      <div style={{ marginBottom: '1rem' }}>
        <label>
          Canal Twitch:{' '}
          <input
            type="text"
            value={channel}
            onChange={(e) => setChannel(e.target.value.trim())}
            placeholder="Digite o nome do canal"
          />
        </label>
      </div>

      {/* 2) Select para idioma de saída */}
      <div style={{ marginBottom: '1rem' }}>
        <label>
          Idioma de saída:{' '}
          <select value={lang} onChange={(e) => setLang(e.target.value)}>
            <option value="en">Inglês (en)</option>
            <option value="pt">Português (pt)</option>
            <option value="es">Espanhol (es)</option>
          </select>
        </label>
      </div>

      {/* 3) Botão para iniciar o pipeline */}
      <div style={{ marginBottom: '1rem' }}>
        <button
          onClick={() => {
            // 1º dispara o POST /start
            startPipeline().then(() => {
              // 2º, assim que a resposta 200 chegar, começamos a checar o HLS
              attachHls();
            });
          }}
        >
          Iniciar Pipeline
        </button>
      </div>

      {/* 4) Vídeo onde o HLS será anexado */}
      <div>
        <video
          ref={videoRef}
          controls
          style={{ width: '100%', maxWidth: '800px', border: '1px solid #ccc' }}
        />
      </div>
    </div>
  );
};

export default App;
