# AI Core — round 2 evidence (visual QA)

All screenshots are real browser captures (Playwright + Chromium, 1440×900, DPR 1),
same viewport, same scroll offsets for before/after pairs.

## Contact sheets

| File | What it shows |
| --- | --- |
| `compare-sections-a.png` | Hero / Capabilities / Projects — before (left) vs after (right) |
| `compare-sections-b.png` | Building / Exploring / Journey — before (left) vs after (right) |
| `compare-transitions.png` | The four authored transitions sampled at their exact midpoints |
| `compare-reverse.png` | Reverse scroll from contact section back to Hero (after only) |
| `compare-fade.png` | Model re-entry inside the fade window between two sections |

## Raw captures

- `before/01-hero.png` … `before/11-maxscroll.png` — original code
- `after/01-hero.png` … `after/11-maxscroll.png` — final code (forward)
- `after-reverse/00-maxscroll.png` … `after-reverse/08-hero.png` — final code (reverse)
- `after-dev/verify-*.png` — re-verification on the dev server, 1440×900
- `after-dev/vp-1280-*.png`, `after-dev/vp-1920-*.png` — responsive spot checks
- `after-dev/fade-*.png` — intermediate frames of the fade window
- Removed debug-only material / label lab frames from `after-dev/`
  (`lab-*`, `p-*`, `crop-*`, `t0*`, `trans-*`). Final verification, responsive,
  fade captures and unclassified captures are retained.

## Acceptance map

| Requirement | Evidence |
| --- | --- |
| Model must not overlap Hero / Capabilities copy | `compare-sections-a.png`, `after-dev/verify-hero.png` |
| Exploring: model was covering “我正在探索的项目” | `compare-sections-b.png` (Exploring row), `after-dev/verify-exploring.png` |
| Projects / Building: model no longer hidden behind large cards | `compare-sections-a.png` (Projects), `compare-sections-b.png` (Building) |
| Per-section screen-space safe area (silhouette vs titles/body/cards/nav) | `frontend/src/components/three/ai-core-composition.ts` + `compare-sections-*.png` |
| Long partial occlusion removed; shrink/retreat/fade where no free space exists | `compare-transitions.png`, `compare-fade.png` |
| Sphere material separation (shell / body / Fresnel), contrast, highlight | Hero and Capabilities rows in both sheets |
| Planet phase / tilt / radius / readable labels | `compare-sections-*.png`, `compare-reverse.png` |
| Single canvas + scroll controller, forward/reverse consistency | `compare-reverse.png` |
| No 3D-over-copy z-index trick | copy stays above canvas; model retreats instead |

Scroll stops used for the pairs (1440×900): hero 0, capabilities 585, projects 1694,
building 3017, exploring 3872, journey 5139, max 5704.
Midpoints: cap→projects 1139, projects→building 2355, building→exploring 3445,
exploring→journey 4505.
