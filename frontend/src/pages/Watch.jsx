import React, { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

function Watch() {
  const [searchParams] = useSearchParams()
  const channel = searchParams.get('channel')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 30000)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center">
      {loading ? (
        <p className="text-xl">Aguarde... sincronizando com a dublagem</p>
      ) : (
        <iframe
          src={`https://player.twitch.tv/?channel=${channel}&parent=livestream-w2-gaules.onrender.com&autoplay=true`}
          height="720"
          width="1280"
          allowFullScreen
        ></iframe>
      )}
    </div>
  )
}

export default Watch
