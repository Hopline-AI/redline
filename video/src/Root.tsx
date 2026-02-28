import React from "react";
import { Composition } from "remotion";
import { Video } from "./Video";
import { FPS, WIDTH, HEIGHT, TOTAL_FRAMES } from "./lib/constants";
import "./index.css";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="RedlineExplainer"
      component={Video}
      durationInFrames={TOTAL_FRAMES}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
    />
  );
};
