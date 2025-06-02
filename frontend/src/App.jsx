// livestream-w2-gaules/frontend/src/App.jsx

import React, { useRef, useEffect, useState } from "react";
import Hls from "hls.js";
import "./index.css"; // ajuste conforme o seu CSS

function App() {
  const videoRef = useRef(null);
  const [canPlay, setCanPlay] = useState(false);
  const [status, setStatus] = useState("Pronto para iniciar");
  const [channel, setChannel] = useState("gaules");
  const [lang, setLang] = useState("en");

  // Função para chamar o endpoint /start/{channel}/{lang}
  async function startPipeline() {
    try {
      setStatus("Iniciando pipeline...");
      const res = await fetch(
        `/start/${encodeURIComponent(channel)}/${encodeURIComponent(lang)}`,
        { method: "POST" }
      );
      if (!res.ok) throw new Error(`Erro ${res.status}`);
      setStatus("Pipeline iniciado! Carregando player...");
      setCanPlay(true);
    } catch (err) {
      console.error(err);
      setStatus(`Falha ao iniciar: ${err.message}`);
    }
  }

  // Quando canPlay virar true, anexamos o HLS ao <video>
  useEffect(() => {
    if (!canPlay) return;

    const video = videoRef.current;
    const hls = new Hls();
    const hlsUrl = `/hls/${channel}/${lang}/index.m3u8`; 
    // OBS: como o FastAPI está montando "/hls" em static,
    //      podemos usar caminho relativo. Em produção ficará:
    //      https://livestream-w2-gaules-v2.onrender.com/hls/gaules/en/index.m3u8

    // Se o browser suportar Hls.js, carregamos via Hls(); senão, tentamos atribuir direto na tag <video>
    if (Hls.isSupported()) {
      hls.loadSource(hlsUrl);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {});
      });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = hlsUrl;
      video.addEventListener("loadedmetadata", () => {
        video.play().catch(() => {});
      });
    } else {
      console.warn("Este navegador não suporta HLS diretamente.");
      setStatus("Navegador não suporta HLS.");
    }

    return () => {
      hls.destroy();
    };
  }, [canPlay, channel, lang]);

  return (
    <div style={{ padding: "1rem", fontFamily: "sans-serif" }}>
      <h1>LiveDub com Speechify</h1>

      <div style={{ marginBottom: "1rem" }}>
        <label>
          Canal Twitch:{" "}
          <input
            type="text"
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
            style={{ width: "200px", marginRight: "1rem" }}
          />
        </label>
        <label>
          Idioma de saída:{" "}
          <select
            value={lang}
            onChange={(e) => setLang(e.target.value)}
            style={{ marginRight: "1rem" }}
          >
            <option value="en">Inglês (en)</option>
            <option value="pt">Português (pt)</option>
            <option value="es">Espanhol (es)</option>
            {/* Adicione aqui outras opções se desejar */}
          </select>
        </label>
        <button onClick={startPipeline}>Iniciar Pipeline</button>
      </div>

      <p>Status: {status}</p>

      {canPlay && (
        <div>
          <video
            ref={videoRef}
            controls
            style={{
              width: "100%",
              maxWidth: "800px",
              border: "1px solid #ccc",
              borderRadius: "4px",
            }}
          />
        </div>
      )}
    </div>
  );
}

export default App;
