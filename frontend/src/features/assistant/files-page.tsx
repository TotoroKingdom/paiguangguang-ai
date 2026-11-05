"use client";

import { useState } from "react";
import { AssistantDialog } from "./assistant-dialog";
import { AssistantIcon } from "./assistant-icon";
import { useAssistant } from "./provider";
import type { DemoFile } from "./types";
import styles from "./catalog.module.css";

const formatSize = (size: number) =>
  size < 1024
    ? `${size} B`
    : size < 1024 * 1024
      ? `${(size / 1024).toFixed(1)} KB`
      : `${(size / 1024 / 1024).toFixed(1)} MB`;
const makeId = () => `file-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

export function FilesPage() {
  const { state, dispatch } = useAssistant();
  const [query, setQuery] = useState("");
  const [deleting, setDeleting] = useState<DemoFile | null>(null);
  const [notice, setNotice] = useState("");
  const [selectionOpen, setSelectionOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const visible = state.files.filter((file) =>
    file.name.toLowerCase().includes(query.trim().toLowerCase()),
  );
  const addFiles = (files: FileList | null) => {
    if (!files?.length) return;
    const entries = Array.from(files, (file): DemoFile => ({
      id: makeId(),
      name: file.name,
      type: file.type || "未知类型",
      size: file.size,
      createdAt: new Date().toISOString(),
    }));
    dispatch({ type: "ADD_FILES", files: entries });
    setNotice(`已添加 ${entries.length} 个文件的元信息。`);
  };
  return (
    <section className={styles.page}>
      <div className={styles.heading}>
        <div>
          <p className={styles.eyebrow}>交互原型 · 模拟数据</p>
          <h1>文件库</h1>
          <p>管理本地模拟文件，选择附件用于聊天。仅保存文件元信息，不读取或解析正文。</p>
        </div>
        <div className={styles.headingActions}>
          <button
            className={styles.outline}
            onClick={() => {
              setSelectedIds(
                state.draft.fileIds.filter((id) => state.files.some((file) => file.id === id)),
              );
              setSelectionOpen(true);
            }}
          >
            选择聊天附件
          </button>
          <label className={styles.primary}>
            上传文件
            <input
              aria-label="上传本地文件"
              className={styles.hiddenInput}
              type="file"
              multiple
              onChange={(event) => {
                addFiles(event.target.files);
                event.target.value = "";
              }}
            />
          </label>
        </div>
      </div>
      {notice && (
        <p className={styles.notice} role="status">
          {notice}
        </p>
      )}
      <label className={styles.search}>
        <AssistantIcon name="search" size={20} />
        <span className={styles.srOnly}>搜索文件</span>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="搜索文件名称…"
        />
      </label>
      <div className={styles.filterRow}>
        <span>共 {visible.length} 个文件</span>
      </div>
      {visible.length === 0 ? (
        <p className={styles.empty}>没有找到文件，可上传文件或调整搜索条件。</p>
      ) : (
        <div className={styles.grid}>
          {visible.map((file) => (
            <article className={styles.card} key={file.id}>
              <div className={styles.cardMain}>
                <span className={styles.iconBox}>
                  <AssistantIcon name="file" size={30} />
                </span>
                <span>
                  <strong>{file.name}</strong>
                  <span className={styles.description}>
                    {formatSize(file.size)} · {file.type}
                  </span>
                </span>
              </div>
              <div className={styles.cardBottom}>
                <span className={styles.badge}>
                  {state.draft.fileIds.includes(file.id) ? "已选为附件" : "本地模拟"}
                </span>
                <button
                  className={styles.smallButton}
                  aria-label={`删除文件：${file.name}`}
                  onClick={() => setDeleting(file)}
                >
                  删除
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
      {selectionOpen && (
        <AssistantDialog title="选择聊天附件" onClose={() => setSelectionOpen(false)}>
          <p className={styles.dialogHint}>可选择多个文件，仅使用元信息。</p>
          {state.files.length === 0 ? (
            <p className={styles.empty}>文件库为空，请先上传文件。</p>
          ) : (
            <div className={styles.list}>
              {state.files.map((file) => (
                <label className={styles.listItem} key={file.id}>
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(file.id)}
                    onChange={(event) =>
                      setSelectedIds(
                        event.target.checked
                          ? [...selectedIds, file.id]
                          : selectedIds.filter((id) => id !== file.id),
                      )
                    }
                  />
                  {file.name} <span className={styles.muted}>{formatSize(file.size)}</span>
                </label>
              ))}
            </div>
          )}
          <div className={styles.dialogActions}>
            <button className={styles.secondary} onClick={() => setSelectionOpen(false)}>
              取消
            </button>
            <button
              className={styles.primary}
              onClick={() => {
                dispatch({ type: "SET_DRAFT", patch: { fileIds: selectedIds } });
                setSelectionOpen(false);
                setNotice(`已选择 ${selectedIds.length} 个聊天附件。`);
              }}
            >
              用于聊天
            </button>
          </div>
        </AssistantDialog>
      )}
      {deleting && (
        <AssistantDialog title="删除文件" onClose={() => setDeleting(null)}>
          <p>确定删除“{deleting.name}”的文件记录吗？</p>
          <div className={styles.dialogActions}>
            <button className={styles.secondary} onClick={() => setDeleting(null)}>
              取消
            </button>
            <button
              className={styles.danger}
              onClick={() => {
                dispatch({ type: "DELETE_FILE", id: deleting.id });
                setDeleting(null);
                setNotice("文件记录已删除。");
              }}
            >
              确认删除
            </button>
          </div>
        </AssistantDialog>
      )}
    </section>
  );
}
