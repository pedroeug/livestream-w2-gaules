// livestream-w2-gaules/frontend/src/App.jsx

import { useState } from "react";

function App() {
  const [running, setRunning] = useState(false);
  const channel = "gaules";
  const lang = "en";

  async function startPipeline(channel, lang) {
    try {
      const res = await fetch(`/start/${channel}/${lang}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error(`Erro ${res.status}`);
      const data = await res.json();
      console.log("Pipeline iniciado:", data);
      setRunning(true);
    } catch (err) {
      console.error("Falha ao iniciar pipeline:", err);
    }
  }

  return (
    <div className="App">
      <h1>LiveDub com Speechify SWS</h1>
      <button
        onClick={() => startPipeline(channel, lang)}
        disabled={running}
      >
        {running ? "Pipeline Rodando…" : "Iniciar Pipeline"}
      </button>

      {running && (
        <div style={{ marginTop: "1rem" }}>
          <p>Para assistir, abra:</p>
          <code>
            {`${window.location.origin}/hls/${channel}/${lang}/index.m3u8`}
          </code>
        </div>
      )}
    </div>
  );
}

export default App;
