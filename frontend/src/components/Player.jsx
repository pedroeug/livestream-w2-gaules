// frontend/src/components/Player.jsx

import React from "react";

const Player = ({ src, width = "640", height = "360" }) => (
  <video
    controls
    width={width}
    height={height}
    style={{ backgroundColor: "#000" }}
  >
    <source src={src} type="application/vnd.apple.mpegURL" />
    Seu navegador não suporta reprodução HLS.
  </video>
);

export default Player;

