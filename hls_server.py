#!/usr/bin/env python3
"""
Servidor HTTP simples e dedicado para servir arquivos HLS
"""

import os
import sys
import http.server
import socketserver
from urllib.parse import urlparse, unquote

PORT = 8001
DIRECTORY = os.path.join(os.getcwd(), "hls")

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Manipulador HTTP com suporte a CORS para servir arquivos HLS"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def do_GET(self):
        """Adiciona cabeçalhos CORS e serve o arquivo solicitado"""
        print(f"Requisição recebida: {self.path}")
        
        # Adiciona cabeçalhos CORS
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        
        # Define o tipo de conteúdo com base na extensão do arquivo
        if self.path.endswith('.m3u8'):
            self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
        elif self.path.endswith('.ts'):
            self.send_header('Content-Type', 'video/mp2t')
        else:
            self.send_header('Content-Type', 'application/octet-stream')
        
        # Finaliza os cabeçalhos e serve o arquivo
        self.end_headers()
        
        # Caminho do arquivo solicitado
        parsed_path = urlparse(self.path)
        file_path = unquote(parsed_path.path.lstrip('/'))
        
        try:
            with open(os.path.join(DIRECTORY, file_path), 'rb') as file:
                self.wfile.write(file.read())
            print(f"Arquivo servido com sucesso: {file_path}")
        except FileNotFoundError:
            print(f"Arquivo não encontrado: {file_path}")
            self.send_error(404, "File not found")
        except Exception as e:
            print(f"Erro ao servir arquivo: {e}")
            self.send_error(500, str(e))
    
    def do_OPTIONS(self):
        """Responde a requisições OPTIONS para suporte a CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def run_server():
    """Inicia o servidor HTTP"""
    # Garante que o diretório HLS existe
    os.makedirs(DIRECTORY, exist_ok=True)
    
    # Configura e inicia o servidor
    handler = CORSHTTPRequestHandler
    httpd = socketserver.TCPServer(("", PORT), handler)
    
    print(f"Servidor HLS iniciado na porta {PORT}")
    print(f"Servindo arquivos do diretório: {DIRECTORY}")
    print(f"URL de acesso: http://localhost:{PORT}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Servidor encerrado pelo usuário")
    finally:
        httpd.server_close()
        print("Servidor encerrado")

if __name__ == "__main__":
    run_server()
