import { useState } from "react";
import Player from "./components/Player";

function App() {
  const [channel, setChannel] = useState("gaules");
  const [lang, setLang] = useState("en");
  const [started, setStarted] = useState(false);

  const startPipeline = async () => {
    try {
      // Chama o backend exatamente na mesma origem
      const resp = await fetch(`/start/${channel}/${lang}`, {
        method: "POST",
      });
      if (!resp.ok) {
        console.error("Falha ao iniciar pipeline:", await resp.text());
        return;
      }
      setStarted(true);
    } catch (err) {
      console.error("Erro ao chamar /start:", err);
    }
  };

  return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>LiveDub com Speechify SWS</h1>

      <div style={{ margin: "1rem 0" }}>
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
          style={{ marginLeft: "1.5rem", padding: "0.5rem 1rem" }}
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
