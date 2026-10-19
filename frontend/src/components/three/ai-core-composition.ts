import { AI_CORE_FOV, aiCoreNodes, type AICoreScenePose } from "./ai-core-data";
import { clamp, type SceneComposition } from "./ai-core-scroll";

export type ContentRole = "nav" | "copy" | "card" | "caption" | "footer";

/**
 * A semantic page block, stored in document coordinates (except fixed UI such
 * as the sticky navigation). These are containers, not individual tags: the
 * model is composed against the copy column, the card grid and the nav rail.
 */
export type ContentBlock = {
  left: number;
  top: number;
  right: number;
  bottom: number;
  role: ContentRole;
  fixed?: boolean;
};

export type MeasuredSceneComposition = SceneComposition & {
  safeRadius: number;
  baseRadius: number;
  blocked: boolean;
};

export type SceneCompositionInput = {
  index: number;
  anchorX: number;
  anchorY: number;
  scrollY: number;
  pose: AICoreScenePose;
  blocks: ContentBlock[];
  viewportWidth: number;
  viewportHeight: number;
};

const EDGE_PADDING = 16;
const BLOCK_MARGIN = 18;
const SHIFT_X = 0.055;
const SHIFT_Y = 0.055;
const MIN_SAFE_RADIUS = 96;
/** Near-side planets project larger than the average-distance estimate. */
const PERSPECTIVE_SAFETY = 1.12;

export function sceneLayoutScale(viewportWidth: number): number {
  if (viewportWidth < 768) {
    return 0.64;
  }
  if (viewportWidth < 1050) {
    return 0.88;
  }
  return 1;
}

/**
 * The largest screen radius the authored scene can occupy at its current
 * camera distance. Multiplying by scale is enough for composition because the
 * camera FOV is fixed for every stop.
 */
export function estimateProjectedModelRadius(
  pose: AICoreScenePose,
  viewportHeight: number,
  layoutScale = 1
): number {
  const maxOrbit = aiCoreNodes.reduce(
    (largest, node) =>
      Math.max(largest, node.orbit.radius * pose.orbitSpread + pose.separation + node.radius),
    0
  );
  const halfFov = Math.tan((AI_CORE_FOV * Math.PI) / 360);
  return (maxOrbit * pose.scale * layoutScale * viewportHeight) / (2 * halfFov * pose.distance);
}

function toViewportBlock(block: ContentBlock, scrollY: number) {
  if (block.fixed) {
    return block;
  }
  return {
    ...block,
    top: block.top - scrollY,
    bottom: block.bottom - scrollY
  };
}

/**
 * Finds the largest free circle around the landmark anchor, pulling the anchor
 * toward the centre of that free space when the section is asymmetric (for
 * example, a heading column on the left and full-width cards underneath).
 */
export function computeSceneComposition(input: SceneCompositionInput): MeasuredSceneComposition {
  const {
    index,
    pose,
    blocks,
    viewportWidth,
    viewportHeight
  } = input;

  const anchorX = clamp(input.anchorX, 0, 1) * viewportWidth;
  const anchorY = clamp(input.anchorY, 0, 1) * viewportHeight;

  let left = EDGE_PADDING;
  let right = viewportWidth - EDGE_PADDING;
  let top = EDGE_PADDING;
  let bottom = viewportHeight - EDGE_PADDING;
  let blocked = false;

  for (const block of blocks) {
    const rect = toViewportBlock(block, input.scrollY);
    if (
      rect.right < -120 ||
      rect.left > viewportWidth + 120 ||
      rect.bottom < -120 ||
      rect.top > viewportHeight + 120
    ) {
      continue;
    }

    const padded = {
      left: rect.left - BLOCK_MARGIN,
      top: rect.top - BLOCK_MARGIN,
      right: rect.right + BLOCK_MARGIN,
      bottom: rect.bottom + BLOCK_MARGIN
    };

    if (block.role === "nav" && block.fixed) {
      top = Math.max(top, padded.bottom);
      continue;
    }

    const containsAnchor =
      anchorX > padded.left &&
      anchorX < padded.right &&
      anchorY > padded.top &&
      anchorY < padded.bottom;

    if (containsAnchor) {
      // The landmark itself sits inside real content on a compressed layout.
      // Keep the anchor but let the caller shrink the model aggressively.
      blocked = true;
      continue;
    }

    if (anchorY > padded.top && anchorY < padded.bottom) {
      if (padded.left >= anchorX) {
        right = Math.min(right, padded.left);
      } else if (padded.right <= anchorX) {
        left = Math.max(left, padded.right);
      }
    }

    if (anchorX > padded.left && anchorX < padded.right) {
      if (padded.top >= anchorY) {
        bottom = Math.min(bottom, padded.top);
      } else if (padded.bottom <= anchorY) {
        top = Math.max(top, padded.bottom);
      }
    }
  }

  const centerX = (left + right) / 2;
  const centerY = (top + bottom) / 2;
  const shiftLimitX = viewportWidth * SHIFT_X;
  const shiftLimitY = viewportHeight * SHIFT_Y;
  const shiftedX = anchorX + clamp(centerX - anchorX, -shiftLimitX, shiftLimitX);
  const shiftedY = anchorY + clamp(centerY - anchorY, -shiftLimitY, shiftLimitY);

  const radiusAt = (x: number, y: number) =>
    Math.min(x - left, right - x, y - top, bottom - y);
  const baseRadius = Math.max(0, radiusAt(anchorX, anchorY));
  const shiftedRadius = Math.max(0, radiusAt(shiftedX, shiftedY));
  const useShifted = shiftedRadius > baseRadius + 6;

  const finalX = useShifted ? shiftedX : anchorX;
  const finalY = useShifted ? shiftedY : anchorY;
  const freeRadius = Math.max(MIN_SAFE_RADIUS, useShifted ? shiftedRadius : baseRadius);
  const layoutScale = sceneLayoutScale(viewportWidth);
  const baseRadiusPx = Math.max(
    1,
    estimateProjectedModelRadius(pose, viewportHeight, layoutScale) * PERSPECTIVE_SAFETY
  );

  let fit = clamp(freeRadius / baseRadiusPx, 0.5, 1.12);
  if (blocked) {
    fit = Math.min(fit, 0.68);
  }

  return {
    index,
    anchorX: clamp(finalX / viewportWidth, 0, 1),
    anchorY: clamp(finalY / viewportHeight, 0, 1),
    fit,
    safeRadius: freeRadius,
    baseRadius: baseRadiusPx,
    blocked
  };
}
