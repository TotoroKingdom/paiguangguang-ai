import { aiCoreScenes, type AICoreScenePose } from "./ai-core-data";

/**
 * A DOM-derived scene stop. `centerY` is measured in document coordinates so it
 * stays valid while the page scrolls; `centerX` is a viewport coordinate.
 */
export type MeasuredSceneAnchor = {
  index: number;
  centerX: number;
  centerY: number;
};

export type SceneStop = {
  index: number;
  scrollY: number;
  anchorX: number;
  anchorY: number;
  /** Screen-space fit derived from the section's measured safe area. */
  fit: number;
};

/** A measured safe-area composition for one scene landmark. */
export type SceneComposition = {
  index: number;
  anchorX: number;
  anchorY: number;
  fit: number;
};

export type ScrollTimeline = {
  stops: SceneStop[];
  maxScroll: number;
  viewportWidth: number;
  viewportHeight: number;
  fadeStart: number;
  fadeEnd: number;
};

export type ScrollSample = {
  from: number;
  to: number;
  t: number;
  progress: number;
  anchorX: number;
  anchorY: number;
  fit: number;
  sceneIndex: number;
};

export type ScrollTimelineInput = {
  viewportWidth: number;
  viewportHeight: number;
  maxScroll: number;
  anchors: MeasuredSceneAnchor[];
  fadeStart?: number;
  fadeEnd?: number;
  reducedMotion?: boolean;
};

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function smoothstep01(value: number): number {
  const t = clamp(value, 0, 1);
  return t * t * (3 - 2 * t);
}

export function anchorXBounds(viewportWidth: number): [number, number] {
  // Keep the model's label cluster inside the viewport on narrow screens.
  return viewportWidth < 768 ? [0.28, 0.72] : [0.22, 0.8];
}

export function buildScrollTimeline(input: ScrollTimelineInput): ScrollTimeline {
  const { viewportWidth, viewportHeight, maxScroll } = input;
  const targetY = viewportWidth < 768 ? 0.5 : 0.46;
  const [minX, maxX] = anchorXBounds(viewportWidth);

  const sorted = [...input.anchors].sort((a, b) => a.index - b.index);
  const raw: SceneStop[] = sorted.map((anchor, index) => {
    const anchorX = clamp(anchor.centerX / Math.max(1, viewportWidth), minX, maxX);
    if (index === 0) {
      return {
        index,
        scrollY: 0,
        anchorX,
        anchorY: clamp(anchor.centerY / Math.max(1, viewportHeight), 0.18, 0.82),
        fit: 1
      };
    }

    return {
      index,
      scrollY: clamp(anchor.centerY - viewportHeight * targetY, 0, maxScroll),
      anchorX,
      anchorY: targetY,
      fit: 1
    };
  });

  const minimumGap = Math.min(180, Math.max(1, viewportHeight * 0.18));
  let previous = -Infinity;
  const stops = raw.map((stop, index) => {
    if (index === 0) {
      previous = stop.scrollY;
      return stop;
    }

    const scrollY = Math.max(stop.scrollY, previous + minimumGap);
    previous = scrollY;
    return { ...stop, scrollY };
  });

  // If the section landmarks are closer together than the requested gap (very
  // short pages), compress the timeline so every stop remains reachable.
  const last = stops[stops.length - 1];
  if (last && last.scrollY > maxScroll) {
    const firstScroll = stops[0]?.scrollY ?? 0;
    const rawSpan = Math.max(1, last.scrollY - firstScroll);
    const targetSpan = Math.max(1, maxScroll - firstScroll);
    for (let index = 1; index < stops.length; index += 1) {
      const stop = stops[index];
      stop.scrollY = firstScroll + ((stop.scrollY - firstScroll) / rawSpan) * targetSpan;
    }
  }

  const lastStop = stops[stops.length - 1]?.scrollY ?? 0;
  const defaultFadeStart = Math.min(maxScroll, lastStop + viewportHeight * 0.35);
  const defaultFadeEnd = Math.min(maxScroll, defaultFadeStart + viewportHeight * 0.6);
  const fadeStart = clamp(input.fadeStart ?? defaultFadeStart, lastStop, maxScroll);
  const fadeEnd = clamp(input.fadeEnd ?? defaultFadeEnd, fadeStart, maxScroll);

  return {
    stops,
    maxScroll,
    viewportWidth,
    viewportHeight,
    fadeStart,
    fadeEnd
  };
}

export function applySceneCompositions(
  timeline: ScrollTimeline,
  compositions: SceneComposition[]
): ScrollTimeline {
  if (compositions.length === 0) {
    return timeline;
  }

  const byIndex = new Map(compositions.map((composition) => [composition.index, composition]));
  return {
    ...timeline,
    stops: timeline.stops.map((stop) => {
      const composition = byIndex.get(stop.index);
      if (!composition) {
        return stop;
      }
      return {
        ...stop,
        anchorX: clamp(composition.anchorX, 0, 1),
        anchorY: clamp(composition.anchorY, 0, 1),
        fit: clamp(composition.fit, 0.5, 1.2)
      };
    })
  };
}

