// livestream-w2-gaules/frontend/src/App.jsx

import React, { useState, useEffect } from "react";
import Hls from "hls.js";

// Para deploy no Render.com (ou similar) onde frontend e backend
// são servidos sob o mesmo domínio, usamos URLs relativas.
// O servidor/proxy reverso configurado no Render deve rotear
// /start/* e /hls/* para o backend FastAPI.

function App() {
  const [channel, setChannel] = useState("gaules");
  const [lang, setLang] = useState("en");
  const [status, setStatus] = useState("");
  const [hlsUrl, setHlsUrl] = useState("");
  const videoRef = React.useRef(null);

  const startPipeline = async () => {
    setStatus("Iniciando pipeline...");
    try {
      // Usar URL relativa para o backend
      const resp = await fetch(`/start/${channel}/${lang}`, {
        method: "POST",
      });
      const data = await resp.json();
      if (resp.ok) {
        setStatus(`Pipeline iniciado: canal=${data.channel}, lang=${data.lang}. Aguardando HLS...`);
        // Atualizar a URL do HLS para o player usando URL relativa
        // O servidor deve servir o HLS a partir desta rota
        setHlsUrl(`/hls/${channel}/${lang}/index.m3u8`);
      } else {
        setStatus(`Erro ao iniciar: ${data.detail || resp.statusText}`);
        setHlsUrl(""); // Limpar URL em caso de erro
      }
    } catch (err) {
      console.error("Erro de rede:", err);
      setStatus("Erro de rede ao iniciar pipeline. Verifique a configuração do servidor/proxy e se o backend está respondendo.");
      setHlsUrl(""); // Limpar URL em caso de erro
    }
  };

  useEffect(() => {
    if (hlsUrl && Hls.isSupported() && videoRef.current) {
      const hls = new Hls();
      hls.loadSource(hlsUrl); // Carrega a URL relativa
      hls.attachMedia(videoRef.current);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        videoRef.current.play().catch(e => console.error("Erro ao tentar tocar o vídeo:", e));
        setStatus("Stream HLS carregado e pronto.");
      });
      hls.on(Hls.Events.ERROR, (event, data) => {
        console.error("Erro no HLS.js:", data);
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              setStatus(`Erro de rede ao carregar o stream HLS (${data.details}). Verifique o caminho do HLS e a configuração do servidor.`);
              // Não tentar reconectar automaticamente em caso de erro 404 ou similar
              if (data.details === 'manifestLoadError' || data.details === 'manifestParsingError') {
                 // Poderia tentar recarregar após um tempo, mas é melhor verificar a causa raiz
                 console.log("Manifest HLS não encontrado ou inválido.");
              } else {
                 // hls.startLoad(); // Tentativa genérica pode causar loops
              }
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              setStatus(`Erro de mídia no stream HLS (${data.details}). Tentando recuperar...`);
              hls.recoverMediaError();
              break;
            default:
              setStatus(`Erro fatal não recuperável no HLS (${data.type}).`);
              hls.destroy();
              break;
          }
        }
      });
      return () => {
        hls.destroy();
      };
    } else if (hlsUrl && videoRef.current && videoRef.current.canPlayType("application/vnd.apple.mpegurl")) {
      // Fallback para navegadores com suporte nativo (ex: Safari)
      videoRef.current.src = hlsUrl; // Usa a URL relativa
      videoRef.current.addEventListener("loadedmetadata", () => {
        videoRef.current.play().catch(e => console.error("Erro ao tentar tocar o vídeo (nativo):", e));
        setStatus("Stream HLS carregado (nativo).");
      });
       videoRef.current.addEventListener("error", (e) => {
         console.error("Erro no player de vídeo nativo:", e);
         setStatus("Erro ao carregar o stream HLS (nativo).");
       });
    }
  }, [hlsUrl]); // Re-executar quando hlsUrl mudar

  return (
    <div style={{ padding: 20 }}>
      <h1>LiveDub – Twitch Dubbing</h1>
      <div>
        <label style={{ marginRight: 10 }}>
          Canal:
          <input
            type="text"
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
            style={{ marginLeft: 5 }}
          />
        </label>
        <label style={{ marginRight: 10 }}>
          Idioma:
          <select value={lang} onChange={(e) => setLang(e.target.value)} style={{ marginLeft: 5 }}>
            <option value="en">English</option>
            <option value="pt">Português</option>
            <option value="es">Español</option>
          </select>
        </label>
        <button onClick={startPipeline}>Iniciar Pipeline</button>
      </div>
      <p>{status}</p>

      <video
        ref={videoRef}
        id="player"
        controls
        style={{ width: "100%", maxWidth: 800, marginTop: 20, backgroundColor: "#333" }}
      >
        {/* A source tag é gerenciada pelo Hls.js ou pelo src nativo */}
        Seu navegador não suporta o elemento de vídeo.
      </video>
    </div>
  );
}

export default App;

