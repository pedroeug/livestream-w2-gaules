// frontend/src/components/Player.jsx

import React from "react";
import Hls from "hls.js";

export default function Player({ src, width, height }) {
  const videoRef = React.useRef();

  React.useEffect(() => {
    if (Hls.isSupported()) {
      const hls = new Hls();
      hls.loadSource(src);
      hls.attachMedia(videoRef.current);
      hls.on(Hls.Events.MANIFEST_PARSED, function () {
        videoRef.current.play();
      });
      return () => {
        hls.destroy();
      };
    } else if (videoRef.current.canPlayType("application/vnd.apple.mpegurl")) {
      videoRef.current.src = src;
      videoRef.current.addEventListener("loadedmetadata", () => {
        videoRef.current.play();
      });
    }
  }, [src]);

  return (
    <video
      ref={videoRef}
      controls
      style={{ width: width, height: height, background: "#000" }}
    />
  );
}
