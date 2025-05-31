import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
// Configuração simplificada para build de produção.
// As configurações de 'server' e 'preview' (incluindo allowedHosts)
// geralmente não são necessárias quando se faz o build para arquivos estáticos
// e se usa um servidor web/plataforma como o Render para servir a pasta 'dist'.
export default defineConfig({
  root: '.',                // Procura por index.html aqui
  base: './',               // Caminhos relativos para assets
  build: {
    outDir: 'dist',         // Gera a pasta frontend/dist
    emptyOutDir: true       // Limpa dist/ antes de cada build
  },
  plugins: [react()]
  // Removidas as seções 'server' e 'preview' que continham 'allowedHosts',
  // pois não são relevantes para o build de produção estático.
  // Se precisar rodar 'npm run preview' especificamente no Render,
  // adicione a seção 'preview' de volta com o host do Render em 'allowedHosts'.
})

