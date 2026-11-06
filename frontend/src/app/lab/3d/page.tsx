import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";

import { MiniRobotPreview } from "@/components/three/mini-robot-preview";
import { labDemos } from "@/features/lab/3d-demos";
import styles from "./gallery.module.css";

export const metadata: Metadata = {
  title: "3D 交互实验室 · 派广广",
  description: "用 Three.js 探索程序化三维建模、实时交互与动态视觉的实验作品集。"
};

export default function ThreeDLabGalleryPage() {
  const availableCount = labDemos.filter((demo) => demo.status === "available").length;

  return (
    <main className={styles.galleryPage}>
      <div className={styles.shell}>
        <nav className={styles.breadcrumb} aria-label="面包屑导航">
          <Link href="/#projects">← 返回我的作品</Link>
          <span aria-hidden="true">/</span>
          <span>3D LAB</span>
        </nav>

        <header className={styles.header}>
          <div>
            <p className={styles.eyebrow}>CREATIVE LAB / EXPERIMENT INDEX</p>
            <h1>3D 交互实验室<span className={styles.headerDot}>.</span></h1>
            <p className={styles.intro}>把想象变成可交互的三维作品。这里持续收录我用 Three.js 构建的角色、机械结构与空间实验。</p>
          </div>
          <div className={styles.counter} aria-label={`已上线 ${availableCount} 个实验，共规划 ${labDemos.length} 个`}>
            <strong>{String(availableCount).padStart(2, "0")}</strong>
            <span>LIVE EXPERIMENTS</span>
            <small>/{String(labDemos.length).padStart(2, "0")} INDEXED</small>
          </div>
        </header>

        <section aria-labelledby="experiment-heading">
          <div className={styles.sectionHeading}>
            <h2 id="experiment-heading">探索作品</h2>
            <span>EXPLORE THE COLLECTION</span>
          </div>
          <div className={styles.grid}>
            {labDemos.map((demo) => {
              const available = demo.status === "available" && Boolean(demo.href);
              const content = (
                <>
                  <div className={styles.poster}>
                    {demo.id === "robot" ? (
                      <MiniRobotPreview poster={demo.preview} alt="" sizes="(max-width: 720px) 100vw, (max-width: 1080px) 50vw, 33vw" />
                    ) : (
                      <Image src={demo.preview} alt="" fill sizes="(max-width: 720px) 100vw, (max-width: 1080px) 50vw, 33vw" unoptimized />
                    )}
                    <span className={`${styles.status} ${available ? styles.statusLive : styles.statusPlanned}`}>
                      {available ? "● 可交互" : "规划中"}
                    </span>
                  </div>
                  <div className={styles.cardBody}>
                    <p className={styles.subtitle}>{demo.subtitle}</p>
                    <div className={styles.cardTitleRow}>
                      <h3>{demo.title}</h3>
                      {available && <span className={styles.arrow} aria-hidden="true">↗</span>}
                    </div>
                    <p className={styles.description}>{demo.description}</p>
                    <ul className={styles.tags} aria-label="技术主题">
                      {demo.tags.map((tag) => <li key={tag}>{tag}</li>)}
                    </ul>
                    <span className={styles.cta}>{available ? "进入实验 →" : "即将开放"}</span>
                  </div>
                </>
              );

              return available ? (
                <Link key={demo.id} href={demo.href!} className={`${styles.card} ${styles.cardLink}`} aria-label={`${demo.title}，进入交互实验`}>
                  {content}
                </Link>
              ) : (
                <article key={demo.id} className={`${styles.card} ${styles.cardPlanned}`} aria-label={`${demo.title}，规划中`}>
                  {content}
                </article>
              );
            })}
          </div>
        </section>

        <footer className={styles.footer}>
          <span>BUILT WITH CURIOSITY · THREE.JS</span>
          <Link href="/#projects">返回作品列表 ↗</Link>
        </footer>
      </div>
    </main>
  );
}
