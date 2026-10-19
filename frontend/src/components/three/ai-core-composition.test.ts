import { describe, expect, it } from "vitest";

import { aiCoreScenes } from "./ai-core-data";
import {
  computeSceneComposition,
  modelCoverage,
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

const compose = (blocks: ContentBlock[], width = 1000, height = 1000) => computeSceneComposition({
  index: 0, anchorX: 0.5, anchorY: 0.5, scrollY: 0,
  pose: aiCoreScenes[0], viewportWidth: width, viewportHeight: height, blocks
});
const block = (left: number, top: number, right: number, bottom: number): ContentBlock => ({
  left, top, right, bottom, role: "card"
});

describe("safe circle boundaries", () => {
  it.each([[600, 600, 800, 800], [200, 600, 400, 800], [600, 200, 800, 400], [200, 200, 400, 400]])(
    "limits a diagonal rectangle at %s,%s", (left, top, right, bottom) => {
      const result = compose([block(left, top, right, bottom)]);
      expect(result.safeRadius).toBeCloseTo(Math.hypot(82, 82));
      expect(result.fit * result.baseRadius).toBeLessThanOrEqual(result.safeRadius);
    }
  );
  it("uses real clearance below the preferred minimum", () => {
    const result = compose([], 120, 120);
    expect(result.safeRadius).toBe(44);
    expect(result.blocked).toBe(true);
    expect(result.fit * result.baseRadius).toBeLessThanOrEqual(44);
  });
  it("shrinks below half scale in a narrow corridor", () => {
    const result = compose([block(0, 0, 462, 1000), block(538, 0, 1000, 1000)]);
    expect(result.safeRadius).toBe(20);
    expect(result.fit).toBeLessThan(0.5);
    expect(result.fit * result.baseRadius).toBeCloseTo(20);
  });
  it("fully retreats when no free space remains", () => {
    const result = compose([block(0, 0, 1000, 1000)]);
    expect(result.safeRadius).toBe(0);
    expect(result.fit).toBe(0);
  });
  it("checks diagonal distance again at the shifted centre", () => {
    const blocks = [block(0, 0, 300, 1000), block(650, 650, 850, 850)];
    const result = compose(blocks);
    const x = result.anchorX * 1000;
    const y = result.anchorY * 1000;
    expect(result.safeRadius).toBeLessThanOrEqual(Math.hypot(Math.max(632 - x, 0), Math.max(632 - y, 0)));
    expect(Math.abs(x - 500)).toBeLessThanOrEqual(55);
  });
});

describe("model coverage union", () => {
  const coverage = (blocks: ContentBlock[], scroll = 0, radius = 10) => modelCoverage(blocks, scroll, 0, 0, radius);
  it("adds disjoint obstacles", () => {
    expect(coverage([block(-10, -10, -5, 10), block(5, -10, 10, 10)])).toBe(0.5);
  });
  it("counts overlapping and nested obstacles only once", () => {
    expect(coverage([block(-10, -10, 5, 10), block(-5, -10, 10, 10), block(-2, -2, 2, 2)])).toBe(1);
  });
  it("merges touching edges without gaps or double counting", () => {
    expect(coverage([block(-10, -10, 0, 0), block(0, -10, 10, 0)])).toBe(0.5);
  });
  it("clips to the model bounds and ignores edge-only contact", () => {
    expect(coverage([block(-30, -30, 0, 30), block(10, -10, 20, 10)])).toBe(0.5);
  });
  it("converts document coordinates while preserving fixed blocks", () => {
    expect(coverage([block(-10, 90, 0, 110), { ...block(0, -10, 10, 10), fixed: true }], 100)).toBe(1);
  });
  it("handles empty obstacles, degenerate rectangles and tiny models", () => {
    expect(coverage([])).toBe(0);
    expect(coverage([block(0, 0, 0, 10)])).toBe(0);
    expect(coverage([block(-10, -10, 10, 10)], 0, 1)).toBe(0);
    expect(coverage([block(-10, -10, 10, 10)], 0, 0)).toBe(0);
  });
});
