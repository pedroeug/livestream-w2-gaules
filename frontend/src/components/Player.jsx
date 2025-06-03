// frontend/src/components/Player.jsx
import { useEffect, useRef } from "react";
import Hls from "hls.js";

export default function Player({ src, width, height }) {
  const videoRef = useRef();

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    // Se o navegador suportar HLS nativo (Safari, iOS), basta atribuir src direto
    if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = src;
    }
    // Caso contrário, usar hls.js para montar o stream
    else if (Hls.isSupported()) {
      const hls = new Hls();
      hls.loadSource(src);
      hls.attachMedia(video);
      // opcional: cleanup ao desmontar
      return () => {
        hls.destroy();
      };
    }
  }, [src]);

  return (
    <video
      ref={videoRef}
      controls
      width={width}
      height={height}
      style={{ backgroundColor: "black" }}
    />
  );
}
