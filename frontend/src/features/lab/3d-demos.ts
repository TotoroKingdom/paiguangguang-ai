export type LabDemo = {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  tags: readonly string[];
  preview: string;
  status: "available" | "planned";
  href?: string;
};

/** Keep available routes and future experiments in one place. */
export const labDemos: readonly LabDemo[] = [
  {
    id: "robot",
    title: "智能机器人",
    subtitle: "AI ROBOT / 001",
    description: "从几何体开始塑造角色，体验悬浮、眨眼、挥手、换色与视角交互。",
    tags: ["程序化建模", "动画状态", "鼠标交互"],
    preview: "/work/threejs-lab-preview.svg",
    status: "available",
    href: "/lab/3d/robot"
  },
  {
    id: "gears",
    title: "机械齿轮",
    subtitle: "KINETIC SYSTEM / 002",
    description: "探索齿轮啮合、连续旋转与机械运动的表达方式。",
    tags: ["机械运动", "参数化几何", "待开发"],
    preview: "/work/threejs-gear-preview.svg",
    status: "planned"
  },
  {
    id: "galaxy",
    title: "粒子星系",
    subtitle: "PARTICLE FIELD / 003",
    description: "尝试通过粒子、轨道和光效构建可探索的宇宙场景。",
    tags: ["粒子系统", "空间场景", "待开发"],
    preview: "/work/threejs-galaxy-preview.svg",
    status: "planned"
  }
];
