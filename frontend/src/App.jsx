// frontend/src/App.jsx

import { useState, useEffect, useRef } from "react";
import Player from "./components/Player";

function App() {
  const [channel, setChannel] = useState("gaules");
  const [lang, setLang] = useState("en");
  const [started, setStarted] = useState(false);
  const [logs, setLogs] = useState([] as string[]); // armazena cada linha de log
  const esRef = useRef<EventSource | null>(null);

  const startPipeline = async () => {
    try {
      // (1) dispara a rota que inicia o pipeline no backend
      await fetch(`/start/${channel}/${lang}`, { method: "POST" });
      setStarted(true);

      // (2) só cria um EventSource se ainda não existir
      if (!esRef.current) {
        const es = new EventSource("/logs/stream");  
        es.onmessage = (e) => {
          // cada e.data é uma linha de log completa
          setLogs((prev) => [...prev, e.data]);
        };
        es.onerror = () => {
          // opcional: fechar a conexão se der erro
          es.close();
        };
        esRef.current = es;
      }
    } catch (err) {
      console.error("Erro ao iniciar pipeline:", err);
    }
  };

  // fechar o EventSource ao desmontar o componente
  useEffect(() => {
    return () => {
      if (esRef.current) {
        esRef.current.close();
      }
    };
  }, []);

  return (
    <div className="App" style={{ padding: "1rem", fontFamily: "sans-serif" }}>
      <h1>LiveDub com Speechify SWS</h1>

      <div style={{ marginBottom: "1rem" }}>
        <label>
          Canal:&nbsp;
          <input
            type="text"
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
          />
        </label>
        <label style={{ marginLeft: "1.5rem" }}>
          Idioma:&nbsp;
          <select value={lang} onChange={(e) => setLang(e.target.value)}>
            <option value="en">Inglês</option>
            <option value="pt">Português</option>
            <option value="es">Espanhol</option>
          </select>
        </label>
        <button
          style={{ marginLeft: "1.5rem", padding: "0.4rem 0.8rem" }}
          onClick={startPipeline}
        >
          Iniciar Pipeline
        </button>
      </div>

      {started && (
        <>
          <div style={{ marginBottom: "1.5rem" }}>
            <h2>Player</h2>
            <Player
              src={`/hls/${channel}/${lang}/index.m3u8`}
              width="640"
              height="360"
            />
          </div>

          <div>
            <h2>Logs em tempo real</h2>
            <pre
              style={{
                background: "#1e1e1e",
                color: "#ddd",
                padding: "1rem",
                height: "200px",
                overflowY: "auto",
                borderRadius: "4px",
                fontSize: "0.85rem",
              }}
            >
              {logs.map((line, i) => (
                <div key={i}>{line}</div>
              ))}
            </pre>
          </div>
        </>
      )}
    </div>
  );
}

export default App;
