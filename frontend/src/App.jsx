import React, { useState, useEffect, useRef } from 'react'
import Hls from 'hls.js'

export default function App() {
  const [channel, setChannel] = useState('gaules')
  const [lang, setLang] = useState('en')
  const videoRef = useRef(null)

  // Quando channel/lang mudarem, inicia/atualiza o player HLS
  useEffect(() => {
    if (!videoRef.current) return

    // URL do HLS gerado pelo backend (supondo que o backend disponibilize /frontend/dist/index.html chama o player)
    const hlsUrl = `${window.location.origin}/hls/${channel}/${lang}/index.m3u8`

    if (Hls.isSupported()) {
      const hls = new Hls()
      hls.loadSource(hlsUrl)
      hls.attachMedia(videoRef.current)
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        videoRef.current.play()
      })
    } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
      videoRef.current.src = hlsUrl
    }
  }, [channel, lang])

  return (
    <div style={{ padding: '1rem', fontFamily: 'Arial, sans-serif' }}>
      <h1>LiveDub – Twitch Dubbing</h1>

      <div style={{ marginBottom: '1rem' }}>
        <label>
          Canal Twitch:{' '}
          <input
            type="text"
            value={channel}
            onChange={e => setChannel(e.target.value)}
            placeholder="gaules"
            style={{ marginRight: '1rem' }}
          />
        </label>
        <label>
          Idioma:{' '}
          <select value={lang} onChange={e => setLang(e.target.value)}>
            <option value="en">Inglês</option>
            <option value="pt">Português</option>
            <option value="es">Espanhol</option>
          </select>
        </label>
      </div>

      <video
        ref={videoRef}
        controls
        style={{
          width: '100%',
          maxWidth: '720px',
          border: '1px solid #ccc',
          borderRadius: '8px',
        }}
      >
        Seu navegador não suporta vídeo HLS.
      </video>
    </div>
  )
}
