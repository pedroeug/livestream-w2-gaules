import { useState } from "react";

function App() {
  const [channel, setChannel] = useState("");
  const [language, setLanguage] = useState("EN");
  const [started, setStarted] = useState(false);

  const start = async () => {
    await fetch("/api/start-dub", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel, target_lang: language })
    });
    setStarted(true);
  };

  return (
    <div style={{ padding: 20, fontFamily: "sans-serif" }}>
      <h1>Livestream W2 – Twitch Dub (Escolha de Idioma)</h1>

      {!started ? (
        <>
          <div style={{ marginBottom: 10 }}>
            <input
              placeholder="Canal da Twitch (ex: gaules)"
              value={channel}
              onChange={e => setChannel(e.target.value)}
              style={{ padding: 8, width: 300 }}
            />
          </div>

          <div style={{ marginBottom: 10 }}>
            <label>
              Idioma de saída:
              <select
                value={language}
                onChange={e => setLanguage(e.target.value)}
                style={{ marginLeft: 8, padding: 4 }}
              >
                <option value="EN">Inglês</option>
                <option value="ES">Espanhol</option>
                <option value="FR">Francês</option>
                <option value="DE">Alemão</option>
                {/* Adicione mais códigos DeepL se quiser */}
              </select>
            </label>
          </div>

          <button onClick={start} style={{ padding: "8px 16px" }}>
            Assistir com Dublagem
          </button>
        </>
      ) : (
        <div style={{ marginTop: 20 }}>
          <video
            controls
            autoPlay
            style={{ maxWidth: 854, width: "100%" }}
            src="/dub_hls/index.m3u8"
          />
        </div>
      )}
    </div>
  );
}

export default App;
