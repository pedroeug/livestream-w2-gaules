import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  root: '.',                // procura por index.html aqui
  base: './',               // caminhos relativos para assets
  build: {
    outDir: 'dist',         // gera a pasta frontend/dist
    emptyOutDir: true       // limpa dist/ antes de cada build
  },
  plugins: [react()]
})
