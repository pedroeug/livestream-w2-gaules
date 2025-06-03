// frontend/src/App.jsx
import { useState } from "react";
import Player from "./components/Player";

function App() {
  const [channel, setChannel] = useState("gaules");
  const [lang, setLang] = useState("en");
  const [started, setStarted] = useState(false);

  const startPipeline = async () => {
    try {
      const res = await fetch(`/start/${channel}/${lang}`, { method: "POST" });
      if (!res.ok) throw new Error(`Status ${res.status}`);
      setStarted(true);
    } catch (err) {
      console.error("Erro ao iniciar pipeline:", err);
    }
  };

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
        <label style={{ marginLeft: "1rem" }}>
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
          style={{ marginLeft: "1rem", padding: "0.4rem 0.8rem" }}
          onClick={startPipeline}
        >
          Iniciar Pipeline
        </button>
      </div>

      {started && (
        <div style={{ marginTop: "2rem" }}>
          <Player
            src={`/hls/${channel}/${lang}/index.m3u8`}
            width="640"
            height="360"
          />
        </div>
      )}
    </div>
  );
}

export default App;
