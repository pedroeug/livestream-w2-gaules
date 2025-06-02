// frontend/src/components/Player.jsx

import React from "react";

export default function Player({ src, width = "640", height = "360" }) {
  return (
    <video
      controls
      width={width}
      height={height}
      style={{ backgroundColor: "#000" }}
    >
      <source src={src} type="application/vnd.apple.mpegurl" />
      Seu navegador não suporta este player HLS.
    </video>
  );
}
