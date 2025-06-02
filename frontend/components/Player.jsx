// frontend/src/components/Player.jsx

import { useEffect, useRef } from "react";
import Hls from "hls.js";

export default function Player({ src, width, height }) {
  const videoRef = useRef();

  useEffect(() => {
    if (videoRef.current) {
      if (Hls.isSupported()) {
        const hls = new Hls();
        hls.loadSource(src);
        hls.attachMedia(videoRef.current);
      } else if (videoRef.current.canPlayType("application/vnd.apple.mpegurl")) {
        videoRef.current.src = src;
      }
    }
  }, [src]);

  return (
    <video
      ref={videoRef}
      controls
      width={width}
      height={height}
    />
  );
}
