import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'

function Home() {
  const [channelInput, setChannelInput] = useState('')
  const [lang, setLang] = useState('en')
  const navigate = useNavigate()

  const handleSubmit = (e) => {
    e.preventDefault()
    if (channelInput.trim()) {
      const name = channelInput.replace('https://www.twitch.tv/', '').replace(/\/.*/, '')
      navigate(`/watch?channel=${name}&lang=${lang}`)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 text-white">
      <form onSubmit={handleSubmit} className="space-y-4 text-center">
        <h1 className="text-3xl font-bold">Assistir com Dublagem</h1>
        <input
          className="px-4 py-2 rounded bg-gray-700 text-white"
          placeholder="Link ou nome do canal"
          value={channelInput}
          onChange={(e) => setChannelInput(e.target.value)}
        />
        <select
          className="px-4 py-2 rounded bg-gray-700 text-white"
          value={lang}
          onChange={(e) => setLang(e.target.value)}
        >
          <option value="en">Inglês</option>
          <option value="es">Espanhol</option>
          <option value="pt">Português</option>
        </select>
        <button
          type="submit"
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded"
        >
          Assistir
        </button>
      </form>
    </div>
  )
}

export default Home
