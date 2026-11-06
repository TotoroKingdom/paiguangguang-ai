import type { Metadata } from "next";
import styles from "./threejs.module.css";

export const metadata: Metadata = {
  title: "Three.js 智能机器人实验室 · 派广广",
  description: "纯 Three.js 代码构建的可交互 3D 智能机器人：悬浮、眨眼、思考、挥手、换色与视角控制。"
};

export default function ThreeJsLabPage() {
  return (
    <main className={styles.labPage}>
      <nav className={styles.labNav} aria-label="实验室导航">
        <a className={styles.backLink} href="/#exploring">← 返回探索项目</a>
        <span className={styles.labLabel}>THREE.JS / AI ROBOT LAB</span>
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