export function findSceneIndex(timeline: ScrollTimeline, scrollY: number): number {
  const stops = timeline.stops;
  if (stops.length === 0) {
    return 0;
  }

  let nearest = 0;
  let nearestDistance = Infinity;
  for (let index = 0; index < stops.length; index += 1) {
    const distance = Math.abs(stops[index].scrollY - scrollY);
    if (distance < nearestDistance) {
      nearestDistance = distance;
      nearest = index;
    }
  }
  return nearest;
}

export function sampleScrollTimeline(
  timeline: ScrollTimeline,
  scrollY: number,
  reducedMotion = false
): ScrollSample {
  const stops = timeline.stops;
  if (stops.length === 0) {
    return { from: 0, to: 0, t: 0, progress: 0, anchorX: 0.5, anchorY: 0.5, fit: 1, sceneIndex: 0 };
  }

  if (reducedMotion) {
    const index = findSceneIndex(timeline, scrollY);
    const stop = stops[index];
    return {
      from: index,
      to: index,
      t: 0,
      progress: index,
      anchorX: stop.anchorX,
      anchorY: stop.anchorY,
      fit: stop.fit,
      sceneIndex: index
    };
  }

  if (scrollY <= stops[0].scrollY) {
    return {
      from: 0,
      to: stops.length > 1 ? 1 : 0,
      t: 0,
      progress: 0,
      anchorX: stops[0].anchorX,
      anchorY: stops[0].anchorY,
      fit: stops[0].fit,
      sceneIndex: 0
    };
  }

  if (scrollY >= stops[stops.length - 1].scrollY) {
    const lastIndex = stops.length - 1;
    return {
      from: lastIndex,
      to: lastIndex,
      t: 0,
      progress: lastIndex,
      anchorX: stops[lastIndex].anchorX,
      anchorY: stops[lastIndex].anchorY,
      fit: stops[lastIndex].fit,
      sceneIndex: lastIndex
    };
  }

  for (let index = 0; index < stops.length - 1; index += 1) {
    const from = stops[index];
    const to = stops[index + 1];
    if (scrollY < to.scrollY) {
      const span = Math.max(1, to.scrollY - from.scrollY);
      const t = smoothstep01((scrollY - from.scrollY) / span);
      return {
        from: index,
        to: index + 1,
        t,
        progress: index + t,
        anchorX: from.anchorX + (to.anchorX - from.anchorX) * t,
        anchorY: from.anchorY + (to.anchorY - from.anchorY) * t,
        fit: from.fit + (to.fit - from.fit) * t,
        sceneIndex: t < 0.5 ? index : index + 1
      };
    }
  }

  const lastIndex = stops.length - 1;
  return {
    from: lastIndex,
    to: lastIndex,
    t: 0,
    progress: lastIndex,
    anchorX: stops[lastIndex].anchorX,
    anchorY: stops[lastIndex].anchorY,
    fit: stops[lastIndex].fit,
    sceneIndex: lastIndex
  };
}

export function fadeForScroll(timeline: ScrollTimeline, scrollY: number): number {
  if (timeline.fadeEnd <= timeline.fadeStart) {
    return scrollY < timeline.fadeEnd ? 1 : 0;
  }
  if (scrollY <= timeline.fadeStart) {
    return 1;
  }
  if (scrollY >= timeline.fadeEnd) {
    return 0;
  }
  return 1 - smoothstep01((scrollY - timeline.fadeStart) / (timeline.fadeEnd - timeline.fadeStart));
}

export function createPoseBuffer(): AICoreScenePose {
  const base = aiCoreScenes[0];
  return { ...base, rotation: [...base.rotation] as [number, number, number] };
}

const lerp = (from: number, to: number, t: number) => from + (to - from) * t;

/** Writes the interpolated pose into an existing object to avoid per-frame allocations. */
export function interpolatePoseInto(
  target: AICoreScenePose,
  from: AICoreScenePose,
  to: AICoreScenePose,
  t: number
): AICoreScenePose {
  target.id = t < 0.5 ? from.id : to.id;
  target.scale = lerp(from.scale, to.scale, t);
  target.distance = lerp(from.distance, to.distance, t);
  target.yaw = lerp(from.yaw, to.yaw, t);
  target.pitch = lerp(from.pitch, to.pitch, t);
  target.rotation[0] = lerp(from.rotation[0], to.rotation[0], t);
  target.rotation[1] = lerp(from.rotation[1], to.rotation[1], t);
  target.rotation[2] = lerp(from.rotation[2], to.rotation[2], t);
  target.orbitSpread = lerp(from.orbitSpread, to.orbitSpread, t);
  target.separation = lerp(from.separation, to.separation, t);
  target.orbitSpeed = lerp(from.orbitSpeed, to.orbitSpeed, t);
  target.labelOpacity = lerp(from.labelOpacity, to.labelOpacity, t);
  target.connections = lerp(from.connections, to.connections, t);
  target.halo = lerp(from.halo, to.halo, t);
  target.energy = lerp(from.energy, to.energy, t);
  target.lookX = lerp(from.lookX, to.lookX, t);
  target.lookY = lerp(from.lookY, to.lookY, t);
  target.roll = lerp(from.roll, to.roll, t);
  return target;
}
