import { useState } from "react";

export default function App() {
  const [channel, setChannel] = useState("");
  const [started, setStarted] = useState(false);

  const start = async () => {
    await fetch("/api/start-dub", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel })
    });
    setStarted(true);
  };

  return (
    <div style={{ padding: 20, fontFamily: "sans-serif" }}>
      <h1>Livestream W2 – Twitch Dub (Gaules Voice Clone)</h1>
      {!started ? (
        <>
          <input
            placeholder="gaules"
            value={channel}
            onChange={e => setChannel(e.target.value)}
            style={{ padding: 8, width: 300 }}
          />
          <button onClick={start} style={{ marginLeft: 8, padding: "8px 16px" }}>
            Assistir com Dublagem
          </button>
        </>
      ) : (
        <video
          controls
          autoPlay
          style={{ marginTop: 20, maxWidth: 854, width: "100%" }}
          src={`/dub_hls/index.m3u8`}
        />
      )}
    </div>
  );
}