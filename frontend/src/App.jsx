// frontend/src/App.jsx

import { useState, useEffect, useRef } from "react";
import Player from "./components/Player";

function App() {
  const [channel, setChannel] = useState("gaules");
  const [lang, setLang] = useState("en");
  const [started, setStarted] = useState(false);
  const [logs, setLogs] = useState("");
  const eventSourceRef = useRef(null);

  const startPipeline = async () => {
    try {
      // 1) Envia POST /start/{channel}/{lang}
      await fetch(`/start/${channel}/${lang}`, { method: "POST" });
      setStarted(true);
    } catch (err) {
      console.error("Erro ao iniciar pipeline:", err);
    }
  };

  // 2) Quando “started” virar true, abre SSE em /logs/{channel}/{lang}
  useEffect(() => {
    if (started) {
      const es = new EventSource(`/logs/${channel}/${lang}`);
      eventSourceRef.current = es;

      es.onmessage = (e) => {
        // e.data contém uma linha de log nova
        setLogs((prev) => prev + e.data + "\n");
      };
      es.onerror = (e) => {
        console.error("Erro no EventSource:", e);
        // Se quiser, pode fechar após erro:
        // es.close();
      };

      return () => {
        // Ao desmontar, fecha a conexão SSE
        es.close();
      };
    }
  }, [started, channel, lang]);

  return (
    <div className="App" style={{ padding: "1rem", fontFamily: "sans-serif" }}>
      <h1>LiveDub com Speechify SWS</h1>
      <div style={{ marginBottom: "1rem" }}>
        <label>
          Canal:
          <input
            type="text"
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
            style={{ marginLeft: "0.5rem" }}
          />
        </label>
        <label style={{ marginLeft: "1.5rem" }}>
          Idioma:
          <select
            value={lang}
            onChange={(e) => setLang(e.target.value)}
            style={{ marginLeft: "0.5rem" }}
          >
            <option value="en">Inglês</option>
            <option value="pt">Português</option>
            <option value="es">Espanhol</option>
          </select>
        </label>
        <button
          onClick={startPipeline}
          style={{
            marginLeft: "1.5rem",
            padding: "0.5rem 1rem",
            fontSize: "1rem",
            cursor: "pointer",
          }}
        >
          Iniciar Pipeline
        </button>
      </div>

      {started && (
        <>
          <div style={{ display: "flex", gap: "2rem" }}>
            {/* 3) Player HLS fica à esquerda */}
            <div>
              <h2>Player</h2>
              <Player
                src={`/hls/${channel}/${lang}/index.m3u8`}
                width="640"
                height="360"
              />
            </div>

            {/* 4) Logs em tempo real à direita */}
            <div style={{ flex: 1 }}>
              <h2>Logs</h2>
              <pre
                style={{
                  background: "#111",
                  color: "#0f0",
                  padding: "1rem",
                  height: "360px",
                  overflowY: "auto",
                }}
              >
                {logs || "(aguardando registros...)"}
              </pre>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default App;
