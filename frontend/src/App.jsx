// livestream-w2-gaules/frontend/src/App.jsx

import { useState, useEffect, useRef } from "react";
import "./App.css"; // Seu CSS habitual, se existir

function App() {
  const [channel, setChannel] = useState("gaules");
  const [lang, setLang] = useState("en");
  const [status, setStatus] = useState("idle"); // "idle" | "starting" | "waiting" | "ready" | "error"
  const [hlsUrl, setHlsUrl] = useState(null);

  // Controle de polling
  const pollingRef = useRef(null);

  // Função que pergunta ao backend para iniciar o pipeline
  async function startPipeline() {
    setStatus("starting");
    setHlsUrl(null);

    try {
      const resp = await fetch(`/start/${channel}/${lang}`, {
        method: "POST",
      });

      if (!resp.ok) {
        throw new Error(`Erro ao iniciar: ${resp.status}`);
      }

      // Pipeline iniciado com sucesso, agora começamos a “esperar” pelo HLS
      setStatus("waiting");
      pollForHls();
    } catch (err) {
      console.error(err);
      setStatus("error");
    }
  }

  // Função que faz o polling periódico
  async function pollForHls() {
    // URL que queremos verificar
    const url = `/hls/${channel}/${lang}/index.m3u8`;

    // Função interna que checa uma vez
    async function checkOnce() {
      try {
        // Faz um HEAD para ver se o arquivo já existe
        const resp = await fetch(url, { method: "HEAD" });
        if (resp.ok) {
          // Encontrou HLS → alteramos o estado para “ready”
          setHlsUrl(url);
          setStatus("ready");
          // Para o polling
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
        // se status não for 200, continua esperando
      } catch (e) {
        // provavelmente 404 ou erro de rede, ignora e tenta de novo
        console.debug("Ainda não disponível:", url);
      }
    }

    // Checa imediatamente e depois a cada 3 s
    checkOnce();
    pollingRef.current = setInterval(checkOnce, 3000);
  }

  // Caso o usuário mude canal/lang no meio do polling, limpamos o intervalo
  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, []);

  return (
    <div className="App" style={{ padding: 20 }}>
      <h1>LiveDub com Speechify SWS</h1>

      <div style={{ marginBottom: 20 }}>
        <label>
          Canal Twitch:&nbsp;
          <input
            type="text"
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
            style={{ width: 200 }}
          />
        </label>
        &nbsp;&nbsp;
        <label>
          Idioma (lang code):&nbsp;
          <select value={lang} onChange={(e) => setLang(e.target.value)}>
            <option value="en">en</option>
            <option value="pt">pt</option>
            <option value="es">es</option>
            {/* Adicione outras opções se quiser */}
          </select>
        </label>
        &nbsp;&nbsp;
        <button
          onClick={startPipeline}
          disabled={status === "starting" || status === "waiting"}
        >
          {status === "idle" && "Iniciar Pipeline"}
          {status === "starting" && "Iniciando..."}
          {status === "waiting" && "Aguardando HLS..."}
        </button>
      </div>

      {status === "error" && (
        <div style={{ color: "red" }}>
          Ocorreu um erro ao iniciar o pipeline.
        </div>
      )}

      {status === "waiting" && (
        <div style={{ color: "#555" }}>Pipeline iniciado. Aguardando HLS...</div>
      )}

      {status === "ready" && hlsUrl && (
        <div>
          <h2>Player HLS Pronto:</h2>
          <video
            style={{ width: "100%", maxWidth: 640 }}
            controls
            autoPlay
            src={hlsUrl}
          >
            Seu navegador não suporta vídeo HTML5.
          </video>
        </div>
      )}
    </div>
  );
}

export default App;
