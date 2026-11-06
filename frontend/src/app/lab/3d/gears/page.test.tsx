import { readFileSync } from "node:fs";
import { join } from "node:path";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import GearsExperimentPage, { metadata } from "./page";

describe("GearsExperimentPage", () => {
  it("embeds the local gears experiment and links back to the gallery", () => {
    render(<GearsExperimentPage />);

    expect(screen.getByRole("link", { name: /返回 3D 实验室/ })).toHaveAttribute("href", "/lab/3d");
    expect(screen.getByTitle("Three.js 机械齿轮传动交互演示")).toHaveAttribute("src", "/threejs-gears/index.html");
    expect(metadata.title).toContain("机械齿轮");
  });

  it("includes the original interactive controls and local Three.js scene", () => {
    const assetDir = join(process.cwd(), "public/threejs-gears");
    const html = readFileSync(join(assetDir, "index.html"), "utf8");
    const script = readFileSync(join(assetDir, "gears.js"), "utf8");

    for (const control of ["presets", "speed", "directions", "wireToggle", "contactToggle", "playToggle", "resetCamera", "stepButton"]) {
      expect(html).toContain(`id="${control}"`);
    }
    expect(html).toContain('src="./gears.js"');
    expect(script).toContain("from '../threejs-lab/vendor/three.module.js'");
    expect(script).toContain("new THREE.ExtrudeGeometry");
    expect(script).toContain("requestAnimationFrame(animate)");
  });
});
