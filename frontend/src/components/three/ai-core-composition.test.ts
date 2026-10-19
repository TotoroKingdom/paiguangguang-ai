import { describe, expect, it } from "vitest";

import { aiCoreScenes } from "./ai-core-data";
import {
  computeSceneComposition,
  estimateProjectedModelRadius,
  type ContentBlock
} from "./ai-core-composition";

const viewportWidth = 1440;
const viewportHeight = 900;
const nav: ContentBlock = {
  left: 80,
  top: 36,
  right: 1360,
  bottom: 106,
  role: "nav",
  fixed: true
};

describe("AI Core screen-space composition", () => {
  it("scales the projected footprint with the authored camera", () => {
    const pose = aiCoreScenes[2];
    const near = estimateProjectedModelRadius({ ...pose, distance: pose.distance * 0.8 }, viewportHeight);
    const far = estimateProjectedModelRadius({ ...pose, distance: pose.distance * 1.2 }, viewportHeight);
    const large = estimateProjectedModelRadius({ ...pose, scale: pose.scale * 1.2 }, viewportHeight);

    expect(near).toBeGreaterThan(far);
    expect(large).toBeGreaterThan(estimateProjectedModelRadius(pose, viewportHeight));
  });

  it("pulls a left-hand scene out of the copy column and above the card grid", () => {
    const composition = computeSceneComposition({
      index: 4,
      anchorX: 0.22,
      anchorY: 0.46,
      scrollY: 3872,
      pose: aiCoreScenes[4],
      viewportWidth,
      viewportHeight,
      blocks: [
        nav,
        { left: 556, top: 4105, right: 1136, bottom: 4465, role: "copy" },
        { left: 80, top: 4505, right: 491, bottom: 4829, role: "card" },
        { left: 515, top: 4505, right: 926, bottom: 4829, role: "card" },
        { left: 949, top: 4505, right: 1360, bottom: 4829, role: "card" }
      ]
    });

    expect(composition.blocked).toBe(false);
    expect(composition.anchorX).toBeLessThan(0.22);
    expect(composition.anchorY).toBeLessThan(0.46);
    expect(composition.safeRadius).toBeGreaterThan(220);
    expect(composition.fit).toBeGreaterThan(0.85);
  });

  it("centres a right-hand scene between the copy column and the viewport edge", () => {
    const composition = computeSceneComposition({
      index: 1,
      anchorX: 0.8,
      anchorY: 0.46,
      scrollY: 585,
      pose: aiCoreScenes[1],
      viewportWidth,
      viewportHeight,
      blocks: [
        nav,
        { left: 80, top: 818, right: 660, bottom: 1178, role: "copy" },
        { left: 80, top: 1218, right: 708, bottom: 1482, role: "card" },
        { left: 732, top: 1218, right: 1360, bottom: 1482, role: "card" }
      ]
    });

    expect(composition.anchorX).toBeLessThan(0.8);
    expect(composition.anchorY).toBeLessThan(0.46);
    expect(composition.anchorX + composition.safeRadius / viewportWidth).toBeLessThanOrEqual(1);
    expect(composition.safeRadius).toBeGreaterThan(220);
  });

  it("degrades to a small model when the landmark is buried in content", () => {
    const composition = computeSceneComposition({
      index: 0,
      anchorX: 0.5,
      anchorY: 0.5,
      scrollY: 0,
      pose: aiCoreScenes[0],
      viewportWidth,
      viewportHeight,
      blocks: [{ left: 0, top: 0, right: viewportWidth, bottom: viewportHeight, role: "card" }]
    });

    expect(composition.blocked).toBe(true);
    expect(composition.fit).toBeLessThanOrEqual(0.68);
  });
});
