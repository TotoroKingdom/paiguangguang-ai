import type { Metadata } from "next";
import Link from "next/link";
import styles from "@/app/threejs/threejs.module.css";

export const metadata: Metadata = {
  title: "机械齿轮 · 3D 交互实验室 · 派广广",
  description: "纯 Three.js 程序化创建双齿轮传动场景，支持齿数组合、转速、方向、线框与视角交互。"
};

export default function GearsExperimentPage() {
  return (
    <main className={styles.labPage}>
      <nav className={styles.labNav} aria-label="实验室导航">
        <Link className={styles.backLink} href="/lab/3d">← 返回 3D 实验室</Link>
        <span className={styles.labLabel}>THREE.JS / MECHANICAL GEARS / 002</span>
      </nav>
      <iframe
        className={styles.labFrame}
        title="Three.js 机械齿轮传动交互演示"
        src="/threejs-gears/index.html"
        loading="eager"
      />
    </main>
  );
}
