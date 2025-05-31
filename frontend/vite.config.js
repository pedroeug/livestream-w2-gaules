import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Configuração básica para um projeto React + Vite
export default defineConfig({
  root: '.',                // A raiz do projeto Vite é esta pasta (onde está index.html)
  base: './',               // Caminho relativo para assets
  build: {
    outDir: 'dist',         // Saída padrão: frontend/dist
    emptyOutDir: true       // Esvazia pasta dist antes de reconstruir
  },
  plugins: [react()]
})
