import { describe, expect, it } from "vitest";

import { aiCoreScenes } from "./ai-core-data";
import {
  applySceneCompositions,
  buildScrollTimeline,
  createPoseBuffer,
  fadeForScroll,
  interpolatePoseInto,
  sampleScrollTimeline
} from "./ai-core-scroll";

const timeline = buildScrollTimeline({
  viewportWidth: 1440,
  viewportHeight: 900,
  maxScroll: 9000,
  anchors: [
    { index: 0, centerX: 1080, centerY: 460 },
    { index: 1, centerX: 1040, centerY: 1900 },
    { index: 2, centerX: 280, centerY: 3600 },
    { index: 3, centerX: 1010, centerY: 5200 },
    { index: 4, centerX: 1130, centerY: 6600 },
    { index: 5, centerX: 950, centerY: 7800 }
  ],
  fadeStart: 8200,
  fadeEnd: 9000
});

describe("AI Core scroll timeline", () => {
  it("derives a monotonic set of scene stops from DOM landmarks", () => {
    expect(timeline.stops).toHaveLength(6);
    expect(timeline.stops[0].scrollY).toBe(0);
    for (let index = 1; index < timeline.stops.length; index += 1) {
      expect(timeline.stops[index].scrollY).toBeGreaterThanOrEqual(timeline.stops[index - 1].scrollY);
      expect(timeline.stops[index].anchorX).toBeGreaterThanOrEqual(0.22);
      expect(timeline.stops[index].anchorX).toBeLessThanOrEqual(0.8);
    }
    expect(timeline.stops[2].anchorX).toBeCloseTo(0.22);
  });

  it("moves forward and backward along exactly the same path", () => {
    const stop = timeline.stops[2];
    const before = sampleScrollTimeline(timeline, stop.scrollY - 180);
    const after = sampleScrollTimeline(timeline, stop.scrollY + 180);
    const returned = sampleScrollTimeline(timeline, stop.scrollY - 180);

    expect(after.progress).toBeGreaterThan(before.progress);
    expect(returned).toEqual(before);
    const segmentMin = Math.min(timeline.stops[1].anchorX, timeline.stops[2].anchorX);
    const segmentMax = Math.max(timeline.stops[1].anchorX, timeline.stops[2].anchorX);
    expect(before.anchorX).toBeGreaterThanOrEqual(segmentMin);
    expect(before.anchorX).toBeLessThanOrEqual(segmentMax);
  });

  it("snaps to the nearest authored scene under reduced motion", () => {
    const nearThird = timeline.stops[3].scrollY - 30;
    const sample = sampleScrollTimeline(timeline, nearThird, true);
    expect(sample.sceneIndex).toBe(3);
    expect(sample.from).toBe(3);
    expect(sample.to).toBe(3);
    expect(sample.t).toBe(0);
  });

  it("fades the model out after the final scene instead of removing it abruptly", () => {
    expect(fadeForScroll(timeline, timeline.fadeStart - 1)).toBe(1);
    expect(fadeForScroll(timeline, timeline.fadeStart + (timeline.fadeEnd - timeline.fadeStart) / 2)).toBeCloseTo(0.5, 1);
    expect(fadeForScroll(timeline, timeline.fadeEnd + 10)).toBe(0);
  });

  it("interpolates scene poses into a reusable buffer", () => {
    const buffer = createPoseBuffer();
    interpolatePoseInto(buffer, aiCoreScenes[1], aiCoreScenes[3], 0.25);
    expect(buffer.distance).toBeGreaterThan(aiCoreScenes[1].distance);
    expect(buffer.distance).toBeLessThan(aiCoreScenes[3].distance);
    expect(buffer.separation).toBeGreaterThan(0);
    expect(buffer.rotation).toHaveLength(3);
  });

  it("applies measured safe-area compositions and interpolates their fit", () => {
    const composed = applySceneCompositions(timeline, [
      { index: 1, anchorX: 0.76, anchorY: 0.42, fit: 0.9 },
      { index: 2, anchorX: 0.2, anchorY: 0.41, fit: 1.05 }
    ]);

    expect(composed.stops[1].anchorX).toBe(0.76);
    expect(composed.stops[1].anchorY).toBe(0.42);
    expect(composed.stops[1].fit).toBe(0.9);
    expect(composed.stops[0].fit).toBe(1);

    const between = sampleScrollTimeline(
      composed,
      (composed.stops[1].scrollY + composed.stops[2].scrollY) / 2
    );
    expect(between.fit).toBeGreaterThan(0.9);
    expect(between.fit).toBeLessThan(1.05);
  });
});
