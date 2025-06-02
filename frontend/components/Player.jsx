// frontend/src/components/Player.jsx
import { useEffect, useRef } from "react";
import Hls from "hls.js";

export default function Player({ src, width, height }) {
  const videoRef = useRef();

  useEffect(() => {
    if (Hls.isSupported()) {
      const hls = new Hls();
      hls.loadSource(src);
      hls.attachMedia(videoRef.current);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        videoRef.current.play().catch(console.error);
      });
      return () => {
        hls.destroy();
      };
    } else if (videoRef.current.canPlayType("application/vnd.apple.mpegurl")) {
      videoRef.current.src = src;
      videoRef.current.addEventListener("loadedmetadata", () => {
        videoRef.current.play().catch(console.error);
      });
    }
  }, [src]);

  return (
    <video
      ref={videoRef}
      width={width}
      height={height}
      controls
      style={{ backgroundColor: "#000" }}
    />
  );
}
