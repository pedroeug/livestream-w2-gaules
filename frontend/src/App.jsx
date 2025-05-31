// livestream-w2-gaules/frontend/src/App.jsx

import React, { useState } from "react";

function App() {
  const [channel, setChannel] = useState("gaules");
  const [lang, setLang] = useState("en");
  const [status, setStatus] = useState("");

  const startPipeline = async () => {
    try {
      const resp = await fetch(`/start/${channel}/${lang}`, {
        method: "POST",
      });
      const data = await resp.json();
      if (resp.ok) {
        setStatus(`Pipeline iniciado: canal=${data.channel}, lang=${data.lang}`);
      } else {
        setStatus(`Erro ao iniciar: ${data.detail || resp.statusText}`);
      }
    } catch (err) {
      setStatus("Erro de rede ao iniciar pipeline.");
    }
  };

  return (
    <div style={{ padding: 20 }}>
      <h1>LiveDub</h1>
      <label>
        Canal:
        <input
          type="text"
          value={channel}
          onChange={(e) => setChannel(e.target.value)}
        />
      </label>
      <br />
      <label>
        Idioma:
        <select value={lang} onChange={(e) => setLang(e.target.value)}>
          <option value="en">English</option>
          <option value="pt">Português</option>
          <option value="es">Español</option>
        </select>
      </label>
      <br />
      <button onClick={startPipeline}>Iniciar Pipeline</button>
      <p>{status}</p>

      <video
        id="player"
        controls
        style={{ width: "100%", maxWidth: 800, marginTop: 20 }}
      >
        <source
          src={`/hls/${channel}/${lang}/index.m3u8`}
          type="application/vnd.apple.mpegurl"
        />
      </video>
    </div>
  );
}

export default App;
