import { onBeforeUnmount, onMounted } from "vue";
import { messageApi } from "@/composables/useMessage";
import { downloadMedia } from "@/utils/download";

export function positionWorkflowVersionMenu(event: ToggleEvent) {
  if (event.newState !== "open") return;
  const popover = event.target as HTMLElement;
  const trigger = document.querySelector<HTMLElement>(`[popovertarget="${popover.id}"]`);
  if (!trigger) return;
  const rect = trigger.getBoundingClientRect();
  const popoverWidth = popover.offsetWidth || 164;
  const popoverHeight = Math.max(popover.scrollHeight, popover.offsetHeight, 92);
  const maxLeft = window.innerWidth - popoverWidth - 8;
  const left = Math.max(8, Math.min(rect.right - popoverWidth, maxLeft));
  let top = rect.bottom + 4;
  if (top + popoverHeight > window.innerHeight - 8) {
    top = Math.max(8, rect.top - popoverHeight - 4);
  }
  popover.style.left = `${left}px`;
  popover.style.top = `${top}px`;
}

export function closeOpenWorkflowMenus(exceptTarget?: EventTarget | null) {
  const activeNode = exceptTarget instanceof Node ? exceptTarget : null;
  document.querySelectorAll<HTMLDetailsElement>(".workflow-more-menu[open]").forEach((menu) => {
    if (!activeNode || !menu.contains(activeNode)) menu.open = false;
  });
  document.querySelectorAll<HTMLElement>(".workflow-more-menu__popover").forEach((popover) => {
    if (!popover.matches(":popover-open") || (activeNode && popover.contains(activeNode))) return;
    popover.hidePopover();
  });
}

export function useStageWorkflowInteractions() {
  async function handleDownloadVideo(url: string, title: string) {
    try {
      const result = await downloadMedia({ url, title, mediaType: "video" });
      if (result.target === "album") messageApi.success("已保存到相册");
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : "下载失败");
    }
  }

  function handlePointerDown(event: PointerEvent) {
    closeOpenWorkflowMenus(event.target);
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === "Escape") closeOpenWorkflowMenus(null);
  }

  onMounted(() => {
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeydown);
  });
  onBeforeUnmount(() => {
    document.removeEventListener("pointerdown", handlePointerDown);
    document.removeEventListener("keydown", handleKeydown);
  });

  return {
    handleDownloadVideo,
    positionVersionMenu: positionWorkflowVersionMenu,
  };
}
