/**
 * use轮询组合式逻辑。
 */
import { onUnmounted, ref } from "vue";

interface UsePollingOptions {
  pauseWhenHidden?: boolean;
}

/**
 * 处理use轮询。
 * @param callback 要执行的回调
 * @param delayMs 轮询间隔（毫秒）
 */
export function usePolling(callback: () => Promise<void> | void, delayMs: number | (() => number), options: UsePollingOptions = {}) {
  const active = ref(false);
  const running = ref(false);
  const timer = ref<number | null>(null);
  const pauseWhenHidden = options.pauseWhenHidden ?? true;

  const isDocumentHidden = () => pauseWhenHidden && typeof document !== "undefined" && document.visibilityState === "hidden";

  /**
   * 停止stop。
   */
  const stop = () => {
    active.value = false;
    if (timer.value !== null) {
      window.clearTimeout(timer.value);
      timer.value = null;
    }
  };

  /**
   * 处理调度。
   */
  const run = async () => {
    if (!active.value) {
      return;
    }

    if (isDocumentHidden()) {
      schedule();
      return;
    }

    if (running.value) {
      schedule();
      return;
    }

    running.value = true;
    try {
      await callback();
    } finally {
      running.value = false;
      if (active.value) {
        schedule();
      }
    }
  };

  /**
   * 处理调度。
   */
  function schedule() {
    if (!active.value || timer.value !== null) {
      return;
    }
    const delay = typeof delayMs === "function" ? delayMs() : delayMs;
    timer.value = window.setTimeout(() => {
      timer.value = null;
      void run();
    }, delay);
  }

  function handleVisibilityChange() {
    if (!active.value || isDocumentHidden() || running.value) {
      return;
    }
    if (timer.value !== null) {
      window.clearTimeout(timer.value);
      timer.value = null;
    }
    void run();
  }

  const start = async (immediate = true) => {
    stop();
    active.value = true;

    if (immediate) {
      await run();
      return;
    }

    schedule();
  };

  if (typeof document !== "undefined") {
    document.addEventListener("visibilitychange", handleVisibilityChange);
  }

  onUnmounted(() => {
    stop();
    if (typeof document !== "undefined") {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    }
  });

  return {
    active,
    running,
    start,
    stop
  };
}
