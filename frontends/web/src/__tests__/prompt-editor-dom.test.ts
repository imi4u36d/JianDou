import { describe, expect, it } from "vitest";
import {
  insertPromptTextAtSelection,
  renderPromptEditor,
  restorePromptSelection,
  serializePromptEditorContent,
} from "@/composables/home/prompt-editor-dom";

describe("prompt editor DOM", () => {
  it("renders reference mentions while preserving plain-text serialization", () => {
    const editor = document.createElement("div");

    renderPromptEditor(editor, "前景 @图片1 后景", [
      { id: "ref-1", label: "图片1", fileUrl: "/storage/ref.png", fileName: "ref.png" },
    ]);

    expect(editor.querySelector("[data-mention-label='图片1'] img")?.getAttribute("src")).toBe("/storage/ref.png");
    expect(serializePromptEditorContent(editor)).toBe("前景 @图片1 后景");
  });

  it("restores a serialized caret offset and inserts plain text", () => {
    const editor = document.createElement("div");
    document.body.appendChild(editor);
    renderPromptEditor(editor, "镜头", []);
    restorePromptSelection(editor, 2);

    expect(insertPromptTextAtSelection(editor, "推进")).toBe(true);
    expect(serializePromptEditorContent(editor)).toBe("镜头推进");
    editor.remove();
  });
});
