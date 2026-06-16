import { ref } from "vue";

/**
 * 全局消息提示 composable。
 * 在右上角弹出 toast 风格的消息提示，自动消失。
 */

type MessageType = "success" | "error" | "warning" | "info";

interface MessageEntry {
  id: string;
  type: MessageType;
  content: string;
}

const entries = ref<MessageEntry[]>([]);
let counter = 0;

function generateId(): string {
  return `msg-${Date.now()}-${++counter}`;
}

/**
 * 显示一条消息提示。
 * @param type 消息类型
 * @param content 消息内容
 * @param duration 显示时长（毫秒），0 表示不自动消失
 */
function show(type: MessageType, content: string, duration = 4000): void {
  const id = generateId();
  entries.value.push({ id, type, content });
  if (duration > 0) {
    setTimeout(() => remove(id), duration);
  }
}

function remove(id: string): void {
  const index = entries.value.findIndex((entry) => entry.id === id);
  if (index >= 0) {
    entries.value.splice(index, 1);
  }
}

export function useMessage() {
  return {
    entries,
    remove,
    success: (content: string, duration?: number) => show("success", content, duration),
    error: (content: string, duration?: number) => show("error", content, duration),
    warning: (content: string, duration?: number) => show("warning", content, duration),
    info: (content: string, duration?: number) => show("info", content, duration),
  };
}

// 暴露全局实例，供非 setup 上下文调用（如 setTimeout 回调）
export const messageApi = useMessage();
