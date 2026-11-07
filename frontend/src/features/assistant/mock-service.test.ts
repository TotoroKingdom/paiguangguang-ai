import { expect, it } from "vitest";
import { capabilityCatalog, createInitialState } from "./data";
import { createMockReply, testConnection } from "./mock-service";
it("uses attachment metadata without claiming file content", () => {
  const result = createMockReply({ text: "分析", fileIds: ["file-1"] }, createInitialState().files);
  expect(result.reply).toContain("项目需求.md");
  expect(result.reply).toContain("不读取文件内容");
});
it("validates address and allows connection retry", async () => {
  const base = {
    id: "x",
    name: "测试",
    url: "https://example.com",
    status: "disconnected" as const,
  };
  expect((await testConnection({ ...base, url: "invalid" })).status).toBe("error");
  const failed = await testConnection(base, true);
  expect(failed.status).toBe("error");
  const success = await testConnection(failed);
  expect(success.status).toBe("connected");
  expect(success.lastError).toBeUndefined();
});

it("uses each skill workflow and separates capability steps", () => {
  const skill = capabilityCatalog.find((item) => item.id === "skill-2")!;
  const result = createMockReply({ text: "需求", capability: skill, fileIds: [] }, []);
  expect(result.steps.map((step) => step.title)).toEqual(skill.steps);
  const tool = createMockReply({ text: "搜索", capability: capabilityCatalog[0], fileIds: [] }, []);
  expect(tool.steps.map((step) => step.title)).toEqual(["调用参数", "工具结果"]);
});
it("distinguishes knowledge analysis from knowledge lookup", () => {
  expect(createMockReply({ text: "知识分析", fileIds: [] }, []).reply).toContain("知识分析建议");
  expect(createMockReply({ text: "知识查询", fileIds: [] }, []).reply).toContain("知识查询建议");
});
