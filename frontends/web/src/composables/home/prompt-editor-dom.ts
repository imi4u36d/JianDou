import type { ReferenceImageItem } from "./useReferenceImages";

export function serializePromptEditorNode(node: Node, parentTag = ""): string {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent ?? "";
  if (!(node instanceof HTMLElement)) return "";
  const mentionLabel = node.dataset.mentionLabel;
  if (mentionLabel) return `@${mentionLabel}`;
  if (node.tagName === "BR") return "\n";
  let text = "";
  node.childNodes.forEach((child) => {
    text += serializePromptEditorNode(child, node.tagName);
  });
  return (node.tagName === "DIV" || node.tagName === "P") && parentTag !== "DIV" && parentTag !== "P"
    ? `${text}\n`
    : text;
}

export function serializePromptEditorContent(editor: HTMLDivElement): string {
  return serializePromptEditorNode(editor)
    .replace(/\u00a0/g, " ")
    .replace(/\u200b/g, "")
    .replace(/\n$/, "");
}

export function buildPromptMentionChip(item: ReferenceImageItem): HTMLSpanElement {
  const chip = document.createElement("span");
  chip.className = "home-reference-pill home-reference-pill-inline";
  chip.setAttribute("contenteditable", "false");
  chip.dataset.mentionLabel = item.label;
  Object.assign(chip.style, {
    display: "inline-flex",
    alignItems: "center",
    gap: "6px",
    maxWidth: "112px",
    height: "24px",
    margin: "0 0.2em",
    verticalAlign: "middle",
    whiteSpace: "nowrap",
    pointerEvents: "none",
  });

  const thumb = document.createElement("span");
  thumb.className = "home-reference-pill__thumb";
  Object.assign(thumb.style, {
    display: "inline-block",
    flex: "0 0 auto",
    width: "24px",
    height: "24px",
    overflow: "hidden",
    borderRadius: "6px",
  });
  const image = document.createElement("img");
  image.src = item.fileUrl;
  image.alt = item.label;
  Object.assign(image.style, {
    display: "block",
    width: "100%",
    height: "100%",
    objectFit: "cover",
  });
  thumb.appendChild(image);

  const label = document.createElement("span");
  label.className = "home-reference-pill__label";
  label.textContent = item.label;
  Object.assign(label.style, {
    display: "inline-block",
    minWidth: "0",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    color: "#657487",
    fontSize: "0.78rem",
    fontWeight: "600",
    lineHeight: "1",
    alignSelf: "center",
  });
  chip.append(thumb, label);
  return chip;
}

export function getPromptSelectionOffset(editor: HTMLDivElement): number | null {
  const selection = window.getSelection();
  if (!selection?.rangeCount) return null;
  const range = selection.getRangeAt(0);
  if (!editor.contains(range.startContainer)) return null;
  const probe = range.cloneRange();
  probe.selectNodeContents(editor);
  probe.setEnd(range.startContainer, range.startOffset);
  const container = document.createElement("div");
  container.appendChild(probe.cloneContents());
  return serializePromptEditorNode(container).replace(/\u00a0/g, " ").replace(/\u200b/g, "").length;
}

export function restorePromptSelection(editor: HTMLDivElement, targetOffset: number): void {
  const range = document.createRange();
  const selection = window.getSelection();
  let remaining = targetOffset;
  let placed = false;
  for (const node of Array.from(editor.childNodes)) {
    if (node.nodeType === Node.TEXT_NODE) {
      const content = node.textContent ?? "";
      if (remaining <= content.length) {
        range.setStart(node, remaining);
        placed = true;
        break;
      }
      remaining -= content.length;
    } else if (node instanceof HTMLElement && node.dataset.mentionLabel) {
      const length = `@${node.dataset.mentionLabel}`.length;
      if (remaining <= length) {
        if (remaining === 0) range.setStartBefore(node);
        else range.setStartAfter(node);
        placed = true;
        break;
      }
      remaining -= length;
    } else if (node instanceof HTMLBRElement) {
      if (remaining <= 1) {
        range.setStartBefore(node);
        placed = true;
        break;
      }
      remaining -= 1;
    }
  }
  if (!placed) {
    range.selectNodeContents(editor);
    range.collapse(false);
  }
  range.collapse(true);
  selection?.removeAllRanges();
  selection?.addRange(range);
}

export function renderPromptEditor(
  editor: HTMLDivElement,
  value: string,
  referenceImages: ReferenceImageItem[],
): void {
  const selectionOffset = getPromptSelectionOffset(editor);
  const byLabel = new Map(referenceImages.map((item) => [item.label, item]));
  const fragment = document.createDocumentFragment();
  const mentionPattern = /@图片\d+/g;
  let lastIndex = 0;
  for (const match of value.matchAll(mentionPattern)) {
    const index = match.index ?? 0;
    if (index > lastIndex) fragment.appendChild(document.createTextNode(value.slice(lastIndex, index)));
    const mention = match[0];
    const item = byLabel.get(mention.slice(1));
    fragment.appendChild(item ? buildPromptMentionChip(item) : document.createTextNode(mention));
    lastIndex = index + mention.length;
  }
  if (lastIndex < value.length) fragment.appendChild(document.createTextNode(value.slice(lastIndex)));
  if (!fragment.childNodes.length) fragment.appendChild(document.createElement("br"));
  editor.replaceChildren(fragment);
  if (selectionOffset !== null) restorePromptSelection(editor, selectionOffset);
}

export function insertPromptTextAtSelection(editor: HTMLDivElement, text: string): boolean {
  const selection = window.getSelection();
  if (!selection?.rangeCount) return false;
  const range = selection.getRangeAt(0);
  if (!editor.contains(range.startContainer)) return false;
  range.deleteContents();
  const node = document.createTextNode(text);
  range.insertNode(node);
  range.setStart(node, text.length);
  range.collapse(true);
  selection.removeAllRanges();
  selection.addRange(range);
  return true;
}
