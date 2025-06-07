import React, { useEffect, useRef, useState } from 'react';
import Hls from 'hls.js';

function Watch() {
  const videoRef = useRef(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [channel, setChannel] = useState('gaules');
  const [lang, setLang] = useState('en');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const paramChannel = params.get('channel');
    const paramLang = params.get('lang');

    if (paramChannel && paramChannel !== channel) setChannel(paramChannel);
    if (paramLang && paramLang !== lang) setLang(paramLang);

    const currentChannel = paramChannel || channel;
    const currentLang = paramLang || lang;

    // URL HLS gerado pelo backend na mesma porta
    const hlsUrl = `/hls/${currentChannel}/${currentLang}/index.m3u8`;
    
    const loadHls = () => {
      if (Hls.isSupported()) {
        const hls = new Hls({
          debug: true,
          enableWorker: true,
          lowLatencyMode: true,
          backBufferLength: 90
        });
        
        hls.on(Hls.Events.MEDIA_ATTACHED, () => {
          console.log('HLS.js vinculado ao elemento de áudio');
        });
        
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          console.log('HLS manifest carregado, iniciando playback');
          videoRef.current.play().catch(e => {
            console.log('Erro ao iniciar playback automático:', e);
          });
          setLoading(false);
        });
        
        hls.on(Hls.Events.ERROR, (event, data) => {
          console.log('Erro HLS.js:', data);
          if (data.fatal) {
            switch(data.type) {
              case Hls.ErrorTypes.NETWORK_ERROR:
                console.log('Erro de rede, tentando reconectar...');
                hls.startLoad();
                break;
              case Hls.ErrorTypes.MEDIA_ERROR:
                console.log('Erro de mídia, tentando recuperar...');
                hls.recoverMediaError();
                break;
              default:
                console.log('Erro fatal, não é possível recuperar');
                hls.destroy();
                setError('Erro ao carregar o stream. Por favor, tente novamente mais tarde.');
                break;
            }
          }
        });
        
        hls.loadSource(hlsUrl);
        hls.attachMedia(videoRef.current);
        
        return () => {
          hls.destroy();
        };
      } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
        // Para Safari que tem suporte nativo a HLS
        videoRef.current.src = hlsUrl;
        videoRef.current.addEventListener('loadedmetadata', () => {
          videoRef.current.play().catch(e => {
            console.log('Erro ao iniciar playback automático:', e);
          });
          setLoading(false);
        });
      } else {
        setError('Seu navegador não suporta HLS');
      }
    };

    if (videoRef.current) {
      loadHls();
    }
  }, [channel, lang]);

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Assistindo: {channel} ({lang})</h1>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}
      
      {loading && (
        <div className="flex justify-center items-center h-32">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          <p className="ml-2">Carregando stream...</p>
        </div>
      )}
      
      <div className="bg-black rounded-lg overflow-hidden">
        <audio 
          ref={videoRef} 
          controls 
          className="w-full"
          autoPlay
        />
      </div>
      
      <div className="mt-4">
        <p className="text-sm text-gray-600">
          Stream de áudio dublado em tempo real usando Whisper, DeepL e Coqui TTS.
        </p>
      </div>
    </div>
  );
}

export default Watch;
