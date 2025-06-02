// livestream-w2-gaules/frontend/src/App.jsx

import React, { useRef, useEffect, useState } from "react";
import "./index.css"; // seu CSS global, se houver

function App() {
  const [status, setStatus] = useState("Pronto para iniciar");
  const [channel, setChannel] = useState("gaules");
  const [lang, setLang] = useState("en");
  const [canPlayAudio, setCanPlayAudio] = useState(false);
  const audioRef = useRef(null);

  // Chama POST /start/{channel}/{lang}
  async function startPipeline() {
    try {
      setStatus("Iniciando pipeline...");
      const res = await fetch(
        `/start/${encodeURIComponent(channel)}/${encodeURIComponent(lang)}`,
        { method: "POST" }
      );
      if (!res.ok) throw new Error(`Erro ${res.status}`);
      setStatus("Pipeline iniciado! Aguardando áudio...");
      setCanPlayAudio(true);
      // O <audio> estará visível e irá tentar tocar
    } catch (err) {
      console.error(err);
      setStatus(`Falha ao iniciar: ${err.message}`);
    }
  }

  // Sempre que canPlayAudio == true, tentamos tocar
  useEffect(() => {
    if (!canPlayAudio) return;
    const audioEl = audioRef.current;
    // Garante que o audio tente tocar (sem auto-play falhando):
    audioEl
      .play()
      .then(() => {
        // Conseguiu iniciar o áudio (mesmo que ainda vazio)
      })
      .catch(() => {
        // Se não conseguir (bloqueio de autoplay), o usuário
        // pode clicar no próprio controle do <audio> para liberar.
      });
  }, [canPlayAudio]);

  // Monta a URL do arquivo MP3 concat
  const audioUrl = `/audio_segments/${channel}/processed/concat.mp3`;

  return (
    <div style={{ padding: 20, fontFamily: "sans-serif" }}>
      <h1>LiveDub com Speechify SWS</h1>

      <div style={{ marginBottom: "1rem" }}>
        <label>
          Canal Twitch:{" "}
          <input
            type="text"
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
            style={{ width: 200, marginRight: 20 }}
          />
        </label>

        <label>
          Idioma de saída:{" "}
          <select
            value={lang}
            onChange={(e) => setLang(e.target.value)}
            style={{ marginRight: 20 }}
          >
            <option value="en">Inglês (en)</option>
            <option value="pt">Português (pt)</option>
            <option value="es">Espanhol (es)</option>
            {/* Adicione mais se desejar */}
          </select>
        </label>

        <button onClick={startPipeline}>Iniciar Pipeline</button>
      </div>

      <p>Status: {status}</p>

      {canPlayAudio && (
        <div style={{ marginTop: 20 }}>
          <audio
            ref={audioRef}
            controls
            src={audioUrl}
            style={{ width: "100%", maxWidth: 600 }}
          >
            Seu navegador não suporta elemento de áudio.
          </audio>
          <p style={{ fontSize: 12, color: "#555" }}>
            * o áudio tocará assim que o arquivo concat.mp3 for criado pelo backend e for preenchido pelo worker.
          </p>
        </div>
      )}
    </div>
  );
}

export default App;
