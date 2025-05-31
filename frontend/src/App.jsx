// livestream-w2-gaules/frontend/src/App.jsx

import React, { useState, useEffect, useRef } from 'react'
import Hls from 'hls.js'

export default function App() {
  const [channel, setChannel] = useState('gaules')
  const [lang, setLang] = useState('en')
  const [isProcessing, setIsProcessing] = useState(false)
  const videoRef = useRef(null)

  // Esta função dispara o pipeline no backend
  async function startPipeline(channelName, language) {
    try {
      setIsProcessing(true)
      // Envia um POST para /start/{channel}/{lang}
      const res = await fetch(
        `${window.location.origin}/start/${encodeURIComponent(channelName)}/${encodeURIComponent(language)}`,
        { method: 'POST' }
      )
      if (!res.ok) {
        console.error('Falha ao iniciar pipeline:', res.status, res.statusText)
      }
    } catch (err) {
      console.error('Erro na chamada /start:', err)
    } finally {
      // Após disparar, mantemos "processando" por causa do delay antes do HLS
      // (mas mesmo que falhe, tentamos carregar o HLS abaixo)
    }
  }

  // Sempre que canal ou idioma mudarem, disparamos o pipeline e depois inicializamos o HLS
  useEffect(() => {
    if (!videoRef.current) return

    // 1) Dispara o pipeline no backend
    startPipeline(channel, lang)

    // 2) Faz um pequeno delay antes de tentar inicializar o Hls.js
    //    para dar tempo do backend gerar o index.m3u8 + ts segments.
    //    Ajuste esse valor conforme a performance do seu pipeline (ex.: 10000 a 20000 ms).
    const DELAY_MS = 15000
    const timer = setTimeout(() => {
      const hlsUrl = `${window.location.origin}/hls/${encodeURIComponent(channel)}/${encodeURIComponent(lang)}/index.m3u8`

      if (Hls.isSupported()) {
        const hls = new Hls()
        hls.loadSource(hlsUrl)
        hls.attachMedia(videoRef.current)
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          videoRef.current.play().catch(() => {
            /* Sem problemas se autoplay falhar */
          })
        })
      } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
        videoRef.current.src = hlsUrl
      }
      setIsProcessing(false)
    }, DELAY_MS)

    // Se o usuário mudar canal/idioma antes do timer, limpa o timer antigo
    return () => clearTimeout(timer)
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
            onChange={e => setChannel(e.target.value.trim())}
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

      {isProcessing && (
        <div style={{ marginBottom: '1rem', color: '#555' }}>
          Iniciando pipeline e gerando HLS… aguarde alguns segundos antes de o vídeo aparecer.
        </div>
      )}

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
