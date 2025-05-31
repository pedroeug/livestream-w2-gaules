// livestream-w2-gaules/frontend/src/App.jsx

import React, { useState, useRef, useEffect } from 'react';
import Hls from 'hls.js';

const App = () => {
  const [channel, setChannel] = useState('gaules');
  const [lang, setLang] = useState('en');
  const videoRef = useRef(null);
  const hlsRef = useRef(null);

  // Função para iniciar o pipeline no backend
  const startPipeline = async () => {
    try {
      const url = `${window.location.origin}/start/${encodeURIComponent(channel)}/${encodeURIComponent(lang)}`;
      const res = await fetch(url, { method: 'POST' });  // ← aqui é crucial: método POST
      if (!res.ok) {
        console.error('Falha ao iniciar pipeline:', res.status, res.statusText);
      } else {
        console.log('Pipeline iniciado com sucesso para', channel, lang);
      }
    } catch (err) {
      console.error('Erro na chamada /start:', err);
    }
  };

  // Função para tentar carregar o HLS repetidamente até encontrar a playlist
  const attachHls = () => {
    const playlistUrl = `${window.location.origin}/hls/${encodeURIComponent(channel)}/${encodeURIComponent(lang)}/index.m3u8`;
    if (videoRef.current) {
      if (hlsRef.current) {
        hlsRef.current.destroy();
      }
      const hls = new Hls();
      hlsRef.current = hls;
      hls.loadSource(playlistUrl);
      hls.attachMedia(videoRef.current);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        console.log('HLS manifest carregado, iniciando playback');
        videoRef.current.play();
      });
      hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.type === Hls.ErrorTypes.NETWORK_ERROR && data.response && data.response.code === 404) {
          console.warn('Playlist não encontrada ainda, tentando novamente em 3s...');
          setTimeout(attachHls, 3000);
        } else {
          console.error('Erro HLS.js:', data);
        }
      });
    }
  };

  // Sempre que o usuário clicar em “Start” ou mudar canal/idioma, reiniciamos o processo
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.pause();
    }
    if (hlsRef.current) {
      hlsRef.current.destroy();
      hlsRef.current = null;
    }
    // Tenta iniciar novamente somente se já tivermos feito o POST
    // (pressionando o botão “Start Pipeline”)
  }, [channel, lang]);

  return (
    <div style={{ padding: '1rem', fontFamily: 'sans-serif' }}>
      <h1>LiveDub para Twitch</h1>

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

      <div style={{ marginBottom: '1rem' }}>
        <button
          onClick={() => {
            startPipeline().then(() => {
              // Depois que o POST retornar 200, começamos a checar o HLS
              attachHls();
            });
          }}
        >
          Iniciar Pipeline
        </button>
      </div>

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
