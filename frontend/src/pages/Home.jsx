import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'

function Home() {
  const [channel, setChannel] = useState('')
  const navigate = useNavigate()

  const handleSubmit = (e) => {
    e.preventDefault()
    if (channel.trim()) {
      navigate(`/watch?channel=${channel}`)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 text-white">
      <form onSubmit={handleSubmit} className="space-y-4 text-center">
        <h1 className="text-3xl font-bold">Assistir com Dublagem</h1>
        <input
          className="px-4 py-2 rounded bg-gray-700 text-white"
          placeholder="Digite o canal (ex: gaules)"
          value={channel}
          onChange={(e) => setChannel(e.target.value)}
        />
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
