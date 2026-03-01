import React from "react";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { SCENE_DURATIONS, TRANSITION_FRAMES } from "./lib/constants";

import { TitleScene } from "./scenes/TitleScene";
import { ProblemScene } from "./scenes/ProblemScene";
import { SavingsScene } from "./scenes/SavingsScene";
import { PipelineScene } from "./scenes/PipelineScene";
import { FinetuningScene } from "./scenes/FinetuningScene";
import { ServingScene } from "./scenes/ServingScene";
import { SelfImprovementScene } from "./scenes/SelfImprovementScene";
import { TechStackScene } from "./scenes/TechStackScene";
import { ClosingScene } from "./scenes/ClosingScene";

const T = TRANSITION_FRAMES;

export const Video: React.FC = () => {
  return (
    <TransitionSeries>
      <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.title}>
        <TitleScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: T })}
      />

      <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.problem}>
        <ProblemScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: T })}
      />

      <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.savings}>
        <SavingsScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={slide({ direction: "from-right" })}
        timing={linearTiming({ durationInFrames: T })}
      />

      <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.pipeline}>
        <PipelineScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: T })}
      />

      <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.finetuning}>
        <FinetuningScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: T })}
      />

      <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.serving}>
        <ServingScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={slide({ direction: "from-right" })}
        timing={linearTiming({ durationInFrames: T })}
      />

      <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.selfImprovement}>
        <SelfImprovementScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: T })}
      />

      <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.techStack}>
        <TechStackScene />
      </TransitionSeries.Sequence>

      <TransitionSeries.Transition
        presentation={fade()}
        timing={linearTiming({ durationInFrames: T })}
      />

      <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.closing}>
        <ClosingScene />
      </TransitionSeries.Sequence>
    </TransitionSeries>
  );
};
