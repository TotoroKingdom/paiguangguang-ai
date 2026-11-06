import type { Metadata } from "next";
import Link from "next/link";
import styles from "@/app/threejs/threejs.module.css";

export const metadata: Metadata = {
  title: "智能机器人 · 3D 交互实验室 · 派广广",
  description: "纯 Three.js 代码构建的可交互 3D 智能机器人：悬浮、眨眼、思考、挥手、换色与视角控制。"
};

export default function RobotExperimentPage() {
  return (
    <main className={styles.labPage}>
      <nav className={styles.labNav} aria-label="实验室导航">
        <Link className={styles.backLink} href="/lab/3d">← 返回 3D 实验室</Link>
        <span className={styles.labLabel}>THREE.JS / AI ROBOT LAB / 001</span>
      </nav>
      <iframe
        className={styles.labFrame}
        title="Three.js 智能机器人交互演示"
        src="/threejs-lab/index.html"
        loading="eager"
      />
    </main>
  );
}
