import { describe, expect, it } from "vitest";
import { createInitialState } from "./data";
import { demoReducer, restoreState } from "./store";
describe("assistant state", () => {
  it("rejects corrupt nested data and returns fresh seed", () => {
    const state = createInitialState();
    state.files[0].size = -1;
    expect(restoreState(JSON.stringify(state))).toEqual(createInitialState());
  });
  it("stops interrupted generation and connections", () => {
    const state = createInitialState();
    state.conversations[0].messages.push({
      id: "m",
      role: "assistant",
      content: "part",
      status: "generating",
    });
    state.connectors[0].status = "connecting";
    const restored = restoreState(JSON.stringify(state));
    expect(restored.conversations[0].messages.at(-1)?.status).toBe("stopped");
    expect(restored.connectors[0].status).toBe("disconnected");
  });
  it("cleans stale draft references during restoration", () => {
    const state = createInitialState();
    state.draft.fileIds = ["missing", "file-1"];
    state.draft.capability = { id: "missing", kind: "skill", name: "不存在" };
    const draft = restoreState(JSON.stringify(state)).draft;
    expect(draft.fileIds).toEqual(["file-1"]);
    expect(draft.capability).toBeNull();
  });
  it("removes deleted file from draft", () => {
    const state = createInitialState();
    state.draft.fileIds = ["file-1", "file-2"];
    expect(demoReducer(state, { type: "DELETE_FILE", id: "file-1" }).draft.fileIds).toEqual([
      "file-2",
    ]);
  });
});

it("keeps drafts isolated across conversations and restores them", () => {
  let state = createInitialState();
  state = demoReducer(state, { type: "SET_DRAFT", patch: { text: "新建草稿" } });
  state = demoReducer(state, { type: "ACTIVATE_DRAFT", key: "conversation-1" });
  expect(state.draft.text).toBe("");
  state = demoReducer(state, {
    type: "SET_DRAFT",
    patch: { text: "会话草稿", fileIds: ["file-1", "missing"] },
  });
  state = demoReducer(state, { type: "ACTIVATE_DRAFT", key: "conversation-2" });
  const restored = restoreState(JSON.stringify(state));
  state = demoReducer(restored, { type: "ACTIVATE_DRAFT", key: "conversation-1" });
  expect(state.draft.text).toBe("会话草稿");
  expect(state.draft.fileIds).toEqual(["file-1"]);
  state = demoReducer(state, { type: "ACTIVATE_DRAFT", key: "new" });
  expect(state.draft.text).toBe("新建草稿");
  state = demoReducer(state, { type: "DELETE_CONVERSATION", id: "conversation-1" });
  expect(state.drafts?.["conversation-1"]).toBeUndefined();
});
it("accepts old v1 data without draft maps and rejects corrupt maps", () => {
  const state = createInitialState();
  delete state.drafts;
  delete state.activeDraftKey;
  state.draft.text = "旧草稿";
  const restored = restoreState(JSON.stringify(state));
  expect(restored.activeDraftKey).toBe("new");
  expect(restored.draft.text).toBe("旧草稿");
  expect(restoreState(JSON.stringify({ ...state, drafts: { bad: { text: 1 } } }))).toEqual(
    createInitialState(),
  );
});

it.each(["constructor", "toString"])(
  "initializes an empty draft for inherited property key %s",
  (key) => {
    const state = demoReducer(createInitialState(), { type: "ACTIVATE_DRAFT", key });
    expect(state.draft).toEqual({ text: "", capability: null, fileIds: [] });
  },
);
