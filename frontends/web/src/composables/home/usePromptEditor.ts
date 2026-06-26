import { computed, nextTick, ref, type Ref } from "vue";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ReferenceImageItem {
  id: string;
  label: string;
  fileUrl: string;
  fileName: string;
}

// ---------------------------------------------------------------------------
// Composable
// ---------------------------------------------------------------------------

export interface UsePromptEditorOptions {
  onMentionTrigger?: () => void;
}

export function usePromptEditor(referenceImages: Ref<ReferenceImageItem[]>, options: UsePromptEditorOptions = {}) {
  // ----- state -----

  const promptEditor = ref<HTMLDivElement | null>(null);
  const promptText = ref("");
  const composingPrompt = ref(false);
  const syncingPromptFromEditor = ref(false);
  const promptEditorFocused = ref(false);

  const showPromptPlaceholder = computed(
    () => !promptText.value.trim() && !promptEditorFocused.value && !composingPrompt.value,
  );

  // ----- serialization helpers -----

  function serializePromptEditorNode(node: Node, parentTag = ""): string {
    if (node.nodeType === Node.TEXT_NODE) {
      return node.textContent ?? "";
    }
    if (!(node instanceof HTMLElement)) {
      return "";
    }
    const mentionLabel = node.dataset.mentionLabel;
    if (mentionLabel) {
      return `@${mentionLabel}`;
    }
    if (node.tagName === "BR") {
      return "\n";
    }
    let text = "";
    node.childNodes.forEach((child) => {
      text += serializePromptEditorNode(child, node.tagName);
    });
    if ((node.tagName === "DIV" || node.tagName === "P") && parentTag !== "DIV" && parentTag !== "P") {
      return `${text}\n`;
    }
    return text;
  }

  function serializePromptEditorContent() {
    const editor = promptEditor.value;
    if (!editor) {
      return promptText.value;
    }
    return serializePromptEditorNode(editor)
      .replace(/\u00a0/g, " ")
      .replace(/\u200b/g, "")
      .replace(/\n$/, "");
  }

  // ----- mention chip rendering -----

  function buildMentionChip(item: ReferenceImageItem) {
    const chip = document.createElement("span");
    chip.className = "home-reference-pill home-reference-pill-inline";
    chip.setAttribute("contenteditable", "false");
    chip.dataset.mentionLabel = item.label;
    chip.style.display = "inline-flex";
    chip.style.alignItems = "center";
    chip.style.gap = "6px";
    chip.style.maxWidth = "112px";
    chip.style.height = "24px";
    chip.style.margin = "0 0.2em";
    chip.style.verticalAlign = "middle";
    chip.style.whiteSpace = "nowrap";
    chip.style.pointerEvents = "none";

    const thumb = document.createElement("span");
    thumb.className = "home-reference-pill__thumb";
    thumb.style.display = "inline-block";
    thumb.style.flex = "0 0 auto";
    thumb.style.width = "24px";
    thumb.style.height = "24px";
    thumb.style.overflow = "hidden";
    thumb.style.borderRadius = "6px";
    const image = document.createElement("img");
    image.src = item.fileUrl;
    image.alt = item.label;
    image.style.display = "block";
    image.style.width = "100%";
    image.style.height = "100%";
    image.style.objectFit = "cover";
    thumb.appendChild(image);

    const label = document.createElement("span");
    label.className = "home-reference-pill__label";
    label.textContent = item.label;
    label.style.display = "inline-block";
    label.style.minWidth = "0";
    label.style.overflow = "hidden";
    label.style.textOverflow = "ellipsis";
    label.style.whiteSpace = "nowrap";
    label.style.color = "#657487";
    label.style.fontSize = "0.78rem";
    label.style.fontWeight = "600";
    label.style.lineHeight = "1";
    label.style.alignSelf = "center";

    chip.appendChild(thumb);
    chip.appendChild(label);
    return chip;
  }

  // ----- editor rendering -----

  function renderPromptEditor(value: string) {
    const editor = promptEditor.value;
    if (!editor) {
      return;
    }
    const selectionOffset = getPromptSelectionOffset(editor);
    const referenceImageByLabel = new Map(referenceImages.value.map((item) => [item.label, item]));
    const fragment = document.createDocumentFragment();
    const mentionPattern = /@图片\d+/g;
    let lastIndex = 0;
    let matched = mentionPattern.exec(value);
    while (matched) {
      if (matched.index > lastIndex) {
        fragment.appendChild(document.createTextNode(value.slice(lastIndex, matched.index)));
      }
      const mention = matched[0];
      const label = mention.slice(1);
      const item = referenceImageByLabel.get(label);
      if (item) {
        fragment.appendChild(buildMentionChip(item));
      } else {
        fragment.appendChild(document.createTextNode(mention));
      }
      lastIndex = matched.index + mention.length;
      matched = mentionPattern.exec(value);
    }
    if (lastIndex < value.length) {
      fragment.appendChild(document.createTextNode(value.slice(lastIndex)));
    }
    if (!fragment.childNodes.length) {
      fragment.appendChild(document.createElement("br"));
    }
    editor.replaceChildren(fragment);
    if (selectionOffset !== null) {
      restorePromptSelection(editor, selectionOffset);
    }
  }

  // ----- selection helpers -----

  function getPromptSelectionOffset(editor: HTMLDivElement) {
    const selection = window.getSelection();
    if (!selection?.rangeCount) {
      return null;
    }
    const range = selection.getRangeAt(0);
    if (!editor.contains(range.startContainer)) {
      return null;
    }
    const probe = range.cloneRange();
    probe.selectNodeContents(editor);
    probe.setEnd(range.startContainer, range.startOffset);
    const container = document.createElement("div");
    container.appendChild(probe.cloneContents());
    return serializePromptEditorNode(container).replace(/\u00a0/g, " ").replace(/\u200b/g, "").length;
  }

  function restorePromptSelection(editor: HTMLDivElement, targetOffset: number) {
    const range = document.createRange();
    const selection = window.getSelection();
    let remaining = targetOffset;
    let placed = false;
    const nodes = Array.from(editor.childNodes);
    for (let index = 0; index < nodes.length; index += 1) {
      const node = nodes[index];
      if (node.nodeType === Node.TEXT_NODE) {
        const content = node.textContent ?? "";
        if (remaining <= content.length) {
          range.setStart(node, remaining);
          placed = true;
          break;
        }
        remaining -= content.length;
        continue;
      }
      if (node instanceof HTMLElement && node.dataset.mentionLabel) {
        const mentionLength = `@${node.dataset.mentionLabel}`.length;
        if (remaining <= mentionLength) {
          if (remaining === 0) {
            range.setStartBefore(node);
          } else {
            range.setStartAfter(node);
          }
          placed = true;
          break;
        }
        remaining -= mentionLength;
        continue;
      }
      if (node instanceof HTMLBRElement) {
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

  // ----- focus helpers -----

  function focusPromptEditorToEnd() {
    const editor = promptEditor.value;
    if (!editor) {
      return;
    }
    editor.focus();
    restorePromptSelection(editor, serializePromptEditorContent().length);
  }

  function insertPlainTextAtSelection(text: string) {
    const editor = promptEditor.value;
    const selection = window.getSelection();
    if (!editor || !selection?.rangeCount) {
      return;
    }
    const range = selection.getRangeAt(0);
    if (!editor.contains(range.startContainer)) {
      focusPromptEditorToEnd();
      return insertPlainTextAtSelection(text);
    }
    range.deleteContents();
    const node = document.createTextNode(text);
    range.insertNode(node);
    range.setStart(node, text.length);
    range.collapse(true);
    selection.removeAllRanges();
    selection.addRange(range);
  }

  // ----- sync -----

  function syncPromptTextFromEditor() {
    syncingPromptFromEditor.value = true;
    promptText.value = serializePromptEditorContent();
    nextTick(() => {
      syncingPromptFromEditor.value = false;
    });
  }

  // ----- event handlers -----

  function handlePromptEditorInput(event: InputEvent) {
    if (event?.isComposing) {
      composingPrompt.value = true;
      return;
    }
    if (event.inputType === "insertCompositionText") {
      return;
    }
    if (composingPrompt.value) {
      return;
    }
    syncPromptTextFromEditor();
    if (event.inputType === "insertText" && event.data === "@") {
      options.onMentionTrigger?.();
    }
  }

  function handlePromptEditorFocus() {
    promptEditorFocused.value = true;
  }

  function handlePromptEditorBlur() {
    promptEditorFocused.value = false;
    renderPromptEditor(promptText.value);
  }

  function handlePromptEditorCompositionStart() {
    composingPrompt.value = true;
  }

  function handlePromptEditorCompositionEnd() {
    composingPrompt.value = false;
    syncPromptTextFromEditor();
  }

  function handlePromptEditorBeforeInput(event: InputEvent) {
    if (event.isComposing || event.inputType === "insertCompositionText") {
      composingPrompt.value = true;
    }
  }

  function handlePromptEditorKeydown(event: KeyboardEvent) {
    if (composingPrompt.value || event.isComposing) {
      return;
    }
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    insertPlainTextAtSelection("\n");
    syncPromptTextFromEditor();
    nextTick(() => renderPromptEditor(promptText.value));
  }

  function handlePromptEditorPaste(event: ClipboardEvent) {
    if (composingPrompt.value) {
      return;
    }
    event.preventDefault();
    const text = event.clipboardData?.getData("text/plain") ?? "";
    insertPlainTextAtSelection(text);
    syncPromptTextFromEditor();
    nextTick(() => renderPromptEditor(promptText.value));
  }

  // ----- return -----

  return {
    // state
    promptEditor,
    promptText,
    composingPrompt,
    syncingPromptFromEditor,
    promptEditorFocused,
    showPromptPlaceholder,

    // functions
    serializePromptEditorNode,
    serializePromptEditorContent,
    buildMentionChip,
    renderPromptEditor,
    getPromptSelectionOffset,
    restorePromptSelection,
    focusPromptEditorToEnd,
    insertPlainTextAtSelection,
    syncPromptTextFromEditor,
    handlePromptEditorInput,
    handlePromptEditorFocus,
    handlePromptEditorBlur,
    handlePromptEditorCompositionStart,
    handlePromptEditorCompositionEnd,
    handlePromptEditorBeforeInput,
    handlePromptEditorKeydown,
    handlePromptEditorPaste,
  };
}
