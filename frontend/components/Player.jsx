import React, { useRef, useEffect } from "react";
import Hls from "hls.js";

/**
 * Player de HLS via hls.js. Recebe:
 *   - src: URL do index.m3u8 (ex: "/hls/gaules/en/index.m3u8")
 *   - width, height: dimensões
 */
export default function Player({ src, width, height }) {
  const videoRef = useRef(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !src) return;

    // Se o navegador suporta Hls.js:
    if (Hls.isSupported()) {
      const hls = new Hls();
      hls.loadSource(src);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {
          // autoplay pode ser bloqueado, mas o usuário pode clicar em play depois
        });
      });
      return () => {
        hls.destroy();
      };
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      // Safari nativo
      video.src = src;
      video.addEventListener("loadedmetadata", () => {
        video.play().catch(() => {});
      });
    }
  }, [src]);

  return (
    <video
      ref={videoRef}
      controls
      width={width}
      height={height}
      style={{ border: "1px solid #444" }}
    />
  );
}
